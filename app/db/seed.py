import datetime
from datetime import timezone
import random
import json
import asyncio
from app.db.models import async_session, Transaction, init_db


def make_order_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:04d}"


def generate_clean_orders(count: int = 20) -> list[dict]:
    customers = [f"CUST_{i}" for i in range(1, 11)]
    devices = [f"FP_CLEAN_{i}" for i in range(1, 8)]
    ips = [f"192.168.{random.randint(1, 10)}.{random.randint(1, 255)}" for _ in range(8)]
    phones = [f"+1555{random.randint(100000, 999999)}" for _ in range(10)]
    addresses = [f"{random.randint(100, 9999)} {random.choice(['Oak', 'Elm', 'Maple', 'Pine', 'Cedar'])} St, Portland, OR 972{random.randint(1, 99):02d}" for _ in range(10)]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/17.2",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15",
    ]

    orders = []
    base_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=7)
    for i in range(count):
        cust_idx = i % len(customers)
        orders.append({
            "order_id": make_order_id("CLEAN", i + 1),
            "customer_id": customers[cust_idx],
            "amount": round(random.uniform(15.0, 150.0), 2),
            "currency": "USD",
            "payment_method": random.choice(["card", "wallet", "cod"]),
            "device_fingerprint": devices[cust_idx % len(devices)],
            "ip_address": ips[cust_idx % len(ips)],
            "phone_number": phones[cust_idx % len(phones)],
            "shipping_address": addresses[cust_idx % len(addresses)],
            "user_agent": agents[cust_idx % len(agents)],
            "session_duration_seconds": round(random.uniform(120.0, 900.0), 1),
            "timestamp": base_time + datetime.timedelta(hours=i * 6),
        })
    return orders


def generate_cod_fraud_ring() -> list[dict]:
    shared_device = "FP_FRAUD_DEVICE_001"
    shared_phone = "+15559999999"
    shared_address = "4567 Industrial Blvd, Warehouse 12, Chicago, IL 60601"
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    ]

    orders = []
    base_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=12)
    for i in range(8):
        cid = f"FRAUD_COD_{i + 1}"
        orders.append({
            "order_id": make_order_id("COD-FRAUD", i + 1),
            "customer_id": cid,
            "amount": round(random.uniform(250.0, 950.0), 2),
            "currency": "USD",
            "payment_method": "cod",
            "device_fingerprint": shared_device,
            "ip_address": f"10.0.{random.randint(1, 5)}.{random.randint(1, 254)}",
            "phone_number": shared_phone,
            "shipping_address": shared_address,
            "user_agent": agents[i % len(agents)],
            "session_duration_seconds": round(random.uniform(8.0, 30.0), 1),
            "timestamp": base_time + datetime.timedelta(minutes=random.randint(1, 180)),
        })
    return orders


def generate_card_testing_burst() -> list[dict]:
    device = "FP_CARD_TEST_001"
    orders = []
    base_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=3)
    for i in range(15):
        orders.append({
            "order_id": make_order_id("CARD-TEST", i + 1),
            "customer_id": f"CARDTEST_{random.choice(['A', 'B', 'C'])}",
            "amount": round(random.uniform(1.0, 8.0), 2),
            "currency": "USD",
            "payment_method": "card",
            "device_fingerprint": device,
            "ip_address": f"203.0.113.{random.randint(1, 20)}",
            "phone_number": f"+1555{random.randint(100000, 999999)}",
            "shipping_address": f"{random.randint(100, 9999)} Test Ave, Unit {random.randint(1, 50)}, New York, NY 100{random.randint(1, 19):02d}",
            "user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0",
            "session_duration_seconds": round(random.uniform(3.0, 12.0), 1),
            "timestamp": base_time + datetime.timedelta(minutes=random.randint(1, 120)),
        })
    return orders


def generate_friendly_fraud_pattern() -> list[dict]:
    orders = []
    base = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=60)

    for i in range(6):
        orders.append({
            "order_id": make_order_id("FRIENDLY", i + 1),
            "customer_id": "FRIENDLY_REPEAT_001",
            "amount": round(random.uniform(80.0, 200.0), 2),
            "currency": "USD",
            "payment_method": "cod" if i > 2 else "card",
            "device_fingerprint": f"FP_FRIENDLY_{i + 1}",
            "ip_address": "192.168.1.100",
            "phone_number": "+15557777777",
            "shipping_address": "789 Home Ln, Springfield, IL 62701",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.2",
            "session_duration_seconds": round(random.uniform(200.0, 600.0), 1),
            "timestamp": base + datetime.timedelta(days=i * 7),
        })
    return orders


async def seed_database():
    async with async_session() as session:
        existing = await session.execute(
            __import__("sqlalchemy").select(Transaction).limit(1)
        )
        if existing.scalar_one_or_none():
            print("Database already seeded, skipping.")
            return

    all_orders = []
    all_orders.extend(generate_clean_orders(20))
    all_orders.extend(generate_cod_fraud_ring())
    all_orders.extend(generate_card_testing_burst())
    all_orders.extend(generate_friendly_fraud_pattern())

    random.shuffle(all_orders)

    async with async_session() as session:
        for o in all_orders:
            txn = Transaction(**o)
            session.add(txn)
        await session.commit()

    print(f"Seeded {len(all_orders)} synthetic transactions.")
