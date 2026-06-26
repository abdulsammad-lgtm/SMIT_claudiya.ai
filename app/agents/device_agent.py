import random
import datetime
from datetime import timezone
from typing import Optional

from agents import Agent, function_tool, Runner

from app.api.schemas import AgentScoreOutput
from app.db.models import async_session, Transaction
from app.orchestrator.policy import score_from_signal


async def _check_device_fingerprint_reuse(device_fingerprint: str, customer_id: str) -> dict:
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(
                Transaction.device_fingerprint == device_fingerprint,
                Transaction.timestamp >= datetime.datetime.now(timezone.utc) - datetime.timedelta(days=30),
            )
        )
        txns = result.scalars().all()
    distinct_customers = set(t.customer_id for t in txns)
    distinct_customers.discard(customer_id)
    count = len(distinct_customers)
    return {"distinct_customer_count": count, "total_transactions": len(txns)}


@function_tool
async def check_device_fingerprint_reuse(device_fingerprint: str, customer_id: str) -> dict:
    return await _check_device_fingerprint_reuse(device_fingerprint, customer_id)


async def _check_ip_geolocation_mismatch(ip_address: str, shipping_address: str) -> dict:
    mock_ip_region = random.choice(["US-East", "US-West", "US-Central"])
    if "Chicago" in shipping_address or "IL" in shipping_address:
        mock_ip_region = "US-Central"
    elif "Portland" in shipping_address or "OR" in shipping_address:
        mock_ip_region = "US-West"
    elif "New York" in shipping_address or "NY" in shipping_address:
        mock_ip_region = "US-East"
    mismatch = 0.0
    if "IL" in shipping_address and mock_ip_region != "US-Central":
        mismatch = 0.7
    elif "OR" in shipping_address and mock_ip_region != "US-West":
        mismatch = 0.5
    return {"region": mock_ip_region, "mismatch_score": mismatch}


@function_tool
async def check_ip_geolocation_mismatch(ip_address: str, shipping_address: str) -> dict:
    return await _check_ip_geolocation_mismatch(ip_address, shipping_address)


async def _check_proxy_vpn(ip_address: str) -> dict:
    is_proxy = ip_address.startswith("10.") or ip_address.startswith("203.0.113.")
    return {"is_proxy_or_vpn": is_proxy, "confidence": 0.9 if is_proxy else 0.1}


@function_tool
async def check_proxy_vpn(ip_address: str) -> dict:
    return await _check_proxy_vpn(ip_address)


async def _check_user_agent_consistency(user_agent: str, customer_id: str) -> dict:
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(
                Transaction.customer_id == customer_id,
            ).order_by(Transaction.timestamp.desc()).limit(5)
        )
        txns = result.scalars().all()
    prev_agents = set(t.user_agent for t in txns if t.user_agent != user_agent)
    is_known = len(prev_agents) == 0
    anomaly_score = 0.0 if is_known else min(0.8, len(prev_agents) * 0.3)
    return {"is_known_agent": is_known, "previous_agents_count": len(prev_agents), "anomaly_score": anomaly_score}


@function_tool
async def check_user_agent_consistency(user_agent: str, customer_id: str) -> dict:
    return await _check_user_agent_consistency(user_agent, customer_id)


async def fast_path_device(txn: Transaction) -> AgentScoreOutput:
    reuse = await _check_device_fingerprint_reuse(txn.device_fingerprint, txn.customer_id)
    geo = await _check_ip_geolocation_mismatch(txn.ip_address, txn.shipping_address)
    proxy = await _check_proxy_vpn(txn.ip_address)
    ua = await _check_user_agent_consistency(txn.user_agent, txn.customer_id)

    scores = []
    reasons = []

    reuse_score = score_from_signal(reuse["distinct_customer_count"], "device_fingerprint_reuse")
    if reuse_score > 20:
        reasons.append(f"device_fingerprint used by {reuse['distinct_customer_count']} other accounts in 30d")
    scores.append(reuse_score)

    geo_score = geo["mismatch_score"] * 100
    if geo_score > 30:
        reasons.append(f"IP geolocation ({geo['region']}) does not match shipping address")
    scores.append(geo_score)

    proxy_score = (proxy["confidence"] * 100) if proxy["is_proxy_or_vpn"] else 0
    if proxy_score > 30:
        reasons.append("connection appears to be through proxy or VPN")
    scores.append(proxy_score)

    ua_score = ua["anomaly_score"] * 100
    if ua_score > 30:
        reasons.append(f"user_agent differs from {ua['previous_agents_count']} previous sessions")
    scores.append(ua_score)

    final_score = min(100.0, sum(scores) / len(scores))
    return AgentScoreOutput(
        score=round(final_score, 1),
        confidence=0.85,
        explanation="; ".join(reasons) if reasons else "device signals clean",
        evidence=reasons,
    )


device_agent_instructions = (
    "You are a device-risk analyst. Score transactions on device fingerprint reuse, "
    "IP/geolocation mismatch, proxy/VPN risk, and user-agent consistency. "
    "Output a score 0-100, confidence 0-1, and a plain-language explanation."
)
device_agent = Agent(
    name="DeviceAgent",
    instructions=device_agent_instructions,
    model="gpt-4o-mini",
    tools=[check_device_fingerprint_reuse, check_ip_geolocation_mismatch, check_proxy_vpn, check_user_agent_consistency],
    output_type=AgentScoreOutput,
)
