import datetime
from datetime import timezone

from agents import function_tool

from app.db.models import async_session, Transaction
from sqlalchemy import select


async def _count_orders(**filters) -> dict:
    now = datetime.datetime.now(timezone.utc)
    windows = {
        "1h": now - datetime.timedelta(hours=1),
        "6h": now - datetime.timedelta(hours=6),
        "24h": now - datetime.timedelta(days=1),
        "7d": now - datetime.timedelta(days=7),
    }
    counts = {}
    async with async_session() as session:
        for label, since in windows.items():
            q = select(Transaction).where(Transaction.timestamp >= since)
            for col, val in filters.items():
                if hasattr(Transaction, col):
                    q = q.where(getattr(Transaction, col) == val)
            result = await session.execute(q)
            rows = result.scalars().all()
            amounts = [t.amount for t in rows]
            counts[label] = {
                "count": len(rows),
                "total_amount": round(sum(amounts), 2),
                "avg_amount": round(sum(amounts) / len(amounts), 2) if amounts else 0,
            }
    return counts


async def _check_customer_velocity(customer_id: str) -> dict:
    return await _count_orders(customer_id=customer_id)


@function_tool
async def check_customer_velocity(customer_id: str) -> dict:
    return await _check_customer_velocity(customer_id)


async def _check_device_velocity(device_fingerprint: str) -> dict:
    return await _count_orders(device_fingerprint=device_fingerprint)


@function_tool
async def check_device_velocity(device_fingerprint: str) -> dict:
    return await _check_device_velocity(device_fingerprint)


async def _check_ip_velocity(ip_address: str) -> dict:
    return await _count_orders(ip_address=ip_address)


@function_tool
async def check_ip_velocity(ip_address: str) -> dict:
    return await _check_ip_velocity(ip_address)


async def _check_phone_velocity(phone_number: str) -> dict:
    return await _count_orders(phone_number=phone_number)


@function_tool
async def check_phone_velocity(phone_number: str) -> dict:
    return await _check_phone_velocity(phone_number)


async def compute_velocity_score(
    customer_id: str,
    device_fingerprint: str,
    ip_address: str,
    phone_number: str,
) -> dict:
    customer_v = await _check_customer_velocity(customer_id)
    device_v = await _check_device_velocity(device_fingerprint)
    ip_v = await _check_ip_velocity(ip_address)
    phone_v = await _check_phone_velocity(phone_number)

    max_1h = max(
        customer_v["1h"]["count"],
        device_v["1h"]["count"],
        ip_v["1h"]["count"],
        phone_v["1h"]["count"],
    )
    max_24h = max(
        customer_v["24h"]["count"],
        device_v["24h"]["count"],
        ip_v["24h"]["count"],
        phone_v["24h"]["count"],
    )

    reasons = []
    scores = []

    if max_1h >= 10:
        scores.append(85)
        reasons.append(f"burst velocity: {max_1h} orders in 1h across customer/device/IP/phone")
    elif max_1h >= 5:
        scores.append(60)
        reasons.append(f"elevated velocity: {max_1h} orders in 1h")
    elif max_1h >= 3:
        scores.append(35)
        reasons.append(f"moderate velocity: {max_1h} orders in 1h")
    else:
        scores.append(0)

    if max_24h >= 20:
        scores.append(80)
        reasons.append(f"high daily velocity: {max_24h} orders in 24h")
    elif max_24h >= 10:
        scores.append(50)
        reasons.append(f"moderate daily velocity: {max_24h} orders in 24h")
    else:
        scores.append(0)

    high_amount_24h = max(
        customer_v["24h"]["total_amount"],
        device_v["24h"]["total_amount"],
        ip_v["24h"]["total_amount"],
        phone_v["24h"]["total_amount"],
    )
    if high_amount_24h > 5000:
        scores.append(40)
        reasons.append(f"high total amount ${high_amount_24h:.0f} in 24h")

    final_score = min(100.0, max(scores) if scores else 0)
    return {
        "score": round(final_score, 1),
        "customer": customer_v,
        "device": device_v,
        "ip": ip_v,
        "phone": phone_v,
        "max_1h": max_1h,
        "max_24h": max_24h,
        "reasons": reasons,
    }
