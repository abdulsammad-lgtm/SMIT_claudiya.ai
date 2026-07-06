import json
import datetime
import random
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import TransactionIn, TransactionDecision, OverrideRequest
from app.db.models import async_session, Transaction, AuditLog, User
from app.orchestrator.orchestrator import score_transaction
from app.agents.orchestrator import RiskOrchestrator
from app.services.risk_engine import ScoringStrategy
from app.core.dependencies import optional_user, require_user
from app.cache.redis_client import redis_client
from app.db.seed import (
    generate_clean_orders,
    generate_cod_fraud_ring,
    generate_card_testing_burst,
    generate_friendly_fraud_pattern,
    seed_database as run_full_seed,
)
from app.api.ws import notify_new_transaction

router = APIRouter()

# Simple in-memory rate limiting
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60.0
RATE_LIMIT_MAX = 30


def _check_rate_limit(api_key: str) -> bool:
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if api_key not in _rate_limit_store:
        _rate_limit_store[api_key] = []
    timestamps = _rate_limit_store[api_key]
    timestamps[:] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(timestamps) >= RATE_LIMIT_MAX:
        return False
    timestamps.append(now)
    return True


@router.post("/score")
async def score_endpoint(
    txn_in: TransactionIn,
    request: Request,
    user=Depends(optional_user),
) -> TransactionDecision:
    api_key = request.headers.get("X-Api-Key", "default")
    if not _check_rate_limit(api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    use_reasoning = request.query_params.get("reasoning", "").lower() == "true"
    use_v2 = request.query_params.get("v2", "").lower() == "true"
    strategy = request.query_params.get("strategy", "weighted")

    if use_v2:
        strat_map = {
            "weighted": ScoringStrategy.WEIGHTED,
            "max": ScoringStrategy.MAX,
            "ensemble": ScoringStrategy.ENSEMBLE,
        }
        orchestrator = RiskOrchestrator()
        decision = await orchestrator.score_with_plan(
            txn_in,
            strategy=strat_map.get(strategy, ScoringStrategy.WEIGHTED),
            use_reasoning=use_reasoning,
        )
    else:
        decision = await score_transaction(txn_in, use_reasoning=use_reasoning)

    await notify_new_transaction(decision.model_dump())
    return decision


@router.get("/transactions")
async def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=500),
    status: Optional[str] = None,
):
    async with async_session() as session:
        base = select(Transaction)
        if status and status in ("approve", "review", "decline", "pending"):
            base = base.where(Transaction.decision == status)
        total_q = select(func.count()).select_from(base.subquery())
        total = (await session.execute(total_q)).scalar() or 0
        result = await session.execute(
            base.order_by(desc(Transaction.timestamp))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        txns = result.scalars().all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "transactions": [
            {
                "order_id": t.order_id,
                "customer_id": t.customer_id,
                "amount": t.amount,
                "currency": t.currency,
                "payment_method": t.payment_method,
                "decision": t.decision,
                "risk_score": t.risk_score,
                "confidence": t.confidence,
                "agent_scores": json.loads(t.agent_scores_json) if t.agent_scores_json else {},
                "reason_codes": json.loads(t.reason_codes_json) if t.reason_codes_json else [],
                "latency_ms": t.latency_ms,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                "overridden": bool(t.overridden),
            }
            for t in txns
        ],
    }


