from agents import Agent, function_tool, Runner

from app.api.schemas import AgentScoreOutput
from app.db.models import Transaction
from app.orchestrator.policy import score_from_signal
from app.tools.fraud_patterns import (
    _detect_card_testing,
    _detect_cod_ring,
    _detect_friendly_fraud,
    _detect_triangulation,
    score_fraud_patterns,
)
from app.tools.velocity_checker import _check_customer_velocity, _check_device_velocity, compute_velocity_score
from app.tools.fraud_patterns import (
    detect_card_testing_pattern,
    detect_cod_fraud_ring,
    detect_friendly_fraud,
    detect_triangulation,
)
from app.tools.velocity_checker import (
    check_customer_velocity,
    check_device_velocity,
    check_ip_velocity,
    check_phone_velocity,
)


async def fast_path_transaction(txn: Transaction) -> AgentScoreOutput:
    card_testing = await _detect_card_testing(txn.device_fingerprint, txn.amount)
    cod_ring = await _detect_cod_ring(txn.phone_number, txn.shipping_address)
    friendly = await _detect_friendly_fraud(txn.customer_id)
    triangulation = await _detect_triangulation(
        txn.ip_address, txn.shipping_address, txn.amount, txn.device_fingerprint
    )
    velocity = await compute_velocity_score(
        txn.customer_id, txn.device_fingerprint, txn.ip_address, txn.phone_number
    )

    scores = []
    reasons = []

    ct_count = card_testing.get("small_txns_count", 0)
    ct_score = score_from_signal(float(ct_count), "card_testing_small_txn_count")
    if ct_score > 20:
        reasons.append(f"card testing: {ct_count} small transactions from device {txn.device_fingerprint}")
    scores.append(ct_score)

    ring_count = cod_ring.get("linked_customer_count", 0)
    ring_score = score_from_signal(float(ring_count), "cod_ring_linked_customers")
    if ring_score > 20:
        reasons.append(f"COD ring: {ring_count} customers linked by phone/address")
    scores.append(ring_score)

    friendly_cod = friendly.get("high_value_cod_orders", 0)
    friendly_score = score_from_signal(float(friendly_cod), "friendly_fraud_cod_orders")
    if friendly_score > 20 and friendly.get("recently_switched_to_cod"):
        reasons.append(f"friendly fraud: {friendly_cod} high-value COD orders, recently switched to COD")
    scores.append(friendly_score)

    addr_count = triangulation.get("distinct_addresses_on_device", 0)
    tri_score = score_from_signal(float(addr_count), "triangulation_address_count")
    if tri_score > 20:
        reasons.append(f"triangulation: {addr_count} different addresses on device {txn.device_fingerprint}")
    scores.append(tri_score)

    vel_score = score_from_signal(float(velocity["max_1h"]), "velocity_burst_1h")
    if vel_score > 20:
        reasons.append(f"velocity burst: {velocity['max_1h']} orders in 1h")
    scores.append(vel_score)

    daily_score = score_from_signal(float(velocity["max_24h"]), "velocity_daily_24h")
    if daily_score > 20:
        reasons.append(f"daily velocity: {velocity['max_24h']} orders in 24h")
    scores.append(daily_score)

    final_score = min(100.0, sum(scores) / len(scores))
    return AgentScoreOutput(
        score=round(final_score, 1),
        confidence=0.85,
        explanation="; ".join(reasons) if reasons else "transaction signals clean",
        evidence=reasons,
    )


transaction_agent_instructions = (
    "You are a transaction fraud analyst. Analyze individual transactions for fraud signals including:\n"
    "- Card testing patterns (multiple small amounts from same device)\n"
    "- COD fraud rings (multiple customers sharing phone/address for COD orders)\n"
    "- Friendly fraud (COD refusal patterns)\n"
    "- Triangulation fraud (same device shipping to many addresses)\n"
    "- Velocity bursts (many orders in short time windows)\n"
    "Output a score 0-100, confidence 0-1, and a plain-language explanation."
)
transaction_agent = Agent(
    name="TransactionAgent",
    instructions=transaction_agent_instructions,
    model="gpt-4o-mini",
    tools=[
        detect_card_testing_pattern,
        detect_cod_fraud_ring,
        detect_friendly_fraud,
        detect_triangulation,
        check_customer_velocity,
        check_device_velocity,
        check_ip_velocity,
        check_phone_velocity,
    ],
    output_type=AgentScoreOutput,
)
