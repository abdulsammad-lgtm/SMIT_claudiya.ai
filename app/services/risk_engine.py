import time
from enum import Enum

from agents import Agent, Runner

from app.api.schemas import TransactionDecision, TransactionIn
from app.orchestration.pipeline import ScoringPipeline
from app.orchestration.coordinator import AgentCoordinator, ExecutionPlan, ExecutionMode
from app.orchestration.composite_scorer import WeightedScorer, EnsembleScorer, MaxScorer


class ScoringStrategy(Enum):
    WEIGHTED = "weighted"
    MAX = "max"
    ENSEMBLE = "ensemble"


class RiskEngine:
    def __init__(
        self,
        strategy: ScoringStrategy = ScoringStrategy.WEIGHTED,
        enable_reasoning: bool = False,
    ):
        self.strategy = strategy
        self.enable_reasoning = enable_reasoning
        self._pipeline: ScoringPipeline | None = None

    @property
    def pipeline(self) -> ScoringPipeline:
        if self._pipeline is None:
            mode = ExecutionMode.REASONING if self.enable_reasoning else ExecutionMode.FAST
            plan = ExecutionPlan(mode=mode)
            coordinator = AgentCoordinator(plan)

            if self.strategy == ScoringStrategy.WEIGHTED:
                scorer = WeightedScorer()
            elif self.strategy == ScoringStrategy.MAX:
                scorer = MaxScorer()
            elif self.strategy == ScoringStrategy.ENSEMBLE:
                scorer = EnsembleScorer([
                    (WeightedScorer(), 0.7),
                    (MaxScorer(), 0.3),
                ])
            else:
                scorer = WeightedScorer()

            self._pipeline = ScoringPipeline(
                coordinator=coordinator,
                scorer=scorer,
            )

        return self._pipeline

    async def score(
        self,
        txn_in: TransactionIn,
        use_reasoning: bool | None = None,
    ) -> TransactionDecision:
        reasoning = use_reasoning if use_reasoning is not None else self.enable_reasoning
        result = await self.pipeline.run(txn_in, use_reasoning=reasoning)
        return result.decision

    async def score_with_timings(
        self,
        txn_in: TransactionIn,
        use_reasoning: bool | None = None,
    ):
        reasoning = use_reasoning if use_reasoning is not None else self.enable_reasoning
        result = await self.pipeline.run(txn_in, use_reasoning=reasoning)
        return {
            "decision": result.decision,
            "stage_timings_ms": result.stage_timings,
            "total_ms": result.decision.latency_ms,
            "pipeline_version": result.pipeline_version,
        }


orchestrator_agent_instructions = (
    "You are the Risk Orchestrator — the central coordinator for a multi-agent fraud detection platform. "
    "Your role is to:\n"
    "1. Receive a transaction and determine the optimal execution plan\n"
    "2. Coordinate parallel execution of specialist agents (Device, Behavior, Network)\n"
    "3. Composite scores from all agents into a final risk assessment\n"
    "4. Apply guardrails to ensure fairness and explainability\n"
    "5. Return a final decision with reason codes\n\n"
    "You handle three execution modes:\n"
    "- FAST: Deterministic scoring (under 150ms) for most transactions\n"
    "- REASONING: Full agent loop with LLM reasoning for borderline/high-risk cases\n"
    "- HYBRID: Fast path first, then reasoning only for high-scoring agents\n\n"
    "The final decision must be one of: approve (risk < 30), review (risk 30-70), decline (risk > 70).\n"
    "Never use raw location as a decline signal."
)

orchestrator_agent = Agent(
    name="RiskOrchestrator",
    instructions=orchestrator_agent_instructions,
    model="gpt-4o-mini",
    output_type=TransactionDecision,
)
