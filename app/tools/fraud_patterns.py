import datetime
from datetime import timezone

from agents import function_tool

from app.db.models import async_session, Transaction
from sqlalchemy import select


async def _get_recent_txns(**filters) -> list:
    async with async_session() as session:
        q = select(Transaction).where(
            Transaction.timestamp >= datetime.datetime.now(timezone.utc) - datetime.timedelta(days=7),
        )
        for col, val in filters.items():
            if hasattr(Transaction, col):
                q = q.where(getattr(Transaction, col) == val)
        result = await session.execute(q)
        return result.scalars().all()


async def _detect_card_testing(device_fingerprint: str, amount: float, threshold: float = 20.0) -> dict:
    recent = await _get_recent_txns(device_fingerprint=device_fingerprint)
    small_txns = [t for t in recent if t.amount < threshold]
    amounts = [t.amount for t in small_txns]
    distinct_cards = len(set(t.payment_method for t in small_txns))
    return {
        "total_recent": len(recent),
        "small_txns_count": len(small_txns),
        "small_txn_amounts": [round(a, 2) for a in amounts[:10]],
        "distinct_payment_methods": distinct_cards,
        "avg_amount": round(sum(amounts) / len(amounts), 2) if amounts else 0,
        "is_card_testing_pattern": len(amounts) >= 5 and all(a < threshold for a in amounts),
    }


@function_tool
async def detect_card_testing_pattern(device_fingerprint: str, amount: float) -> dict:
    return await _detect_card_testing(device_fingerprint, amount)


async def _detect_cod_ring(phone_number: str, shipping_address: str) -> dict:
    recent = await _get_recent_txns()
    cod_txns = [t for t in recent if t.payment_method == "cod"]
    addr_norm = shipping_address.strip().lower()
    same_address = [t for t in cod_txns if t.shipping_address.strip().lower() == addr_norm]
    same_phone = [t for t in cod_txns if t.phone_number == phone_number]
    linked_customers = set(t.customer_id for t in same_address + same_phone)
    linked_customers.discard("")
    return {
        "cod_orders_total": len(cod_txns),
        "same_address_orders": len(same_address),
        "same_phone_orders": len(same_phone),
        "linked_customer_count": len(linked_customers),
        "linked_customers": list(linked_customers)[:10],
        "total_linked_amount": round(sum(t.amount for t in same_address + same_phone), 2),
    }


@function_tool
async def detect_cod_fraud_ring(phone_number: str, shipping_address: str) -> dict:
    return await _detect_cod_ring(phone_number, shipping_address)


async def _detect_friendly_fraud(customer_id: str) -> dict:
    recent = await _get_recent_txns(customer_id=customer_id)
    cod_txns = [t for t in recent if t.payment_method == "cod"]
    cod_count = len(cod_txns)
    high_value_cod = [t for t in cod_txns if t.amount > 100]
    history_span_days = 0
    if len(recent) >= 2:
        span = (recent[-1].timestamp - recent[0].timestamp).total_seconds()
        history_span_days = round(span / 86400, 1)
    return {
        "total_orders": len(recent),
        "cod_orders": cod_count,
        "high_value_cod_orders": len(high_value_cod),
        "total_cod_amount": round(sum(t.amount for t in cod_txns), 2),
        "history_span_days": history_span_days,
        "first_payment_method": recent[0].payment_method if recent else None,
        "recently_switched_to_cod": cod_count > 0 and (recent[0].payment_method != "cod" if recent else False),
    }


@function_tool
async def detect_friendly_fraud(customer_id: str) -> dict:
    return await _detect_friendly_fraud(customer_id)


async def _detect_triangulation(ip_address: str, shipping_address: str, amount: float, device_fingerprint: str) -> dict:
    recent = await _get_recent_txns()
    high_value = amount > 500
    ip_txns = [t for t in recent if t.ip_address == ip_address]
    device_txns = [t for t in recent if t.device_fingerprint == device_fingerprint]
    addresses_used = set(t.shipping_address.strip().lower() for t in device_txns)
    return {
        "is_high_value": high_value,
        "distinct_addresses_on_device": len(addresses_used),
        "orders_from_this_ip": len(ip_txns),
        "orders_from_this_device": len(device_txns),
        "different_addresses": list(addresses_used)[:5],
        "is_triangulation_pattern": high_value and len(addresses_used) >= 3,
    }


@function_tool
async def detect_triangulation(ip_address: str, shipping_address: str, amount: float, device_fingerprint: str) -> dict:
    return await _detect_triangulation(ip_address, shipping_address, amount, device_fingerprint)


async def score_fraud_patterns(
    txn,
    card_testing: dict | None = None,
    cod_ring: dict | None = None,
    friendly: dict | None = None,
    triangulation: dict | None = None,
) -> dict:
    scores = []
    reasons = []

    if card_testing and card_testing.get("is_card_testing_pattern"):
        count = card_testing["small_txns_count"]
        score = min(80, 20 + count * 5)
        scores.append(score)
        reasons.append(f"card testing pattern: {count} small transactions from same device")
    else:
        scores.append(0)

    if cod_ring and cod_ring.get("linked_customer_count", 0) > 1:
        count = cod_ring["linked_customer_count"]
        score = min(90, 30 + count * 10)
        scores.append(score)
        reasons.append(f"COD fraud ring: {count} customers linked by phone/address")
    else:
        scores.append(0)

    if friendly and friendly.get("high_value_cod_orders", 0) > 2:
        score = min(70, 30 + friendly["high_value_cod_orders"] * 5)
        scores.append(score)
        cod_count = friendly["cod_orders"]
        reasons.append(f"friendly fraud pattern: {cod_count} COD orders, {friendly['high_value_cod_orders']} high-value")
    else:
        scores.append(0)

    if triangulation and triangulation.get("is_triangulation_pattern"):
        score = 65
        scores.append(score)
        addrs = triangulation["distinct_addresses_on_device"]
        reasons.append(f"triangulation fraud: {addrs} different shipping addresses on same device")
    else:
        scores.append(0)

    final_score = min(100.0, sum(scores) / max(len([s for s in scores if s > 0]), 1))
    return {
        "score": round(final_score, 1),
        "reasons": reasons,
    }
