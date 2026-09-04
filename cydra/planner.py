"""Bounded information-gain planning primitives.

An Observation is a plan, not permission to execute it. Persistent hypothesis
state lives in :mod:`cydra.hypothesis`; execution identity is attached to the
plan before an execution boundary may consume it.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from uuid import uuid4

from .execution_request import ExecutionRequest
from .hypothesis import Hypothesis


@dataclass(frozen=True)
class Observation:
    name: str
    outcomes: list[str]
    cost: float
    authorized: bool = True
    execution_id: str | None = None
    execution_request_digest: str | None = None
    execution_request: ExecutionRequest | None = None
    domain: str = "target"
    discriminates_hypothesis_ids: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("observation name must not be empty")
        if self.cost <= 0:
            raise ValueError("observation cost must be positive")
        if self.domain not in {"target", "meta"}:
            raise ValueError("observation domain must be 'target' or 'meta'")
        pair = tuple(self.discriminates_hypothesis_ids)
        if pair and (len(pair) != 2 or pair[0] == pair[1] or any(not x.strip() for x in pair)):
            raise ValueError("discriminating observation requires two distinct non-empty hypothesis IDs")
        object.__setattr__(self, "discriminates_hypothesis_ids", pair)
        object.__setattr__(self, "target_ids", tuple(self.target_ids))
        if self.execution_request is not None:
            if not isinstance(self.execution_request, ExecutionRequest):
                raise TypeError("execution_request must be canonical ExecutionRequest")
            if self.execution_id is None:
                object.__setattr__(self, "execution_id", self.execution_request.execution_id)
            if self.execution_id != self.execution_request.execution_id:
                raise ValueError("observation execution identity does not match execution request")
            digest = self.execution_request.digest
            if self.execution_request_digest is None:
                object.__setattr__(self, "execution_request_digest", digest)
            elif self.execution_request_digest != digest:
                raise ValueError("observation execution request digest does not match canonical request")
        elif self.execution_request_digest is not None and self.execution_id is None:
            raise ValueError("execution request digest requires execution identity")

    @property
    def hypothesis_pair(self):
        return self.discriminates_hypothesis_ids

    @property
    def planned_execution_id(self) -> str | None:
        return self.execution_id

    @property
    def planned_request_digest(self) -> str | None:
        return self.execution_request_digest


@dataclass(frozen=True)
class Plan:
    observation: str
    expected_information_gain: float
    utility: float
    rationale: str
    discriminates_hypothesis_ids: tuple[str, ...] = ()
    execution_id: str | None = None
    execution_request_digest: str | None = None


def _entropy(values):
    return -sum(p * math.log2(p) for p in values if p > 0)


def information_gain(hypotheses: list[Hypothesis], observation: Observation) -> float | None:
    if not hypotheses or not observation.authorized:
        return None
    if observation.discriminates_hypothesis_ids:
        wanted = set(observation.discriminates_hypothesis_ids)
        hypotheses = [h for h in hypotheses if h.hypothesis_id in wanted]
        if {h.hypothesis_id for h in hypotheses} != wanted:
            return None
    total = sum(max(0.0, h.belief) for h in hypotheses)
    if total <= 0:
        return None
    priors = {h.name: max(0.0, h.belief) / total for h in hypotheses}
    prior = _entropy(priors.values())
    expected = 0.0
    known = False
    for outcome in observation.outcomes:
        likelihood = {h.name: max(0.0, h.planning_predictions.get(observation.name, {}).get(outcome, 0.0)) for h in hypotheses}
        if not any(likelihood.values()):
            continue
        known = True
        p_out = sum(priors[h.name] * likelihood[h.name] for h in hypotheses)
        if p_out <= 0:
            continue
        posterior = {name: priors[name] * likelihood[name] / p_out for name in priors}
        expected += p_out * _entropy(posterior.values())
    return max(0.0, prior - expected) if known else None


def choose_next_observation(hypotheses: list[Hypothesis], observations: list[Observation], **_) -> Plan | None:
    candidates = []
    for observation in observations:
        gain = information_gain(hypotheses, observation)
        if gain is not None:
            candidates.append((gain / observation.cost, gain, observation))
    if not candidates:
        return None
    utility, gain, observation = sorted(candidates, key=lambda x: (-x[0], -x[1], x[2].name))[0]
    return Plan(
        observation.name,
        round(gain, 6),
        round(utility, 6),
        "Selected by expected information gain per unit cost.",
        observation.discriminates_hypothesis_ids,
        observation.execution_id,
        observation.execution_request_digest,
    )


def new_execution_id() -> str:
    """Create an opaque execution identity; it carries no authority."""
    return f"exec:{uuid4().hex}"
