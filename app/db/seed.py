import datetime
from datetime import timezone
import random
import json
import asyncio
from app.db.models import async_session, Transaction, init_db


def make_order_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:04d}"


CARD_BINS_REAL = [
    "414720", "414721", "414722",  # Visa (real issuers)
    "517805", "517806",             # Mastercard
    "371449", "371450",             # Amex
    "601100", "601101",             # Discover
    "400000",                        # Visa test (won't resolve in BIN lookup)
]

MERCHANT_CATS_LOW_RISK = ["books", "groceries", "home_goods", "utilities", "clothing"]
MERCHANT_CATS_MED_RISK = ["clothing", "home_goods", "electronics"]
MERCHANT_CATS_HIGH_RISK = ["electronics", "jewelry", "luxury_goods", "gift_cards", "crypto"]

REGIONS = ["US-East", "US-Central", "US-West", "EU-West", "APAC"]
REGION_COUNTRY = {
    "US-East": "US", "US-Central": "US", "US-West": "US",
    "EU-West": "GB", "APAC": "JP",
}

def _weighted_choice(items: list, weights: list | None = None):
    if weights:
        return random.choices(items, weights=weights, k=1)[0]
    return random.choice(items)

def _random_amount(low: float, high: float, lognormal: bool = False) -> float:
    if lognormal:
        return round(random.lognormvariate(4.0, 0.7), 2)
    return round(random.uniform(low, high), 2)

def _random_zip() -> str:
    return f"{random.randint(10000, 99999)}"

def _random_billing_avs(clean: bool) -> tuple[str, bool, str]:
    """Returns (avs_result, cvv_provided, billing_zip_match_ratio)."""
    if clean:
        r = random.random()
        if r < 0.82:      return ("Y", True, "")
        elif r < 0.88:    return ("A", True, "")   # street match only
        elif r < 0.93:    return ("Z", True, "")   # zip match only
        elif r < 0.97:    return ("Y", False, "")  # user forgot CVV
        else:             return ("N", True, "")   # address mismatch (real false positive)
    else:
        r = random.random()
        if r < 0.18:      return ("Y", True, "")   # stolen card with full data
        elif r < 0.30:    return ("A", True, "")
        elif r < 0.38:    return ("Z", True, "")
        elif r < 0.60:    return ("N", False, "")  # no CVV + no match
        elif r < 0.80:    return ("N", True, "")   # no address match but has CVV
        else:             return ("U", False, "")  # unavailable

def _random_vpn_proxy(clean: bool) -> tuple[bool, bool]:
    if clean:
        return (random.random() < 0.035, random.random() < 0.012)
    else:
        return (random.random() < 0.38, random.random() < 0.22)

def _random_billing_shipping_countries(clean: bool) -> tuple[str, str]:
    """Returns (billing_country, shipping_country)."""
    if clean:
        r = random.random()
        if r < 0.85:
            return ("US", "US")
        elif r < 0.92:
            return ("US", "US")  # same country, different region (below handled by zip)
        elif r < 0.96:
            return ("US", "CA")  # Canada
        elif r < 0.98:
            return ("US", "GB")  # UK
        else:
            return ("US", _weighted_choice(["DE", "AU", "JP", "FR"], [3, 2, 1, 1]))
    else:
        r = random.random()
        if r < 0.35:
            return ("US", "US")  # domestic fraud
        elif r < 0.50:
            return ("US", _weighted_choice(["CN", "NG", "RU", "PK"], [4, 3, 2, 1]))
        elif r < 0.70:
            return ("US", _weighted_choice(["CA", "GB", "AU"], [3, 2, 1]))
        else:
            return (_weighted_choice(["US", "GB", "CA", "AU"], [5, 2, 2, 1]),
                    _weighted_choice(["US", "CN", "NG", "RU"], [3, 3, 2, 2]))


def generate_clean_orders(count: int = 20) -> list[dict]:
    customers = [f"CUST_{i}" for i in range(1, 11)]
    ips = ["192.168.1.100", "10.0.0.50", "172.16.0.25", "203.0.113.10",
           "198.51.100.20", "192.0.2.30", "8.8.8.8", "1.1.1.1",
           "104.16.0.1", "151.101.0.1"]
    phones = [f"+1555{random.randint(100000, 999999)}" for _ in range(10)]
    base_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=7)

    orders = []
    for i in range(count):
        cust_idx = i % len(customers)
        device = f"FP_CLEAN_{cust_idx + 1}"

        billing_country, shipping_country = _random_billing_shipping_countries(clean=True)
        avs, cvv_provided, _ = _random_billing_avs(clean=True)
        is_vpn, is_proxy = _random_vpn_proxy(clean=True)
        shipping_addr = f"{random.randint(100, 9999)} {random.choice(['Oak', 'Elm', 'Maple', 'Pine', 'Cedar'])} St"
        billing_addr = shipping_addr if billing_country == shipping_country else f"{random.randint(100, 9999)} {random.choice(['Main', 'Broad', 'Park'])} Ave"
        billing_zip = _random_zip()
        shipping_zip = billing_zip if (billing_country == shipping_country and random.random() < 0.82) else _random_zip()

        a = _random_amount(low=12.0, high=200.0, lognormal=True)
        orders.append({
            "order_id": make_order_id("CLEAN", i + 1),
            "customer_id": customers[cust_idx],
            "amount": a,
            "currency": "USD",
            "payment_method": _weighted_choice(["card", "wallet", "cod"], [7, 2, 1]),
            "device_fingerprint": device,
            "ip_address": ips[cust_idx % len(ips)],
            "phone_number": phones[cust_idx % len(phones)],
            "shipping_address": f"{shipping_addr}, {_weighted_choice(['Portland, OR', 'Chicago, IL', 'New York, NY', 'Austin, TX', 'Seattle, WA'])} {shipping_zip}",
            "user_agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) Safari/605.1.15",
            ]),
            "session_duration_seconds": round(random.uniform(90.0, 1200.0), 1),
            "timestamp": base_time + datetime.timedelta(hours=i * 6 + random.randint(-30, 30)),
            "card_bin": random.choice(CARD_BINS_REAL),
            "card_last4": f"{random.randint(1000, 9999)}",
            "cvv_provided": 1 if cvv_provided else 0,
            "avs_result": avs,
            "billing_address": billing_addr,
            "billing_country": billing_country,
            "billing_zip": billing_zip,
            "shipping_country": shipping_country,
            "shipping_zip": shipping_zip,
            "merchant_id": f"M{random.randint(100, 500):03d}",
            "merchant_category": _weighted_choice(
                MERCHANT_CATS_LOW_RISK + MERCHANT_CATS_MED_RISK,
                [5, 4, 3, 2, 3, 2, 1, 1],
            ),
        })
    return orders


