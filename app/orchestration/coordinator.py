import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents import Runner

from app.api.schemas import AgentScoreOutput, TransactionIn
from app.db.models import Transaction
from app.agents.device_agent import device_agent, fast_path_device
from app.agents.behavior_agent import behavior_agent, fast_path_behavior
from app.agents.network_agent import network_agent, fast_path_network
from app.agents.transaction_agent import transaction_agent, fast_path_transaction
from app.agents.behavioral_agent import behavioral_agent, fast_path_behavioral


class ExecutionMode(Enum):
    FAST = "fast"
    REASONING = "reasoning"
    HYBRID = "hybrid"


@dataclass
class ExecutionPlan:
    mode: ExecutionMode
    agents: list[str] = field(default_factory=lambda: ["device", "behavior", "network", "transaction", "behavioral"])
    timeout_per_agent: float = 30.0
    fallback_to_fast: bool = True


class AgentResult:
    def __init__(self, name: str, score: AgentScoreOutput, latency_ms: float, from_reasoning: bool = False):
        self.name = name
        self.score = score
        self.latency_ms = latency_ms
        self.from_reasoning = from_reasoning


async def _run_agent_with_fallback(
    agent,
    fast_path_fn,
    txn: Transaction,
    input_text: str,
    timeout_sec: float = 30.0,
) -> tuple[AgentScoreOutput, bool]:
    try:
        start = time.perf_counter()
        result = await asyncio.wait_for(
            Runner.run(agent, input_text),
            timeout=timeout_sec,
        )
        elapsed = (time.perf_counter() - start) * 1000
        return result.final_output, True
    except Exception:
        start = time.perf_counter()
        output = await fast_path_fn(txn)
        elapsed = (time.perf_counter() - start) * 1000
        return output, False


class AgentCoordinator:
    def __init__(self, plan: ExecutionPlan | None = None):
        self.plan = plan or ExecutionPlan(mode=ExecutionMode.FAST)

    async def execute_all(
        self,
        txn: Transaction,
        txn_in: TransactionIn | None = None,
    ) -> dict[str, AgentResult]:
        input_text = f"Score transaction {txn.order_id}"

        if self.plan.mode == ExecutionMode.FAST:
            return await self._execute_fast(txn)
        elif self.plan.mode == ExecutionMode.REASONING:
            return await self._execute_reasoning(txn, input_text)
        else:
            return await self._execute_hybrid(txn, input_text)

    async def _execute_fast(self, txn: Transaction) -> dict[str, AgentResult]:
        start = time.perf_counter()
        results = await asyncio.gather(
            fast_path_device(txn), fast_path_behavior(txn),
            fast_path_network(txn), fast_path_transaction(txn),
            fast_path_behavioral(txn),
        )
        elapsed = (time.perf_counter() - start) * 1000
        per_agent = elapsed / 5
        return {
            "device": AgentResult("device", results[0], per_agent),
            "behavior": AgentResult("behavior", results[1], per_agent),
            "network": AgentResult("network", results[2], per_agent),
            "transaction": AgentResult("transaction", results[3], per_agent),
            "behavioral": AgentResult("behavioral", results[4], per_agent),
        }

    async def _execute_reasoning(self, txn: Transaction, input_text: str) -> dict[str, AgentResult]:
        timeout = self.plan.timeout_per_agent
        results = await asyncio.gather(
            _run_agent_with_fallback(device_agent, fast_path_device, txn, input_text, timeout),
            _run_agent_with_fallback(behavior_agent, fast_path_behavior, txn, input_text, timeout),
            _run_agent_with_fallback(network_agent, fast_path_network, txn, input_text, timeout),
            _run_agent_with_fallback(transaction_agent, fast_path_transaction, txn, input_text, timeout),
            _run_agent_with_fallback(behavioral_agent, fast_path_behavioral, txn, input_text, timeout),
        )

        return {
            "device": AgentResult("device", results[0][0], 0, results[0][1]),
            "behavior": AgentResult("behavior", results[1][0], 0, results[1][1]),
            "network": AgentResult("network", results[2][0], 0, results[2][1]),
            "transaction": AgentResult("transaction", results[3][0], 0, results[3][1]),
            "behavioral": AgentResult("behavioral", results[4][0], 0, results[4][1]),
        }

    async def _execute_hybrid(self, txn: Transaction, input_text: str) -> dict[str, AgentResult]:
        fast_results = await self._execute_fast(txn)
        high_risk_agents = [
            name for name, r in fast_results.items()
            if r.score.score > 30
        ]

        if not high_risk_agents:
            return fast_results

        reasoning_tasks = {}
        timeout = self.plan.timeout_per_agent
        agent_map = {
            "device": device_agent, "behavior": behavior_agent,
            "network": network_agent, "transaction": transaction_agent,
            "behavioral": behavioral_agent,
        }
        fast_map = {
            "device": fast_path_device, "behavior": fast_path_behavior,
            "network": fast_path_network, "transaction": fast_path_transaction,
            "behavioral": fast_path_behavioral,
        }
        for name in high_risk_agents:
            reasoning_tasks[name] = _run_agent_with_fallback(
                agent_map[name], fast_map[name], txn, input_text, timeout
            )

        reasoning_results = await asyncio.gather(*reasoning_tasks.values())
        for name, (output, from_reasoning) in zip(high_risk_agents, reasoning_results):
            fast_results[name] = AgentResult(name, output, 0, from_reasoning)

        return fast_results
