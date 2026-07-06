import time
import json
import asyncio

from agents import Runner

from app.api.schemas import TransactionDecision, AgentScoreOutput, TransactionIn
from app.db.models import async_session, Transaction, AuditLog, DecisionEnum
from app.agents.device_agent import fast_path_device, device_agent, get_device_enrichment
from app.agents.behavior_agent import fast_path_behavior, behavior_agent
from app.agents.network_agent import fast_path_network, network_agent
from app.agents.transaction_agent import fast_path_transaction, transaction_agent
from app.agents.behavioral_agent import fast_path_behavioral, behavioral_agent
from app.orchestrator.policy import FAST_PATH_WEIGHTS, RISK_THRESHOLDS, BASE_CONFIDENCE
from app.guardrail.guardrail import apply_guardrails, compute_reason_codes


async def _run_agent_with_fallback(agent, fast_path_fn, txn, input_text, timeout_sec=30):
    try:
        result = await asyncio.wait_for(
            Runner.run(agent, input_text),
            timeout=timeout_sec,
        )
        return result.final_output
    except Exception:
        return await fast_path_fn(txn)


async def score_transaction(txn_in: TransactionIn, use_reasoning: bool = False) -> TransactionDecision:
    start = time.perf_counter()
    txn = await _get_or_create_txn(txn_in)
    agent_raw = {}

    enrichment = await get_device_enrichment(txn)

    if use_reasoning:
        input_text = f"Score transaction {txn.order_id}"
        tasks = [
            _run_agent_with_fallback(device_agent, fast_path_device, txn, input_text),
            _run_agent_with_fallback(behavior_agent, fast_path_behavior, txn, input_text),
            _run_agent_with_fallback(network_agent, fast_path_network, txn, input_text),
            _run_agent_with_fallback(transaction_agent, fast_path_transaction, txn, input_text),
            _run_agent_with_fallback(behavioral_agent, fast_path_behavioral, txn, input_text),
        ]
        device_score, behavior_score, network_score, transaction_score, behavioral_score = await asyncio.gather(*tasks)
    else:
        device_score = await fast_path_device(txn)
        behavior_score = await fast_path_behavior(txn)
        network_score = await fast_path_network(txn)
        transaction_score = await fast_path_transaction(
            txn,
            ip_country=enrichment.get("ip_country", ""),
            is_vpn=enrichment.get("is_vpn", False),
            is_proxy=enrichment.get("is_proxy", False),
        )
        behavioral_score = await fast_path_behavioral(txn)

    agent_raw["device"] = device_score.model_dump()
    agent_raw["behavior"] = behavior_score.model_dump()
    agent_raw["network"] = network_score.model_dump()
    agent_raw["transaction"] = transaction_score.model_dump()
    agent_raw["behavioral"] = behavioral_score.model_dump()

    agent_scores = {
        "device": device_score.score,
        "behavior": behavior_score.score,
        "network": network_score.score,
        "transaction": transaction_score.score,
        "behavioral": behavioral_score.score,
    }

    all_evidence = (
        (device_score.evidence or [])
        + (behavior_score.evidence or [])
        + (network_score.evidence or [])
        + (transaction_score.evidence or [])
        + (behavioral_score.evidence or [])
    )
    has_hard_block = any("hard_block" in (e or "") for e in all_evidence)

    if has_hard_block:
        raw_risk = max(agent_scores.values())
    else:
        weighted = (
            FAST_PATH_WEIGHTS["device"] * device_score.score
            + FAST_PATH_WEIGHTS["behavior"] * behavior_score.score
            + FAST_PATH_WEIGHTS["network"] * network_score.score
            + FAST_PATH_WEIGHTS["transaction"] * transaction_score.score
            + FAST_PATH_WEIGHTS["behavioral"] * behavioral_score.score
        )
        raw_risk = min(100.0, max(0.0, weighted))

    confidence = min(
        1.0,
        BASE_CONFIDENCE
        * (1.0 - device_score.score / 200)
        * (1.0 - behavior_score.score / 200)
        * (1.0 - network_score.score / 200)
        * (1.0 - transaction_score.score / 200)
        * (1.0 - behavioral_score.score / 200),
    )

    reason_codes = compute_reason_codes(device_score, behavior_score, network_score)
    for s in (transaction_score, behavioral_score):
        if s.score > 20:
            if s.explanation:
                reason_codes.append(s.explanation)
            elif s.evidence:
                reason_codes.extend(s.evidence[:2])

    guardrail_result = await apply_guardrails(
        raw_risk, agent_scores, reason_codes, agent_raw, device_score, behavior_score, network_score, txn
    )

    elapsed = (time.perf_counter() - start) * 1000

    decision = TransactionDecision(
        order_id=txn.order_id,
        decision=guardrail_result["decision"],
        risk_score=round(guardrail_result["risk_score"], 1),
        confidence=round(guardrail_result["confidence"], 2),
        agent_scores=agent_scores,
        reason_codes=guardrail_result["reason_codes"],
        latency_ms=round(elapsed, 1),
    )

    await _persist(txn, decision, agent_raw, guardrail_result)
    return decision


