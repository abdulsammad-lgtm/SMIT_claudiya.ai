import time
import json
from dataclasses import dataclass, field
from enum import Enum

from app.api.schemas import TransactionDecision, AgentScoreOutput, TransactionIn
from app.db.models import Transaction, async_session, AuditLog
from app.orchestration.coordinator import AgentCoordinator, ExecutionPlan, ExecutionMode, AgentResult
from app.orchestration.composite_scorer import CompositeScorer, WeightedScorer
from app.guardrail.guardrail import apply_guardrails, compute_reason_codes
from sqlalchemy import select


class PipelineStage(Enum):
    INIT = "init"
    AGENT_EXECUTION = "agent_execution"
    COMPOSITE_SCORING = "composite_scoring"
    GUARDRAIL = "guardrail"
    PERSIST = "persist"
    COMPLETE = "complete"


@dataclass
class PipelineResult:
    decision: TransactionDecision
    agent_raw: dict = field(default_factory=dict)
    guardrail_result: dict = field(default_factory=dict)
    stage_timings: dict[str, float] = field(default_factory=dict)
    pipeline_version: str = "2.0"


class ScoringPipeline:
    def __init__(
        self,
        coordinator: AgentCoordinator | None = None,
        scorer: CompositeScorer | None = None,
    ):
        self.coordinator = coordinator or AgentCoordinator(
            ExecutionPlan(mode=ExecutionMode.FAST)
        )
        self.scorer = scorer or WeightedScorer()

    async def run(
        self,
        txn_in: TransactionIn,
        use_reasoning: bool = False,
    ) -> PipelineResult:
        timings: dict[str, float] = {}
        pipeline_start = time.perf_counter()

        txn = await self._stage_init(txn_in)
        timings["init"] = (time.perf_counter() - pipeline_start) * 1000

        if use_reasoning:
            self.coordinator.plan.mode = ExecutionMode.REASONING

        agent_start = time.perf_counter()
        agent_results = await self.coordinator.execute_all(txn, txn_in)
        timings["agent_execution"] = (time.perf_counter() - agent_start) * 1000

        agent_raw = {
            name: r.score.model_dump()
            for name, r in agent_results.items()
        }
        agent_scores = {
            name: r.score.score
            for name, r in agent_results.items()
        }

        scoring_start = time.perf_counter()
        raw_risk, confidence = await self.scorer.compute(
            agent_results["device"].score,
            agent_results["behavior"].score,
            agent_results["network"].score,
            agent_results.get("transaction").score if "transaction" in agent_results else None,
            agent_results.get("behavioral").score if "behavioral" in agent_results else None,
        )
        timings["composite_scoring"] = (time.perf_counter() - scoring_start) * 1000

        reason_codes = compute_reason_codes(
            agent_results["device"].score,
            agent_results["behavior"].score,
            agent_results["network"].score,
        )

        guardrail_start = time.perf_counter()
        guardrail_result = await apply_guardrails(
            raw_risk, agent_scores, reason_codes, agent_raw,
            agent_results["device"].score,
            agent_results["behavior"].score,
            agent_results["network"].score,
            txn,
        )
        timings["guardrail"] = (time.perf_counter() - guardrail_start) * 1000

        elapsed = (time.perf_counter() - pipeline_start) * 1000
        decision = TransactionDecision(
            order_id=txn.order_id,
            decision=guardrail_result["decision"],
            risk_score=round(guardrail_result["risk_score"], 1),
            confidence=round(guardrail_result["confidence"], 2),
            agent_scores=agent_scores,
            reason_codes=guardrail_result["reason_codes"],
            latency_ms=round(elapsed, 1),
        )

        persist_start = time.perf_counter()
        await self._stage_persist(txn, decision, agent_raw, guardrail_result)
        timings["persist"] = (time.perf_counter() - persist_start) * 1000

        return PipelineResult(
            decision=decision,
            agent_raw=agent_raw,
            guardrail_result=guardrail_result,
            stage_timings=timings,
            pipeline_version="2.0",
        )

    async def _stage_init(self, txn_in: TransactionIn) -> Transaction:
        async with async_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.order_id == txn_in.order_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            txn = Transaction(
                order_id=txn_in.order_id,
                customer_id=txn_in.customer_id,
                amount=txn_in.amount,
                currency=txn_in.currency,
                payment_method=txn_in.payment_method,
                device_fingerprint=txn_in.device_fingerprint,
                ip_address=txn_in.ip_address,
                phone_number=txn_in.phone_number,
                shipping_address=txn_in.shipping_address,
                user_agent=txn_in.user_agent,
                session_duration_seconds=txn_in.session_duration_seconds,
                timestamp=txn_in.timestamp,
            )
            session.add(txn)
            await session.commit()
            return txn

    async def _stage_persist(self, txn: Transaction, decision: TransactionDecision, agent_raw: dict, guardrail_result: dict):
        async with async_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.order_id == txn.order_id)
            )
            db_txn = result.scalar_one_or_none()
            if db_txn:
                db_txn.decision = decision.decision
                db_txn.risk_score = decision.risk_score
                db_txn.confidence = decision.confidence
                db_txn.agent_scores_json = json.dumps(decision.agent_scores)
                db_txn.reason_codes_json = json.dumps(decision.reason_codes)
                db_txn.latency_ms = decision.latency_ms
                db_txn.scoring_path = guardrail_result.get("scoring_path", "fast")

            audit = AuditLog(
                order_id=txn.order_id,
                event_type="score",
                new_decision=decision.decision,
                details_json=json.dumps({
                    "agent_scores": decision.agent_scores,
                    "risk_score": decision.risk_score,
                    "confidence": decision.confidence,
                    "reason_codes": decision.reason_codes,
                    "agent_raw": agent_raw,
                    "guardrail_applied": guardrail_result.get("guardrail_applied", False),
                    "pipeline_version": "2.0",
                }),
            )
            session.add(audit)
            await session.commit()
