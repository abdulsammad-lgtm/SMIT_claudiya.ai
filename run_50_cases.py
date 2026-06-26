"""Score 50 test transactions via API to populate the dashboard."""
import httpx
import asyncio
import random
import json

API = "http://127.0.0.1:8080"

CUSTOMERS = {
    "clean": [
        ("CUST_CLEAN_1", "192.168.1.1", "+15551111111", "123 Oak St, Portland, OR 97201", "FP_CLEAN_1"),
        ("CUST_CLEAN_2", "192.168.1.2", "+15552222222", "456 Pine St, Portland, OR 97202", "FP_CLEAN_2"),
        ("CUST_CLEAN_3", "10.0.0.3", "+15553333333", "789 Maple Ave, Seattle, WA 98101", "FP_CLEAN_3"),
        ("CUST_CLEAN_4", "172.16.0.4", "+15554444444", "321 Elm St, San Francisco, CA 94102", "FP_CLEAN_4"),
        ("CUST_CLEAN_5", "192.168.5.5", "+15555555555", "654 Birch Rd, Denver, CO 80201", "FP_CLEAN_5"),
        ("CUST_CLEAN_6", "10.0.0.6", "+15556666666", "987 Cedar Ln, Austin, TX 73301", "FP_CLEAN_6"),
        ("CUST_CLEAN_7", "172.16.0.7", "+15557777777", "111 Walnut Dr, Chicago, IL 60601", "FP_CLEAN_7"),
        ("CUST_CLEAN_8", "192.168.8.8", "+15558888888", "222 Spruce Ct, Boston, MA 02101", "FP_CLEAN_8"),
        ("CUST_CLEAN_9", "10.0.0.9", "+15559999999", "333 Ash Way, Miami, FL 33101", "FP_CLEAN_9"),
        ("CUST_CLEAN_10", "172.16.0.10", "+15550000001", "444 Poplar St, NYC, NY 10001", "FP_CLEAN_10"),
    ],
    "cod_fraud": [
        ("FRAUD_COD_1", "10.0.1.10", "+15551234001", "4567 Industrial Blvd, Warehouse 12, Chicago, IL 60601", "FP_FRAUD_001"),
        ("FRAUD_COD_2", "10.0.1.11", "+15551234002", "4567 Industrial Blvd, Warehouse 12, Chicago, IL 60601", "FP_FRAUD_001"),
        ("FRAUD_COD_3", "10.0.1.12", "+15551234003", "4567 Industrial Blvd, Warehouse 12, Chicago, IL 60601", "FP_FRAUD_001"),
        ("FRAUD_COD_4", "10.0.1.13", "+15551234004", "8900 Logistics Dr, Unit 5, Chicago, IL 60616", "FP_FRAUD_002"),
        ("FRAUD_COD_5", "10.0.1.14", "+15551234005", "8900 Logistics Dr, Unit 5, Chicago, IL 60616", "FP_FRAUD_002"),
        ("FRAUD_COD_6", "10.0.1.15", "+15551234006", "8900 Logistics Dr, Unit 5, Chicago, IL 60616", "FP_FRAUD_002"),
        ("FRAUD_COD_7", "10.0.1.16", "+15551234007", "234 Commerce Pkwy, Detroit, MI 48201", "FP_FRAUD_003"),
        ("FRAUD_COD_8", "10.0.1.17", "+15551234008", "234 Commerce Pkwy, Detroit, MI 48201", "FP_FRAUD_003"),
    ],
    "card_test": [
        ("CARDTEST_A", "203.0.113.10", "+15550100001", "100 Test Ave, Unit 1, NYC, NY 10001", "FP_CARD_TEST_001"),
        ("CARDTEST_A", "203.0.113.11", "+15550100002", "100 Test Ave, Unit 2, NYC, NY 10001", "FP_CARD_TEST_001"),
        ("CARDTEST_A", "203.0.113.12", "+15550100003", "100 Test Ave, Unit 3, NYC, NY 10001", "FP_CARD_TEST_001"),
        ("CARDTEST_B", "203.0.113.20", "+15550200001", "200 Fraud Ln, Newark, NJ 07101", "FP_CARD_TEST_002"),
        ("CARDTEST_B", "203.0.113.21", "+15550200002", "200 Fraud Ln, Newark, NJ 07101", "FP_CARD_TEST_002"),
        ("CARDTEST_B", "203.0.113.22", "+15550200003", "200 Fraud Ln, Newark, NJ 07101", "FP_CARD_TEST_002"),
        ("CARDTEST_B", "203.0.113.23", "+15550200004", "200 Fraud Ln, Newark, NJ 07101", "FP_CARD_TEST_002"),
    ],
    "friendly_fraud": [
        ("FRIENDLY_1", "192.168.100.1", "+15557770001", "789 Home Ln, Springfield, IL 62701", "FP_FRIENDLY_1"),
        ("FRIENDLY_1", "192.168.100.1", "+15557770001", "789 Home Ln, Springfield, IL 62701", "FP_FRIENDLY_1"),
        ("FRIENDLY_2", "192.168.100.2", "+15557770002", "456 Family Dr, Columbus, OH 43201", "FP_FRIENDLY_2"),
        ("FRIENDLY_2", "192.168.100.2", "+15557770002", "456 Family Dr, Columbus, OH 43201", "FP_FRIENDLY_2"),
        ("FRIENDLY_2", "192.168.100.2", "+15557770002", "456 Family Dr, Columbus, OH 43201", "FP_FRIENDLY_2"),
    ],
}

