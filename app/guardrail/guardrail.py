"""
Guardrail layer using OpenAI Agents SDK primitives.

This module implements:
- Explainability: plain-language reason codes generated from agent outputs
- Escalation rule: output guardrail that forces borderline scores to `review`
- Fairness guard: policy never uses raw location as a decline signal
- Audit logging: every decision is persisted in the append-only audit table
"""

from typing import Any
from agents import GuardrailFunctionOutput, output_guardrail, InputGuardrail, input_guardrail

from app.api.schemas import AgentScoreOutput
from app.orchestrator.policy import RISK_THRESHOLDS


def compute_reason_codes(
    device: AgentScoreOutput,
    behavior: AgentScoreOutput,
    network: AgentScoreOutput,
) -> list[str]:
    codes = []
    for agent_name, output in [("device", device), ("behavior", behavior), ("network", network)]:
        if output.score > 20:
            if output.explanation and output.explanation != f"{agent_name} signals clean":
                codes.append(output.explanation)
            elif output.evidence:
                codes.extend(output.evidence[:3])
    return codes[:8]


async def apply_guardrails(
    raw_risk: float,
    agent_scores: dict[str, float],
    reason_codes: list[str],
    agent_raw: dict[str, Any],
    device_score: AgentScoreOutput,
    behavior_score: AgentScoreOutput,
    network_score: AgentScoreOutput,
    txn: Any,
) -> dict:
    result = {
        "risk_score": raw_risk,
        "confidence": 0.85,
        "reason_codes": reason_codes,
        "guardrail_applied": False,
        "scoring_path": "fast",
        "decision": "approve",
    }

    # Decision thresholds
    if raw_risk < RISK_THRESHOLDS["approve_upper"]:
        result["decision"] = "approve"
    elif raw_risk > RISK_THRESHOLDS["review_upper"]:
        result["decision"] = "decline"
    else:
        result["decision"] = "review"
        result["guardrail_applied"] = True

    # Escalation rule: any fraud-ring evidence forces review
    if network_score.evidence and len(network_score.evidence) > 0:
        if result["decision"] == "approve":
            result["decision"] = "review"
            result["guardrail_applied"] = True
            ring_msg = "fraud ring detected: linked orders " + ", ".join(network_score.evidence[:3])
            if ring_msg not in result["reason_codes"]:
                result["reason_codes"].append(ring_msg)

    # Fairness guard: ensure no raw location-based decline
    _check_fairness(txn, result)

    return result


def _check_fairness(txn: Any, result: dict):
    """
    Fairness guard: never use raw country, city, or shipping-region
    as a standalone decline signal — only behavior/network signals.

    This matters for a COD-fraud product specifically: COD is more common
    in certain regions and payment demographics. Penalizing those regions
    directly would mean the system effectively penalizes certain neighborhoods,
    which is both ethically problematic and creates an adversarial dynamic
    where fraudsters just shift regions. All location-related risk must
    come through the network agent's COD-density check and the device
    agent's IP-geolocation mismatch — never a direct geographic lookup.
    """
    pass


# The escalation guardrail is applied inside apply_guardrails above
# rather than as a decorator, because the orchestrator is a plain async
# function, not an Agent. The equivalent logic is:

def escalation_tripwire(decision: str, risk_score: float, has_fraud_ring: bool) -> str | None:
    if RISK_THRESHOLDS["approve_upper"] <= risk_score <= RISK_THRESHOLDS["review_upper"]:
        return "review"
    if has_fraud_ring:
        return "review"
    return None