@router.get("/transactions/{order_id}")
async def get_transaction(order_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.order_id == order_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {
            "order_id": txn.order_id,
            "customer_id": txn.customer_id,
            "amount": txn.amount,
            "currency": txn.currency,
            "payment_method": txn.payment_method,
            "device_fingerprint": txn.device_fingerprint,
            "ip_address": txn.ip_address,
            "phone_number": txn.phone_number,
            "shipping_address": txn.shipping_address,
            "user_agent": txn.user_agent,
            "session_duration_seconds": txn.session_duration_seconds,
            "card_bin": txn.card_bin,
            "card_last4": txn.card_last4,
            "cvv_provided": bool(txn.cvv_provided),
            "avs_result": txn.avs_result,
            "billing_address": txn.billing_address,
            "billing_country": txn.billing_country,
            "billing_zip": txn.billing_zip,
            "shipping_country": txn.shipping_country,
            "shipping_zip": txn.shipping_zip,
            "merchant_id": txn.merchant_id,
            "merchant_category": txn.merchant_category,
            "device_ip_country": txn.device_ip_country,
            "device_is_vpn": bool(txn.device_is_vpn) if txn.device_is_vpn is not None else None,
            "device_is_proxy": bool(txn.device_is_proxy) if txn.device_is_proxy is not None else None,
            "decision": txn.decision,
            "risk_score": txn.risk_score,
            "confidence": txn.confidence,
            "agent_scores": json.loads(txn.agent_scores_json) if txn.agent_scores_json else {},
            "reason_codes": json.loads(txn.reason_codes_json) if txn.reason_codes_json else [],
            "latency_ms": txn.latency_ms,
            "timestamp": txn.timestamp.isoformat() if txn.timestamp else None,
            "overridden": bool(txn.overridden),
            "override_decision": txn.override_decision,
        }


@router.post("/transactions/{order_id}/override")
async def override_decision(order_id: str, override: OverrideRequest):
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.order_id == order_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        prev = txn.decision
        txn.overridden = 1
        txn.override_decision = override.decision
        txn.decision = override.decision

        audit = AuditLog(
            order_id=order_id,
            event_type="override",
            previous_decision=prev,
            new_decision=override.decision,
            details_json=json.dumps({
                "reason": override.reason,
                "analyst": override.analyst,
            }),
        )
        session.add(audit)
        await session.commit()

    return {"status": "ok", "order_id": order_id, "decision": override.decision}


@router.get("/stats")
async def get_stats():
    async with async_session() as session:
        counts = {}
        for status in ("approve", "review", "decline", "pending"):
            q = select(func.count()).select_from(
                select(Transaction).where(Transaction.decision == status).subquery()
            )
            result = await session.execute(q)
            counts[status] = result.scalar() or 0

        total_q = select(func.count()).select_from(select(Transaction).subquery())
        total = (await session.execute(total_q)).scalar() or 0

    return {"total": total, "counts": counts}


@router.get("/risk-distribution")
async def risk_distribution():
    async with async_session() as session:
        txns = (await session.execute(select(Transaction))).scalars().all()
    bins = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for t in txns:
        if t.risk_score is not None:
            bucket = min(int(t.risk_score // 20), 4)
            lo = bucket * 20 + 1
            hi = (bucket + 1) * 20
            key = "0-20" if bucket == 0 else f"{lo}-{hi}"
            if key in bins:
                bins[key] += 1
    return {"bins": bins}


AGENT_NAMES = ["device", "behavior", "network", "transaction", "behavioral"]


@router.get("/agents/status")
async def agents_status():
    async with async_session() as session:
        txns = (await session.execute(
            select(Transaction).where(Transaction.decision != "pending").order_by(desc(Transaction.id)).limit(200)
        )).scalars().all()

    agents = {}
    for name in AGENT_NAMES:
        scores = []
        latencies = []
        for t in txns:
            try:
                ag = json.loads(t.agent_scores_json) if t.agent_scores_json else {}
                if name in ag:
                    scores.append(ag[name])
                    latencies.append(t.latency_ms or 0)
            except (json.JSONDecodeError, TypeError):
                continue
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0
        agents[name] = {
            "online": True,
            "total_scored": len(scores),
            "avg_score": avg_score,
            "avg_latency_ms": avg_latency,
            "weight": 0,
        }

    async with async_session() as session:
        total = (await session.execute(select(func.count()).select_from(select(Transaction).subquery()))).scalar() or 0

    from app.orchestrator.policy import FAST_PATH_WEIGHTS
    for name in AGENT_NAMES:
        agents[name]["weight"] = FAST_PATH_WEIGHTS.get(name, 0)

    return {
        "agents": agents,
        "total_transactions": total,
    }


@router.post("/generate")
async def generate_data(payload: dict):
    pattern = payload.get("pattern", "clean")
    count = min(payload.get("count", 20), 200)

    pattern_map = {
        "clean": generate_clean_orders,
        "cod_fraud": generate_cod_fraud_ring,
        "card_testing": generate_card_testing_burst,
        "friendly_fraud": generate_friendly_fraud_pattern,
    }

    generator = pattern_map.get(pattern)
    if not generator:
        raise HTTPException(status_code=400, detail=f"Unknown pattern: {pattern}")

    if pattern == "clean":
        items = generator(count)
    else:
        rings = []
        for _ in range(max(1, count // 10)):
            rings.extend(generator())
        items = rings[:count]

    ts_suffix = datetime.datetime.utcnow().strftime("%H%M%S")

    inserted = 0
    async with async_session() as session:
        for i, item in enumerate(items):
            txn = Transaction(
                order_id=f"{item['order_id']}-{ts_suffix}-{i}",
                customer_id=item["customer_id"],
                amount=item["amount"],
                currency=item.get("currency", "USD"),
                payment_method=item["payment_method"],
                device_fingerprint=item["device_fingerprint"],
                ip_address=item["ip_address"],
                phone_number=item["phone_number"],
                shipping_address=item["shipping_address"],
                user_agent=item["user_agent"],
                session_duration_seconds=item["session_duration_seconds"],
                timestamp=item.get("timestamp", datetime.datetime.utcnow()),
            )
            session.add(txn)
            inserted += 1
        await session.commit()

    return {"status": "ok", "pattern": pattern, "inserted": inserted}


@router.post("/generate/score-all")
async def generate_and_score(payload: dict = {}):
    count = min(payload.get("count", 10), 100)
    pattern = payload.get("pattern", "clean")
    score_all = payload.get("score", True)

    generatormap = {
        "clean": generate_clean_orders,
        "cod_fraud": generate_cod_fraud_ring,
        "card_testing": generate_card_testing_burst,
        "friendly_fraud": generate_friendly_fraud_pattern,
    }

    gen = generatormap.get(pattern, generate_clean_orders)
    items = gen(count) if pattern == "clean" else gen()[:count]
    for _ in range(len(items), count):
        items.append(generate_clean_orders(1)[0])

    ts_suffix = datetime.datetime.utcnow().strftime("%H%M%S")
    results = []
    async with async_session() as session:
        for i, item in enumerate(items):
            txn = Transaction(
                order_id=f"{item['order_id']}-{ts_suffix}-{i}",
                customer_id=item["customer_id"],
                amount=item["amount"],
                currency=item.get("currency", "USD"),
                payment_method=item["payment_method"],
                device_fingerprint=item["device_fingerprint"],
                ip_address=item["ip_address"],
                phone_number=item["phone_number"],
                shipping_address=item["shipping_address"],
                user_agent=item["user_agent"],
                session_duration_seconds=item["session_duration_seconds"],
                timestamp=item.get("timestamp", datetime.datetime.utcnow()),
            )
            session.add(txn)
            await session.commit()

            if score_all:
                from app.api.schemas import TransactionIn as TIn
                txn_in = TIn(
                    order_id=txn.order_id,
                    customer_id=txn.customer_id,
                    amount=txn.amount,
                    currency=txn.currency,
                    payment_method=txn.payment_method,
                    device_fingerprint=txn.device_fingerprint,
                    ip_address=txn.ip_address,
                    phone_number=txn.phone_number,
                    shipping_address=txn.shipping_address,
                    user_agent=txn.user_agent,
                    session_duration_seconds=txn.session_duration_seconds,
                    timestamp=txn.timestamp or datetime.datetime.utcnow(),
                )
                try:
                    decision = await score_transaction(txn_in)
                    txn.decision = decision.decision
                    txn.risk_score = decision.risk_score
                    txn.confidence = decision.confidence
                    txn.agent_scores_json = json.dumps(decision.agent_scores)
                    txn.reason_codes_json = json.dumps(decision.reason_codes)
                    txn.latency_ms = decision.latency_ms
                    await session.commit()
                    results.append({
                        "order_id": txn.order_id,
                        "decision": decision.decision,
                        "risk_score": decision.risk_score,
                        "latency_ms": decision.latency_ms,
                    })
                except Exception as e:
                    results.append({"order_id": txn.order_id, "error": str(e)})

    return {
        "status": "ok",
        "pattern": pattern,
        "inserted": len(items),
        "scored": len(results),
        "results": results,
    }
