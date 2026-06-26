import re
import datetime
from typing import Any

from app.configs.policies import (
    BiasPolicy,
    ConfidencePolicy,
    SafetyPolicy,
    PiiRules,
    CompliancePolicy,
    HumanReviewPolicy,
    BiasDimension,
    ComplianceRegulation,
)
from app.api.schemas import TransactionDecision


class BiasCheckResult:
    def __init__(self, dimension: BiasDimension, passed: bool, disparity: float, details: str):
        self.dimension = dimension
        self.passed = passed
        self.disparity = disparity
        self.details = details
        self.timestamp = datetime.datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension.value,
            "passed": self.passed,
            "disparity": self.disparity,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class ValidationIssue:
    def __init__(self, code: str, severity: str, message: str, field: str | None = None):
        self.code = code
        self.severity = severity
        self.message = message
        self.field = field

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "field": self.field,
        }


class ValidationResult:
    def __init__(self, passed: bool):
        self.passed = passed
        self.issues: list[ValidationIssue] = []
        self.bias_checks: list[BiasCheckResult] = []
        self.confidence_valid = True
        self.compliance_checks: dict[str, bool] = {}
        self.needs_human_review = False
        self.review_reason: str | None = None

    def add_issue(self, code: str, severity: str, message: str, field: str | None = None):
        self.issues.append(ValidationIssue(code, severity, message, field))
        if severity == "error":
            self.passed = False

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "bias_checks": [b.to_dict() for b in self.bias_checks],
            "confidence_valid": self.confidence_valid,
            "compliance_checks": self.compliance_checks,
            "needs_human_review": self.needs_human_review,
            "review_reason": self.review_reason,
        }


