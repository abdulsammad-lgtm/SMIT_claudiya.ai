"""
Demo test scenarios — run against the live API with synthetic data.
These validate the platform end-to-end and serve as a demo script.

Usage:
    pytest app/tests/test_scenarios.py -v
    # Or run individually:
    python -m pytest app/tests/test_scenarios.py::test_clean_order -v
"""

import pytest
import httpx
from app.api.main import app
from app.db.models import async_session, Transaction, init_db
from app.db.seed import (
    generate_clean_orders,
    generate_cod_fraud_ring,
    generate_card_testing_burst,
    generate_friendly_fraud_pattern,
)
from app.orchestrator.orchestrator import score_transaction
from app.api.schemas import TransactionIn


BASE_URL = "http://test"
transport = httpx.ASGITransport(app=app)  # noqa


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


async def _seed_clean():
    async with async_session() as session:
        for o in generate_clean_orders(5):
            t = Transaction(**o)
            session.add(t)
        await session.commit()


async def _seed_all():
    async with async_session() as session:
        for o in generate_clean_orders(20):
            session.add(Transaction(**o))
        for o in generate_cod_fraud_ring():
            session.add(Transaction(**o))
        for o in generate_card_testing_burst():
            session.add(Transaction(**o))
        for o in generate_friendly_fraud_pattern():
            session.add(Transaction(**o))
        await session.commit()


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    async with async_session() as session:
        for txn in (await session.execute(__import__("sqlalchemy").select(Transaction))).scalars().all():
            await session.delete(txn)
        await session.commit()
    yield


@pytest.mark.anyio
async def test_clean_order_fast_path():
    await _seed_clean()
    txn_in = TransactionIn(
        order_id="TEST-CLEAN-001",
        customer_id="CUST_1",
        amount=45.00,
        currency="USD",
        payment_method="card",
        device_fingerprint="FP_CLEAN_1",
        ip_address="192.168.1.1",
        phone_number="+15551111111",
        shipping_address="123 Oak St, Portland, OR 97201",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        session_duration_seconds=350.0,
    )
    decision = await score_transaction(txn_in, use_reasoning=False)
    assert decision.decision in ("approve", "review"), f"Expected approve or review, got {decision.decision} (score={decision.risk_score})"
    assert decision.risk_score < 50, f"Risk score too high for clean order: {decision.risk_score}"
    assert decision.latency_ms < 500, f"Latency too high: {decision.latency_ms}ms"


@pytest.mark.anyio
async def test_cod_fraud_ring():
    await _seed_all()
    txn_in = TransactionIn(
        order_id="TEST-COD-RING-001",
        customer_id="FRAUD_COD_9",
        amount=899.00,
        currency="USD",
        payment_method="cod",
        device_fingerprint="FP_FRAUD_DEVICE_001",
        ip_address="10.0.1.99",
        phone_number="+15559999999",
        shipping_address="4567 Industrial Blvd, Warehouse 12, Chicago, IL 60601",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        session_duration_seconds=12.0,
    )
    decision = await score_transaction(txn_in, use_reasoning=False)
    assert decision.decision in ("review", "decline")
    assert decision.risk_score > 30
    assert decision.agent_scores.get("network", 0) > 20
    has_ring_reason = any("linked" in r.lower() or "connected" in r.lower() or "fraud" in r.lower() for r in decision.reason_codes)
    assert has_ring_reason


@pytest.mark.anyio
async def test_card_testing_burst():
    await _seed_all()
    txn_in = TransactionIn(
        order_id="TEST-CARD-BURST-001",
        customer_id="CARDTEST_A",
        amount=3.50,
        currency="USD",
        payment_method="card",
        device_fingerprint="FP_CARD_TEST_001",
        ip_address="203.0.113.99",
        phone_number="+15551234567",
        shipping_address="100 Test Ave, Unit 5, New York, NY 10001",
        user_agent="Mozilla/5.0 (Linux; Android 14) Chrome/120.0.0.0",
        session_duration_seconds=5.0,
    )
    decision = await score_transaction(txn_in, use_reasoning=False)
    assert decision.risk_score > 20
    assert decision.agent_scores.get("behavior", 0) > 20


@pytest.mark.anyio
async def test_friendly_fraud_pattern():
    await _seed_all()
    txn_in = TransactionIn(
        order_id="TEST-FRIENDLY-001",
        customer_id="FRIENDLY_REPEAT_001",
        amount=175.00,
        currency="USD",
        payment_method="cod",
        device_fingerprint="FP_FRIENDLY_99",
        ip_address="192.168.1.100",
        phone_number="+15557777777",
        shipping_address="789 Home Ln, Springfield, IL 62701",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.2",
        session_duration_seconds=300.0,
    )
    decision = await score_transaction(txn_in, use_reasoning=False)
    assert decision.risk_score > 10
    has_cod_reason = any("cod" in r.lower() or "refusal" in r.lower() for r in decision.reason_codes)
    assert has_cod_reason


@pytest.mark.anyio
async def test_api_score_endpoint():
    await _seed_clean()
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.post("/api/score", json={
            "order_id": "API-TEST-001",
            "customer_id": "CUST_1",
            "amount": 50.0,
            "currency": "USD",
            "payment_method": "card",
            "device_fingerprint": "FP_CLEAN_1",
            "ip_address": "192.168.1.1",
            "phone_number": "+15551111111",
            "shipping_address": "123 Oak St, Portland, OR 97201",
            "user_agent": "Mozilla/5.0 Chrome/120.0.0.0",
            "session_duration_seconds": 400.0,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] in ("approve", "review", "decline")
    assert 0 <= data["risk_score"] <= 100
    assert "agent_scores" in data


@pytest.mark.anyio
async def test_list_transactions():
    await _seed_all()
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
        resp = await client.get("/api/transactions?per_page=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert len(data["transactions"]) > 0


@pytest.mark.anyio
async def test_override_endpoint():
    await _seed_all()
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
        list_resp = await client.get("/api/transactions?status=review&per_page=1")
        txns = list_resp.json().get("transactions", [])
        if not txns:
            return
        oid = txns[0]["order_id"]
        resp = await client.post(f"/api/transactions/{oid}/override", json={
            "decision": "approve",
            "reason": "Manual override test",
            "analyst": "pytest",
        })
    assert resp.status_code == 200
    assert resp.json()["decision"] == "approve"
