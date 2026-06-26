from typing import Literal
from dataclasses import dataclass, field

from agents import Agent, Runner, GuardrailFunctionOutput, output_guardrail

from app.api.schemas import TransactionDecision
from app.configs.policies import HumanReviewPolicy, CompliancePolicy, ComplianceRegulation
from app.services.validation_service import ValidationService


@dataclass
class ComplianceCheckResult:
    passed: bool
    decision: Literal["approve", "review", "decline", "escalate"]
    issues: list[str] = field(default_factory=list)
    confidence_valid: bool = True
    needs_human_review: bool = False
    review_reason: str | None = None
    compliance_flags: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "decision": self.decision,
            "issues": self.issues,
            "confidence_valid": self.confidence_valid,
            "needs_human_review": self.needs_human_review,
            "review_reason": self.review_reason,
            "compliance_flags": self.compliance_flags,
        }


compliance_guardrail_instructions = (
    "You are the Compliance Guardrail — the final validation layer for a fraud detection platform. "
    "Your role is to:\n"
    "1. Validate that the output decision is safe, fair, and compliant\n"
    "2. Check for bias in the decision — no region, payment method, or device should be unfairly targeted\n"
    "3. Ensure confidence scores meet minimum thresholds for the given decision type\n"
    "4. Flag any decisions that need human review (borderline scores, low confidence, bias detected)\n"
    "5. Override the decision to 'escalate' if safety guardrails are breached\n\n"
    "Rules:\n"
    "- Never approve a transaction with risk score >= 30\n"
    "- Never decline a transaction with risk score <= 70\n"
    "- Escalate if confidence < 0.60 or if risk score is in [25, 35] range\n"
    "- Escalate if any bias check fails\n"
    "- Escalate if compliance checks require it\n"
    "- All issues must be reported in 'issues' field\n"
    "- Never use raw location as a decline signal"
)

compliance_guardrail_agent = Agent(
    name="ComplianceGuardrail",
    instructions=compliance_guardrail_instructions,
    model="gpt-4o-mini",
    output_type=ComplianceCheckResult,
)


async def validate_transaction_output(decision: TransactionDecision) -> ComplianceCheckResult:
    """
    Validate a transaction decision through the compliance guardrail.
    Combines deterministic validation (validation_service) with
    LLM-based guardrail assessment.
    """
    service = ValidationService()
    deterministic = await service.validate_transaction(decision)

    issues = [f"{i.code}: {i.message}" for i in deterministic.issues]

    if deterministic.needs_human_review:
        override_decision: Literal["approve", "review", "decline", "escalate"] = "escalate"
    elif not deterministic.passed:
        override_decision = "review"
    else:
        override_decision = decision.decision

    if not deterministic.confidence_valid and override_decision == "approve":
        override_decision = "review"

    return ComplianceCheckResult(
        passed=deterministic.passed and deterministic.confidence_valid,
        decision=override_decision,
        issues=issues,
        confidence_valid=deterministic.confidence_valid,
        needs_human_review=deterministic.needs_human_review,
        review_reason=deterministic.review_reason,
        compliance_flags=deterministic.compliance_checks,
    )


async def validate_with_llm(decision: TransactionDecision) -> ComplianceCheckResult:
    """
    Run the LLM-based compliance guardrail agent for complex validation.
    Use this when deterministic checks pass but the decision is borderline.
    """
    result = await Runner.run(compliance_guardrail_agent, input={
        "decision": decision.decision,
        "risk_score": decision.risk_score,
        "confidence": decision.confidence,
        "agent_scores": decision.agent_scores,
        "reason_codes": decision.reason_codes,
    })
    return result.final_output
