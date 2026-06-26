import pytest
from app.api.schemas import TransactionDecision
from app.services.validation_service import ValidationService, ValidationResult
from app.configs.policies import BiasDimension


@pytest.fixture
def service():
    return ValidationService()


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
def borderline_decision():
    return TransactionDecision(
        order_id="ord_002",
        decision="review",
        risk_score=28.0,
        confidence=0.55,
        agent_scores={"device": 30.0, "behavior": 25.0, "network": 35.0, "transaction": 20.0, "behavioral": 30.0},
        reason_codes=["velocity anomaly", "new device"],
        latency_ms=52.0,
    )


@pytest.fixture
def high_risk_decision():
    return TransactionDecision(
        order_id="ord_003",
        decision="decline",
        risk_score=85.0,
        confidence=0.90,
        agent_scores={"device": 80.0, "behavior": 90.0, "network": 85.0, "transaction": 75.0, "behavioral": 95.0},
        reason_codes=["fraud ring detected", "card testing pattern", "velocity burst", "COD abuse"],
        latency_ms=38.0,
    )


class TestOutputValidation:
    def test_clean_decision_passes(self, service, clean_decision):
        result = service.validate_output(clean_decision)
        assert result.passed

    def test_missing_field_fails(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"order_id": None})
        result = service.validate_output(bad)
        assert not result.passed
        assert any("missing_field" == i.code for i in result.issues)

    def test_risk_out_of_range_fails(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"risk_score": -5.0})
        result = service.validate_output(bad)
        assert not result.passed
        assert any("risk_out_of_range" == i.code for i in result.issues)

    def test_risk_above_max_fails(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"risk_score": 150.0})
        result = service.validate_output(bad)
        assert not result.passed
        assert any("risk_out_of_range" == i.code for i in result.issues)

    def test_confidence_out_of_range_fails(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"confidence": 1.5})
        result = service.validate_output(bad)
        assert not result.passed
        assert any("confidence_out_of_range" == i.code for i in result.issues)

    def test_negative_agent_score_fails(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"agent_scores": {"device": -10.0, "behavior": 20.0, "network": 15.0, "transaction": 12.0, "behavioral": 8.0}})
        result = service.validate_output(bad)
        assert not result.passed
        assert any("negative_agent_score" == i.code for i in result.issues)

    def test_too_many_reason_codes_warns(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"reason_codes": [f"code_{i}" for i in range(20)]})
        result = service.validate_output(bad)
        assert result.passed
        assert any("too_many_reason_codes" == i.code for i in result.issues)

    def test_inconsistent_decision_warns(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"decision": "approve", "risk_score": 50.0})
        result = service.validate_output(bad)
        assert result.passed
        assert any("inconsistent_approve" == i.code for i in result.issues)


class TestConfidenceValidation:
    def test_approve_with_good_confidence_passes(self, service, clean_decision):
        assert service.validate_confidence(clean_decision)

    def test_approve_with_low_confidence_fails(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"confidence": 0.50})
        assert not service.validate_confidence(bad)

    def test_decline_with_good_confidence_passes(self, service, high_risk_decision):
        assert service.validate_confidence(high_risk_decision)

    def test_review_with_low_confidence_fails(self, service, borderline_decision):
        bad = borderline_decision.model_copy(update={"confidence": 0.40})
        assert not service.validate_confidence(bad)