ITEMS = {
    "clean": [25.00, 45.00, 67.50, 89.99, 120.00, 34.99, 55.00, 78.50],
    "cod_fraud": [499.99, 899.00, 750.00, 1200.00, 450.00, 999.99, 600.00, 850.00],
    "card_test": [1.50, 2.99, 3.50, 5.00, 0.99, 4.50, 2.00, 3.00],
    "friendly_fraud": [150.00, 175.00, 200.00, 90.00, 130.00],
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
UA_MOBILE = "Mozilla/5.0 (Linux; Android 14) Chrome/120.0.0.0"
UA_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.2"


async def score_one(client, order_id, customer_id, amount, currency, payment_method,
                    device_fp, ip, phone, address, ua, session_sec, use_reasoning=False):
    params = "?reasoning=true" if use_reasoning else ""
    try:
        resp = await client.post(
            f"/api/score{params}",
            json={
                "order_id": order_id,
                "customer_id": customer_id,
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
                "device_fingerprint": device_fp,
                "ip_address": ip,
                "phone_number": phone,
                "shipping_address": address,
                "user_agent": ua,
                "session_duration_seconds": session_sec,
            },
            timeout=60,
        )
        return resp.status_code, resp.json() if resp.status_code == 200 else resp.text[:200]
    except Exception as e:
        return 0, str(e)[:200]


async def main():
    async with httpx.AsyncClient(base_url=API) as client:
        tasks = []
        order_idx = 1

        # 20 clean orders
        for i in range(20):
            cust, ip, phone, addr, fp = random.choice(CUSTOMERS["clean"])
            amt = random.choice(ITEMS["clean"])
            session = random.randint(120, 600)
            ua_choice = random.choice([UA, UA_MAC])
            oid = f"50T-CLEAN-{order_idx:03d}"
            tasks.append(score_one(client, oid, cust, amt, "USD", "card", fp, ip, phone, addr, ua_choice, session))
            order_idx += 1

        # 12 COD fraud
        for i in range(12):
            cust, ip, phone, addr, fp = random.choice(CUSTOMERS["cod_fraud"])
            amt = random.choice(ITEMS["cod_fraud"])
            session = random.randint(5, 25)
            oid = f"50T-COD-{order_idx:03d}"
            tasks.append(score_one(client, oid, cust, amt, "USD", "cod", fp, ip, phone, addr, UA, session))
            order_idx += 1

        # 10 card testing
        for i in range(10):
            cust, ip, phone, addr, fp = random.choice(CUSTOMERS["card_test"])
            amt = random.choice(ITEMS["card_test"])
            session = random.randint(2, 10)
            ua_choice = random.choice([UA_MOBILE, UA])
            oid = f"50T-CARD-{order_idx:03d}"
            tasks.append(score_one(client, oid, cust, amt, "USD", "card", fp, ip, phone, addr, ua_choice, session))
            order_idx += 1

        # 8 friendly fraud
        for i in range(8):
            cust, ip, phone, addr, fp = random.choice(CUSTOMERS["friendly_fraud"])
            amt = random.choice(ITEMS["friendly_fraud"])
            session = random.randint(60, 300)
            oid = f"50T-FRIEND-{order_idx:03d}"
            tasks.append(score_one(client, oid, cust, amt, "USD", "cod", fp, ip, phone, addr, UA_MAC, session))
            order_idx += 1

        results = await asyncio.gather(*tasks)

    ok = sum(1 for s, _ in results if s == 200)
    fail = sum(1 for s, _ in results if s != 200)
    print(f"Scored {ok} transactions ({fail} failed)")
    for s, data in results[:5]:
        if s == 200:
            d = data.get("decision", "?")
            r = data.get("risk_score", "?")
            print(f"  {data.get('order_id','?')}: {d} (risk={r})")
    if fail:
        print(f"\nFailures:")
        for s, data in results:
            if s != 200:
                print(f"  status={s}: {str(data)[:100]}")

if __name__ == "__main__":
    asyncio.run(main())