class ValidationService:
    def validate_output(self, decision: TransactionDecision) -> ValidationResult:
        result = ValidationResult(passed=True)
        rules = SafetyPolicy["output_validation"]

        for field in rules["required_fields"]:
            if not hasattr(decision, field) or getattr(decision, field) is None:
                result.add_issue("missing_field", "error", f"Required field '{field}' is missing", field=field)

        score = decision.risk_score
        lo, hi = rules["risk_score_range"]
        if score < lo or score > hi:
            result.add_issue("risk_out_of_range", "error", f"Risk score {score} outside [{lo}, {hi}]", field="risk_score")

        confidence = decision.confidence
        clo, chi = rules["confidence_range"]
        if confidence < clo or confidence > chi:
            result.add_issue("confidence_out_of_range", "error", f"Confidence {confidence} outside [{clo}, {chi}]", field="confidence")

        if rules["disallow_negative_values"]:
            for score_val in decision.agent_scores.values():
                if score_val < 0:
                    result.add_issue("negative_agent_score", "error", f"Negative agent score: {score_val}", field="agent_scores")

        if len(decision.reason_codes) > rules["max_reason_codes"]:
            result.add_issue("too_many_reason_codes", "warning", f"More than {rules['max_reason_codes']} reason codes")

        self._check_decision_consistency(decision, result)
        self._check_pii_in_output(decision, result)

        return result

    def _check_decision_consistency(self, decision: TransactionDecision, result: ValidationResult):
        guardrails = SafetyPolicy["output_guardrails"]
        if decision.decision == "approve" and decision.risk_score >= guardrails["approve_must_have_risk_under"]:
            result.add_issue("inconsistent_approve", "warning", f"Approved but risk score {decision.risk_score} >= {guardrails['approve_must_have_risk_under']}")
        if decision.decision == "decline" and decision.risk_score <= guardrails["decline_must_have_risk_above"]:
            result.add_issue("inconsistent_decline", "warning", f"Declined but risk score {decision.risk_score} <= {guardrails['decline_must_have_risk_above']}")

    def _check_pii_in_output(self, decision: TransactionDecision, result: ValidationResult):
        patterns = PiiRules["patterns"]
        texts_to_check = decision.reason_codes[:]
        for pattern in patterns:
            compiled = re.compile(pattern)
            for text in texts_to_check:
                if compiled.search(text):
                    result.add_issue("pii_exposed", "error", f"PII detected in reason code: '{PiiRules['redaction_placeholder']}'", field="reason_codes")
                    return

    def validate_confidence(self, decision: TransactionDecision) -> bool:
        thresholds = ConfidencePolicy["thresholds"].get(decision.decision)
        if not thresholds:
            return False
        if decision.confidence < thresholds["min_confidence"]:
            return False
        if decision.decision == "approve" and decision.risk_score > thresholds["max_risk"]:
            return False
        if decision.decision == "decline" and decision.risk_score < thresholds["min_risk"]:
            return False
        return True

    def detect_bias(
        self,
        decisions: list[TransactionDecision],
        group_labels: list[str],
        dimension: BiasDimension,
    ) -> BiasCheckResult:
        metrics = BiasPolicy["fairness_metrics"].get(dimension)
        if not metrics or not metrics["enabled"]:
            return BiasCheckResult(dimension, True, 0.0, f"{dimension.value} bias monitoring disabled")

        groups: dict[str, list[float]] = {}
        for dec, label in zip(decisions, group_labels):
            if label not in groups:
                groups[label] = []
            groups[label].append(dec.risk_score)

        if len(groups) < 2:
            return BiasCheckResult(dimension, True, 0.0, "Only one group present — cannot compute disparity")

        max_disparity = metrics["max_disparity"]
        group_means = {g: sum(scores) / len(scores) for g, scores in groups.items()}
        overall_mean = sum(group_means.values()) / len(group_means)
        max_deviation = max(abs(m - overall_mean) for m in group_means.values())

        passed = max_deviation <= max_disparity
        details = (
            f"Groups: { {g: round(m, 2) for g, m in group_means.items()} }, "
            f"max_deviation={round(max_deviation, 3)}, threshold={max_disparity}"
        )

        return BiasCheckResult(dimension, passed, max_deviation, details)

    def run_compliance_checks(self, decision: TransactionDecision, txn_amount: float | None = None) -> dict[str, bool]:
        results = {}
        for reg in CompliancePolicy["enabled_regulations"]:
            rules = CompliancePolicy["regulations"].get(reg, {})
            reg_name = reg.value
            if reg == ComplianceRegulation.GDPR:
                passed = rules.get("require_explanation", False) and len(decision.reason_codes) > 0
            elif reg == ComplianceRegulation.AML:
                passed = True
                if txn_amount and txn_amount >= rules.get("require_identity_verification_on_threshold", 10000):
                    passed = decision.decision == "review" or decision.decision == "decline"
            elif reg == ComplianceRegulation.KYC:
                if decision.decision == "review":
                    passed = False
            else:
                passed = True
            results[reg_name] = passed
        return results

    def should_escalate_to_human(self, decision: TransactionDecision, validation_result: ValidationResult) -> tuple[bool, str | None]:
        triggers = HumanReviewPolicy["escalation_triggers"]

        if triggers["max_confidence"]["enabled"]:
            if decision.confidence < triggers["max_confidence"]["threshold_below"]:
                validation_result.review_reason = f"Low confidence: {decision.confidence} < {triggers['max_confidence']['threshold_below']}"
                return True, validation_result.review_reason

        if triggers["low_confidence_high_risk"]["enabled"]:
            if decision.confidence < triggers["low_confidence_high_risk"]["confidence_below"] and decision.risk_score > triggers["low_confidence_high_risk"]["risk_above"]:
                validation_result.review_reason = f"Low confidence ({decision.confidence}) with high risk ({decision.risk_score})"
                return True, validation_result.review_reason

        if triggers["borderline_score"]["enabled"]:
            lo, hi = triggers["borderline_score"]["range"]
            if lo <= decision.risk_score <= hi:
                validation_result.review_reason = f"Borderline risk score {decision.risk_score} in [{lo}, {hi}]"
                return True, validation_result.review_reason

        if not validation_result.confidence_valid:
            validation_result.review_reason = "Confidence validation failed"
            return True, validation_result.review_reason

        for bias_check in validation_result.bias_checks:
            if not bias_check.passed:
                validation_result.review_reason = f"Bias check failed: {bias_check.dimension.value}"
                return True, validation_result.review_reason

        return False, None

    async def validate_transaction(
        self,
        decision: TransactionDecision,
        txn_amount: float | None = None,
        group_label: str | None = None,
        previous_decisions: list[TransactionDecision] | None = None,
        previous_labels: list[str] | None = None,
    ) -> ValidationResult:
        result = self.validate_output(decision)

        result.confidence_valid = self.validate_confidence(decision)
        if not result.confidence_valid:
            result.add_issue("low_confidence", "warning", f"Confidence {decision.confidence} below threshold for '{decision.decision}' decision")

        if previous_decisions and previous_labels:
            bias_result = self.detect_bias(previous_decisions, previous_labels, BiasDimension.REGION)
            result.bias_checks.append(bias_result)

        result.compliance_checks = self.run_compliance_checks(decision, txn_amount)

        needs_review, reason = self.should_escalate_to_human(decision, result)
        result.needs_human_review = needs_review
        if reason:
            result.review_reason = reason

        return result
