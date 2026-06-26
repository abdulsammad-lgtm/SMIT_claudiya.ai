import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum

from agents import Agent, Runner

from app.api.schemas import TransactionDecision, AgentScoreOutput, TransactionIn
from app.db.models import Transaction
from app.orchestration.composite_scorer import WeightedScorer, EnsembleScorer, MaxScorer
from app.orchestration.coordinator import AgentCoordinator, ExecutionPlan, ExecutionMode
from app.orchestration.pipeline import ScoringPipeline
from app.guardrail.guardrail import compute_reason_codes
from app.services.risk_engine import RiskEngine, ScoringStrategy


@dataclass
class OrchestratorConfig:
    default_strategy: ScoringStrategy = ScoringStrategy.WEIGHTED
    enable_reasoning: bool = False
    parallel_execution: bool = True
    fallback_to_fast: bool = True
    timeout_per_agent: float = 30.0


class RiskOrchestrator:
    def __init__(self, config: OrchestratorConfig | None = None):
        self.config = config or OrchestratorConfig()
        self.engine = RiskEngine(
            strategy=self.config.default_strategy,
            enable_reasoning=self.config.enable_reasoning,
        )

    async def score_transaction(
        self,
        txn_in: TransactionIn,
        use_reasoning: bool | None = None,
    ) -> TransactionDecision:
        return await self.engine.score(txn_in, use_reasoning=use_reasoning)

    async def score_with_plan(
        self,
        txn_in: TransactionIn,
        strategy: ScoringStrategy | None = None,
        use_reasoning: bool | None = None,
    ) -> TransactionDecision:
        engine = RiskEngine(
            strategy=strategy or self.config.default_strategy,
            enable_reasoning=use_reasoning or self.config.enable_reasoning,
        )
        return await engine.score(txn_in, use_reasoning=use_reasoning)

    async def benchmark(
        self,
        txn_in: TransactionIn,
        strategies: list[ScoringStrategy] | None = None,
    ) -> dict[str, dict]:
        if strategies is None:
            strategies = list(ScoringStrategy)

        results = {}
        for strat in strategies:
            engine = RiskEngine(strategy=strat)
            result = await engine.score_with_timings(txn_in)
            results[strat.value] = result
        return results


orchestrator_agent = Agent(
    name="RiskOrchestrator",
    instructions=(
        "You are the Risk Orchestrator — the central coordinator for a multi-agent fraud detection platform. "
        "Coordinate parallel execution of Device, Behavior, and Network agents. "
        "Composite scores into a final risk assessment. Apply guardrails. "
        "Output a TransactionDecision with reason codes."
    ),
    model="gpt-4o-mini",
    output_type=TransactionDecision,
)


async def direct_orchestrate(
    txn_in: TransactionIn,
    use_reasoning: bool = False,
) -> TransactionDecision:
    orchestrator = RiskOrchestrator(
        OrchestratorConfig(
            enable_reasoning=use_reasoning,
        )
    )
    return await orchestrator.score_transaction(txn_in, use_reasoning=use_reasoning)
