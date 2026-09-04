"""Bounded information-gain planning primitives.

Execution lifecycle integration is intentionally kept outside this module; an
Observation is a plan, not permission to execute it.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Hypothesis:
    name: str
    probability: float
    predictions: dict[str, dict[str, float]]
    state: str = "unresolved"

    @property
    def hypothesis_id(self) -> str:
        return f"hypothesis:{self.name}"

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")


@dataclass(frozen=True)
class Observation:
    name: str
    outcomes: list[str]
    cost: float
    authorized: bool = True
    domain: str = "target"
    discriminates_hypothesis_ids: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()
    rationale: str = ""

    def __post_init__(self):
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

    @property
    def hypothesis_pair(self):
        return self.discriminates_hypothesis_ids


@dataclass(frozen=True)
class Plan:
    observation: str
    expected_information_gain: float
    utility: float
    rationale: str
    discriminates_hypothesis_ids: tuple[str, ...] = ()


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
    total = sum(max(0.0, h.probability) for h in hypotheses)
    if total <= 0:
        return None
    priors = {h.name: max(0.0, h.probability) / total for h in hypotheses}
    prior = _entropy(priors.values())
    expected = 0.0
    known = False
    for outcome in observation.outcomes:
        likelihood = {h.name: max(0.0, h.predictions.get(observation.name, {}).get(outcome, 0.0)) for h in hypotheses}
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
    return Plan(observation.name, round(gain, 6), round(utility, 6), "Selected by expected information gain per unit cost.", observation.discriminates_hypothesis_ids)
