import pytest
pytestmark = pytest.mark.asyncio

from app.api.schemas import TransactionDecision
from app.agents.compliance_guardrail import validate_transaction_output


@pytest.fixture
def clean_decision():
    return TransactionDecision(
        order_id="ord_001",
        decision="approve",
        risk_score=15.0,
        confidence=0.85,
        agent_scores={"device": 10.0, "behavior": 20.0, "network": 15.0, "transaction": 12.0, "behavioral": 8.0},
        reason_codes=["device matches history", "normal shipping pattern"],
        latency_ms=45.0,
    )


@pytest.fixture
def low_confidence_decision():
    return TransactionDecision(
        order_id="ord_002",
        decision="approve",
        risk_score=10.0,
        confidence=0.45,
        agent_scores={"device": 10.0, "behavior": 10.0, "network": 10.0, "transaction": 10.0, "behavioral": 10.0},
        reason_codes=["clean signals"],
        latency_ms=30.0,
    )


@pytest.fixture
def borderline_decision():
    return TransactionDecision(
        order_id="ord_003",
        decision="approve",
        risk_score=28.0,
        confidence=0.80,
        agent_scores={"device": 30.0, "behavior": 25.0, "network": 35.0, "transaction": 20.0, "behavioral": 30.0},
        reason_codes=["velocity anomaly"],
        latency_ms=52.0,
    )


class TestComplianceGuardrail:
    async def test_clean_decision_passes(self, clean_decision):
        result = await validate_transaction_output(clean_decision)
        assert result.passed
        assert result.decision == clean_decision.decision
        assert not result.needs_human_review

    async def test_low_confidence_escalates(self, low_confidence_decision):
        result = await validate_transaction_output(low_confidence_decision)
        assert not result.passed
        assert result.decision == "escalate"
        assert not result.confidence_valid

    async def test_borderline_triggers_escalation(self, borderline_decision):
        result = await validate_transaction_output(borderline_decision)
        assert result.needs_human_review
        assert result.decision == "escalate"

    async def test_negative_agent_score_fails(self, clean_decision):
        bad = clean_decision.model_copy(update={"agent_scores": {"device": -5.0, "behavior": 20.0, "network": 15.0, "transaction": 12.0, "behavioral": 8.0}})
        result = await validate_transaction_output(bad)
        assert not result.passed
        assert any("negative" in i.lower() for i in result.issues)

    async def test_missing_field_fails(self, clean_decision):
        bad = clean_decision.model_copy(update={"order_id": None})
        result = await validate_transaction_output(bad)
        assert not result.passed
        assert any("missing" in i.lower() for i in result.issues)