class TestBiasDetection:
    def test_no_bias_when_groups_balanced(self, service):
        decisions = [
            TransactionDecision(order_id=f"ord_{i}", decision="approve", risk_score=20.0, confidence=0.85, agent_scores={"device": 10.0, "behavior": 20.0, "network": 15.0, "transaction": 12.0, "behavioral": 8.0}, reason_codes=[], latency_ms=10.0)
            for i in range(10)
        ]
        labels = ["us"] * 5 + ["eu"] * 5
        result = service.detect_bias(decisions, labels, BiasDimension.REGION)
        assert result.passed

    def test_bias_detected_when_groups_unbalanced(self, service):
        decisions = [
            TransactionDecision(order_id=f"ord_{i}", decision="decline", risk_score=90.0, confidence=0.90, agent_scores={"device": 80.0, "behavior": 90.0, "network": 85.0, "transaction": 75.0, "behavioral": 95.0}, reason_codes=[], latency_ms=10.0)
            for i in range(10)
        ] + [
            TransactionDecision(order_id=f"ord_{i}", decision="approve", risk_score=10.0, confidence=0.90, agent_scores={"device": 5.0, "behavior": 10.0, "network": 8.0, "transaction": 12.0, "behavioral": 8.0}, reason_codes=[], latency_ms=10.0)
            for i in range(10)
        ]
        labels = ["region_a"] * 10 + ["region_b"] * 10
        result = service.detect_bias(decisions, labels, BiasDimension.REGION)
        assert not result.passed


class TestHumanReviewEscalation:
    def test_low_confidence_escalates(self, service, borderline_decision):
        result = service.validate_output(borderline_decision)
        result.confidence_valid = False
        needs, reason = service.should_escalate_to_human(borderline_decision, result)
        assert needs
        assert "confidence" in reason.lower()

    def test_borderline_score_escalates(self, service):
        dec = TransactionDecision(
            order_id="ord_brd", decision="review", risk_score=30.0, confidence=0.80,
            agent_scores={"device": 30.0, "behavior": 30.0, "network": 30.0, "transaction": 30.0, "behavioral": 30.0},
            reason_codes=["borderline"], latency_ms=10.0,
        )
        result = service.validate_output(dec)
        needs, reason = service.should_escalate_to_human(dec, result)
        assert needs
        assert "borderline" in reason.lower()

    def test_clean_decision_no_escalation(self, service, clean_decision):
        result = service.validate_output(clean_decision)
        needs, reason = service.should_escalate_to_human(clean_decision, result)
        assert not needs


class TestComplianceChecks:
    def test_gdpr_requires_explanations(self, service, clean_decision):
        bad = clean_decision.model_copy(update={"reason_codes": []})
        checks = service.run_compliance_checks(bad)
        assert not checks.get("gdpr", True)

    def test_aml_flags_high_value(self, service, high_risk_decision):
        checks = service.run_compliance_checks(high_risk_decision, txn_amount=50000)
        assert checks.get("aml", True)

    def test_kyc_requires_verification_for_review(self, service):
        dec = TransactionDecision(
            order_id="ord_kyc", decision="review", risk_score=50.0, confidence=0.75,
            agent_scores={"device": 50.0, "behavior": 50.0, "network": 50.0, "transaction": 50.0, "behavioral": 50.0},
            reason_codes=["kyc required"], latency_ms=10.0,
        )
        checks = service.run_compliance_checks(dec)
        assert not checks.get("kyc", True)


class TestEndToEndValidation:
    def test_clean_transaction_passes_all(self, service, clean_decision):
        result = service.validate_output(clean_decision)
        assert result.passed
        assert result.confidence_valid

    def test_borderline_flagged_for_review(self, service, borderline_decision):
        result = service.validate_output(borderline_decision)
        compliance = service.run_compliance_checks(borderline_decision)
        needs, reason = service.should_escalate_to_human(borderline_decision, result)
        assert needs or not all(compliance.values())

    def test_high_value_transaction_escalates(self, service):
        dec = TransactionDecision(
            order_id="ord_hv", decision="approve", risk_score=20.0, confidence=0.85,
            agent_scores={"device": 20.0, "behavior": 20.0, "network": 20.0, "transaction": 20.0, "behavioral": 20.0},
            reason_codes=["high value"], latency_ms=10.0,
        )
        checks = service.run_compliance_checks(dec, txn_amount=60000)
        assert not checks.get("aml", True)
