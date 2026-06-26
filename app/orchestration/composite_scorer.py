import abc
from typing import Protocol

from app.api.schemas import AgentScoreOutput
from app.orchestrator.policy import FAST_PATH_WEIGHTS, BASE_CONFIDENCE


class CompositeScorer(abc.ABC):
    @abc.abstractmethod
    async def compute(
        self,
        device: AgentScoreOutput,
        behavior: AgentScoreOutput,
        network: AgentScoreOutput,
        transaction: AgentScoreOutput | None = None,
        behavioral: AgentScoreOutput | None = None,
    ) -> tuple[float, float]:
        ...


class WeightedScorer(CompositeScorer):
    def __init__(self, weights: dict[str, float] | None = None, base_confidence: float = BASE_CONFIDENCE):
        self.weights = weights or FAST_PATH_WEIGHTS
        self.base_confidence = base_confidence

    async def compute(
        self,
        device: AgentScoreOutput,
        behavior: AgentScoreOutput,
        network: AgentScoreOutput,
        transaction: AgentScoreOutput | None = None,
        behavioral: AgentScoreOutput | None = None,
    ) -> tuple[float, float]:
        txn_score = transaction.score if transaction else 0.0
        beh_score = behavioral.score if behavioral else 0.0

        weighted = (
            self.weights["device"] * device.score
            + self.weights["behavior"] * behavior.score
            + self.weights["network"] * network.score
            + self.weights.get("transaction", 0.0) * txn_score
            + self.weights.get("behavioral", 0.0) * beh_score
        )
        raw_risk = min(100.0, max(0.0, weighted))

        conf = self.base_confidence
        for s in [device.score, behavior.score, network.score, txn_score, beh_score]:
            conf *= (1.0 - s / 200)
        confidence = min(1.0, conf)
        return raw_risk, confidence


class MaxScorer(CompositeScorer):
    async def compute(
        self,
        device: AgentScoreOutput,
        behavior: AgentScoreOutput,
        network: AgentScoreOutput,
        transaction: AgentScoreOutput | None = None,
        behavioral: AgentScoreOutput | None = None,
    ) -> tuple[float, float]:
        scores = [device.score, behavior.score, network.score]
        if transaction:
            scores.append(transaction.score)
        if behavioral:
            scores.append(behavioral.score)
        raw_risk = max(scores)
        confidence = BASE_CONFIDENCE
        return raw_risk, confidence


class EnsembleScorer(CompositeScorer):
    def __init__(self, scorers: list[tuple[CompositeScorer, float]]):
        self.scorers = scorers

    async def compute(
        self,
        device: AgentScoreOutput,
        behavior: AgentScoreOutput,
        network: AgentScoreOutput,
        transaction: AgentScoreOutput | None = None,
        behavioral: AgentScoreOutput | None = None,
    ) -> tuple[float, float]:
        total_weight = sum(w for _, w in self.scorers)
        weighted_risk = 0.0
        weighted_conf = 0.0
        for scorer, weight in self.scorers:
            risk, conf = await scorer.compute(device, behavior, network, transaction, behavioral)
            weighted_risk += risk * (weight / total_weight)
            weighted_conf += conf * (weight / total_weight)
        return weighted_risk, weighted_conf