def generate_cod_fraud_ring() -> list[dict]:
    shared_device = "FP_FRAUD_RING_001"
    shared_phone = "+15559999999"
    shared_address = "4567 Industrial Blvd, Warehouse 12, Chicago, IL 60601"
    base_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=12)

    orders = []
    for i in range(8):
        cid = f"FRAUD_COD_{i + 1}"
        orders.append({
            "order_id": make_order_id("COD-FRAUD", i + 1),
            "customer_id": cid,
            "amount": round(random.uniform(200.0, 900.0), 2),
            "currency": "USD",
            "payment_method": "cod",
            "device_fingerprint": shared_device,
            "ip_address": f"10.0.{random.randint(1, 5)}.{random.randint(1, 254)}",
            "phone_number": shared_phone,
            "shipping_address": shared_address,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "session_duration_seconds": round(random.uniform(5.0, 25.0), 1),
            "timestamp": base_time + datetime.timedelta(minutes=random.randint(1, 180)),
            "card_bin": "",
            "card_last4": "",
            "cvv_provided": 0,
            "avs_result": "U",
            "billing_address": "",
            "billing_country": "",
            "billing_zip": "",
            "shipping_country": "US",
            "shipping_zip": "60601",
            "merchant_id": "M999",
            "merchant_category": "electronics",
        })
    return orders


def generate_card_testing_burst() -> list[dict]:
    device = "FP_CARD_TEST_001"
    shared_ip = "203.0.113.42"
    base_time = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=3)

    orders = []
    for i in range(15):
        is_micro = i < 12
        amount = round(random.uniform(0.50, 1.00), 2) if is_micro else round(random.uniform(200.0, 600.0), 2)
        attempts = [
            "N", "N", "N", "N", "N", "Z",  # micro txns: mostly N (card not valid)
            "N",                             # last micro: still N
            "N", "Z", "N", "A",
            "Z", "N", "Y",                   # larger txns: varied
        ]
        orders.append({
            "order_id": make_order_id("CARD-TEST", i + 1),
            "customer_id": random.choice(["CARDTEST_A", "CARDTEST_B", "CARDTEST_C"]),
            "amount": amount,
            "currency": "USD",
            "payment_method": "card",
            "device_fingerprint": device,
            "ip_address": shared_ip,
            "phone_number": f"+1555{random.randint(100000, 999999)}",
            "shipping_address": f"{random.randint(100, 9999)} Fake Ave, Unit {i+1}, Portland, OR 972{random.randint(1, 99):02d}",
            "user_agent": "Mozilla/5.0 (Linux; Android 14) Chrome/120.0.0.0 Safari/537.36",
            "session_duration_seconds": round(random.uniform(2.0, 8.0), 1),
            "timestamp": base_time + datetime.timedelta(minutes=random.randint(0, 120)),
            "card_bin": random.choice(["411111", "550000", "340000"]),
            "card_last4": f"{random.randint(1000, 9999)}",
            "cvv_provided": 1 if not is_micro else 0,
            "avs_result": attempts[i] if i < len(attempts) else "N",
            "billing_address": f"{random.randint(100, 9999)} Stolen St",
            "billing_country": "US",
            "billing_zip": "97222",
            "shipping_country": "US",
            "shipping_zip": "97222",
            "merchant_id": "M666",
            "merchant_category": "electronics",
        })
    return orders


def generate_friendly_fraud_pattern() -> list[dict]:
    base = datetime.datetime.now(timezone.utc) - datetime.timedelta(days=60)
    orders = []
    for i in range(6):
        is_cod = i > 2
        orders.append({
            "order_id": make_order_id("FRIENDLY", i + 1),
            "customer_id": "FRIENDLY_REPEAT_001",
            "amount": round(random.uniform(80.0, 220.0), 2),
            "currency": "USD",
            "payment_method": "cod" if is_cod else "card",
            "device_fingerprint": f"FP_FRIENDLY_{i + 1}",
            "ip_address": "192.168.1.100",
            "phone_number": "+15557777777",
            "shipping_address": "789 Home Ln, Springfield, IL 62701",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
            "session_duration_seconds": round(random.uniform(180.0, 600.0), 1),
            "timestamp": base + datetime.timedelta(days=i * 7 + random.randint(-1, 1)),
            "card_bin": random.choice(CARD_BINS_REAL),
            "card_last4": f"{random.randint(1000, 9999)}",
            "cvv_provided": 1,
            "avs_result": "Y",
            "billing_address": "789 Home Ln, Springfield, IL 62701",
            "billing_country": "US",
            "billing_zip": "62701",
            "shipping_country": "US",
            "shipping_zip": "62701",
            "merchant_id": "M001",
            "merchant_category": _weighted_choice(["clothing", "electronics"], [3, 1]),
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