async def _get_or_create_txn(txn_in: TransactionIn) -> Transaction:
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Transaction).where(Transaction.order_id == txn_in.order_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.card_bin = txn_in.card_bin or existing.card_bin
            existing.card_last4 = txn_in.card_last4 or existing.card_last4
            existing.cvv_provided = txn_in.cvv_provided
            existing.avs_result = txn_in.avs_result or existing.avs_result
            existing.billing_address = txn_in.billing_address or existing.billing_address
            existing.billing_country = txn_in.billing_country or existing.billing_country
            existing.billing_zip = txn_in.billing_zip or existing.billing_zip
            existing.shipping_country = txn_in.shipping_country or existing.shipping_country
            existing.shipping_zip = txn_in.shipping_zip or existing.shipping_zip
            existing.merchant_id = txn_in.merchant_id or existing.merchant_id
            existing.merchant_category = txn_in.merchant_category or existing.merchant_category
            return existing
        txn = Transaction(
            order_id=txn_in.order_id,
            customer_id=txn_in.customer_id,
            amount=txn_in.amount,
            currency=txn_in.currency,
            payment_method=txn_in.payment_method,
            device_fingerprint=txn_in.device_fingerprint,
            ip_address=txn_in.ip_address,
            phone_number=txn_in.phone_number,
            shipping_address=txn_in.shipping_address,
            user_agent=txn_in.user_agent,
            session_duration_seconds=txn_in.session_duration_seconds,
            timestamp=txn_in.timestamp,
            card_bin=txn_in.card_bin or "",
            card_last4=txn_in.card_last4 or "",
            cvv_provided=txn_in.cvv_provided,
            avs_result=txn_in.avs_result,
            billing_address=txn_in.billing_address or "",
            billing_country=txn_in.billing_country or "",
            billing_zip=txn_in.billing_zip or "",
            shipping_country=txn_in.shipping_country or "",
            shipping_zip=txn_in.shipping_zip or "",
            merchant_id=txn_in.merchant_id or "",
            merchant_category=txn_in.merchant_category or "",
        )
        session.add(txn)
        await session.commit()
        return txn


async def _persist(txn: Transaction, decision: TransactionDecision, agent_raw: dict, guardrail_result: dict):
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Transaction).where(Transaction.order_id == txn.order_id)
        )
        db_txn = result.scalar_one_or_none()
        if db_txn:
            db_txn.decision = decision.decision
            db_txn.risk_score = decision.risk_score
            db_txn.confidence = decision.confidence
            db_txn.agent_scores_json = json.dumps(decision.agent_scores)
            db_txn.reason_codes_json = json.dumps(decision.reason_codes)
            db_txn.latency_ms = decision.latency_ms
            db_txn.scoring_path = guardrail_result.get("scoring_path", "fast")

        audit = AuditLog(
            order_id=txn.order_id,
            event_type="score",
            new_decision=decision.decision,
            details_json=json.dumps({
                "agent_scores": decision.agent_scores,
                "risk_score": decision.risk_score,
                "confidence": decision.confidence,
                "reason_codes": decision.reason_codes,
                "agent_raw": agent_raw,
                "guardrail_applied": guardrail_result.get("guardrail_applied", False),
            }),
        )
        session.add(audit)
        await session.commit()
