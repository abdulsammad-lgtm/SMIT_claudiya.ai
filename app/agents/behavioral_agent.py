from agents import Agent, function_tool, Runner

from app.api.schemas import AgentScoreOutput
from app.db.models import Transaction
from app.orchestrator.policy import score_from_signal
from app.tools.behavior_analysis import (
    _analyze_login_anomaly,
    _analyze_session_pattern,
    _analyze_typing_biometrics,
    _analyze_mouse_behavior,
    _analyze_user_behavior_profile,
    compute_behavioral_intelligence_score,
)
from app.tools.behavior_analysis import (
    analyze_login_anomaly,
    analyze_session_pattern,
    analyze_typing_biometrics,
    analyze_mouse_behavior,
    analyze_user_behavior_profile,
)


async def fast_path_behavioral(txn: Transaction) -> AgentScoreOutput:
    score, reasons = await compute_behavioral_intelligence_score(
        customer_id=txn.customer_id,
        ip_address=txn.ip_address,
        user_agent=txn.user_agent,
        device_fingerprint=txn.device_fingerprint,
        session_duration_seconds=txn.session_duration_seconds,
        amount=txn.amount,
    )
    return AgentScoreOutput(
        score=score,
        confidence=0.85,
        explanation="; ".join(reasons) if reasons else "behavioral signals clean",
        evidence=reasons,
    )


behavioral_agent_instructions = (
    "You are a behavioral intelligence analyst. Analyze user behavior for fraud signals including:\n"
    "- Login anomalies (unusual IPs, user agents, login frequency)\n"
    "- Session analysis (duration anomalies, amount-to-duration ratio)\n"
    "- Behavioral biometrics (typing patterns suggesting automation, mouse movement naturalness)\n"
    "- User profile stability (changes in preferences, IP volatility)\n"
    "Output a score 0-100, confidence 0-1, and a plain-language explanation."
)
behavioral_agent = Agent(
    name="BehavioralAgent",
    instructions=behavioral_agent_instructions,
    model="gpt-4o-mini",
    tools=[
        analyze_login_anomaly,
        analyze_session_pattern,
        analyze_typing_biometrics,
        analyze_mouse_behavior,
        analyze_user_behavior_profile,
    ],
    output_type=AgentScoreOutput,
)
