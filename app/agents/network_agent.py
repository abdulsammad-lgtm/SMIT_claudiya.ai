import datetime
from datetime import timezone
import random
from typing import Optional

import networkx as nx
from agents import Agent, function_tool, Runner

from app.api.schemas import AgentScoreOutput
from app.db.models import async_session, Transaction
from app.orchestrator.policy import score_from_signal
from sqlalchemy import select


async def _build_fraud_graph(device_fingerprint: str, phone_number: str, shipping_address: str, customer_id: str) -> dict:
    result = await _fetch_recent_txns()
    all_txns = result

    G = nx.Graph()
    address_normalized = shipping_address.strip().lower()

    for t in all_txns:
        G.add_node(f"cust:{t.customer_id}", type="customer")
        G.add_node(f"dev:{t.device_fingerprint}", type="device")
        G.add_node(f"phone:{t.phone_number}", type="phone")
        addr_norm = t.shipping_address.strip().lower() if t.shipping_address else ""
        G.add_node(f"addr:{addr_norm}", type="address")

        G.add_edge(f"cust:{t.customer_id}", f"dev:{t.device_fingerprint}", order=t.order_id)
        G.add_edge(f"cust:{t.customer_id}", f"phone:{t.phone_number}", order=t.order_id)
        G.add_edge(f"cust:{t.customer_id}", f"addr:{addr_norm}", order=t.order_id)

    components = list(nx.connected_components(G))
    involved = []
    for comp in components:
        customers = [n for n in comp if n.startswith("cust:")]
        devices = [n for n in comp if n.startswith("dev:")]
        phones = [n for n in comp if n.startswith("phone:")]
        addresses = [n for n in comp if n.startswith("addr:")]
        linked_order_ids = _get_linked_order_ids(G, comp)
        if len(customers) > 1 or (
            (f"cust:{customer_id}" in comp) and
            any(a == f"addr:{address_normalized}" for a in comp)
        ):
            involved.append({
                "customers": [c.replace("cust:", "") for c in customers],
                "devices": [d.replace("dev:", "") for d in devices],
                "phones": [p.replace("phone:", "") for p in phones],
                "addresses": [a.replace("addr:", "") for a in addresses],
                "component_size": len(comp),
                "distinct_customer_count": len(customers),
                "linked_order_ids": linked_order_ids[:20],
            })

    target_comp = None
    for comp in components:
        if f"cust:{customer_id}" in comp:
            linked_ids = _get_linked_order_ids(G, comp)
            target_comp = {
                "customers": [n.replace("cust:", "") for n in comp if n.startswith("cust:")],
                "devices": [n.replace("dev:", "") for n in comp if n.startswith("dev:")],
                "phones": [n.replace("phone:", "") for n in comp if n.startswith("phone:")],
                "addresses": [n.replace("addr:", "") for n in comp if n.startswith("addr:")],
                "component_size": len(comp),
                "linked_order_ids": linked_ids[:20],
            }
            break

    return {
        "target_component": target_comp,
        "total_components": len(components),
        "suspicious_components": involved,
    }


async def _fetch_recent_txns() -> list:
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(
                Transaction.timestamp >= datetime.datetime.now(timezone.utc) - datetime.timedelta(days=60),
            )
        )
        return result.scalars().all()


def _get_linked_order_ids(G, comp):
    linked = []
    for u, v, d in G.edges(data=True):
        if (u in comp) and (v in comp):
            oid = d.get("order", "")
            if oid and oid not in linked:
                linked.append(oid)
    return linked


@function_tool
async def build_fraud_graph(device_fingerprint: str, phone_number: str, shipping_address: str, customer_id: str) -> dict:
    return await _build_fraud_graph(device_fingerprint, phone_number, shipping_address, customer_id)


async def _check_cod_address_density(shipping_address: str) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.payment_method == "cod")
        )
        cod_txns = result.scalars().all()
    total_cod = len(cod_txns)

    addr_norm = shipping_address.strip().lower()
    addr_cod_count = sum(1 for t in cod_txns if t.shipping_address.strip().lower() == addr_norm)

    baseline = max(1, total_cod / max(1, 100))
    density_ratio = addr_cod_count / baseline if baseline > 0 else 0

    return {
        "address_cod_count": addr_cod_count,
        "total_cod_orders": total_cod,
        "density_ratio": round(density_ratio, 2),
        "is_elevated": density_ratio > 2.0,
    }


@function_tool
async def check_cod_address_density(shipping_address: str) -> dict:
    return await _check_cod_address_density(shipping_address)


async def fast_path_network(txn: Transaction) -> AgentScoreOutput:
    graph_data = await _build_fraud_graph(
        txn.device_fingerprint, txn.phone_number, txn.shipping_address, txn.customer_id
    )
    cod_density = await _check_cod_address_density(txn.shipping_address)

    scores = []
    reasons = []
    evidence = []

    comp = graph_data.get("target_component")
    if comp:
        cust_count = comp.get("distinct_customer_count", comp.get("component_size", 1))
        net_score = score_from_signal(cust_count, "network_component_size")
        linked = [oid for oid in comp.get("linked_order_ids", []) if oid != txn.order_id]
        if net_score > 20:
            reasons.append(f"connected to {cust_count} entities in fraud graph sharing device/phone/address")
            if linked:
                evidence.extend(linked[:10])
        scores.append(net_score)
    else:
        scores.append(0)

    density_score = score_from_signal(cod_density["density_ratio"], "network_cod_density")
    if density_score > 30:
        reasons.append(f"address has {cod_density['address_cod_count']} COD orders ({cod_density['density_ratio']}x baseline)")
    scores.append(density_score)

    final_score = min(100.0, sum(scores) / len(scores))
    return AgentScoreOutput(
        score=round(final_score, 1),
        confidence=0.85,
        explanation="; ".join(reasons) if reasons else "no network signals",
        evidence=evidence,
    )


network_agent_instructions = (
    "You are a network-analysis fraud investigator. Analyze the fraud graph for connected components "
    "sharing devices, phone numbers, or shipping addresses. Detect fraud rings — especially COD fraud rings "
    "where multiple customer accounts share a single device and phone. "
    "Output score 0-100, confidence 0-1, explanation, and evidence list with linked order IDs."
)
network_agent = Agent(
    name="NetworkAgent",
    instructions=network_agent_instructions,
    model="gpt-4o-mini",
    tools=[build_fraud_graph, check_cod_address_density],
    output_type=AgentScoreOutput,
)
