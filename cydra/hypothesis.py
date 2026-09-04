"""Persistent, evidence-bound hypothesis state and belief updates.

Belief is uncertainty, not verification. Updates are bound to the exact
verification evidence IDs supplied by the caller; unbound evidence cannot
silently influence a hypothesis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from .invariants import CandidateVerification, VerificationEvidence, VerificationState


class HypothesisState(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    statement: str
    belief: float = 0.5
    state: HypothesisState = HypothesisState.UNRESOLVED
    planning_predictions: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.hypothesis_id.strip():
            raise ValueError("hypothesis_id must not be empty")
        if not self.statement.strip():
            raise ValueError("statement must not be empty")
        if not 0.0 <= self.belief <= 1.0:
            raise ValueError("belief must be between 0 and 1")

    @property
    def name(self) -> str:
        prefix = "hypothesis:"
        return self.hypothesis_id[len(prefix):] if self.hypothesis_id.startswith(prefix) else self.hypothesis_id

    @property
    def probability(self) -> float:
        return self.belief

    @property
    def predictions(self) -> dict[str, dict[str, float]]:
        return self.planning_predictions


@dataclass(frozen=True)
class BeliefUpdate:
    hypothesis_id: str
    prior_belief: float
    posterior_belief: float
    prior_state: HypothesisState
    posterior_state: HypothesisState
    evidence_ids: tuple[str, ...]
    rationale: str


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def update_hypothesis(
    hypothesis: Hypothesis,
    verification: CandidateVerification,
    evidence: Iterable[VerificationEvidence],
) -> tuple[Hypothesis, BeliefUpdate]:
    """Apply one explicit verification result without promoting it to proof."""
    items = tuple(evidence)
    supplied = {item.evidence_id for item in items}
    bound = tuple(verification.evidence_ids)
    if any(not item for item in bound):
        raise ValueError("verification contains an empty evidence ID")
    if not set(bound).issubset(supplied):
        raise ValueError("verification references evidence that was not supplied")

    relevant = tuple(item for item in items if item.evidence_id in bound and item.role.value != "neutral")
    if verification.state == VerificationState.SUPPORTED and relevant:
        strength = max(item.confidence for item in relevant)
        posterior = hypothesis.belief + (1.0 - hypothesis.belief) * strength * 0.5
        state = HypothesisState.SUPPORTED
        rationale = "supporting verification evidence increased belief"
    elif verification.state == VerificationState.CONTRADICTED and relevant:
        strength = max(item.confidence for item in relevant)
        posterior = hypothesis.belief * (1.0 - strength * 0.5)
        state = HypothesisState.CONTRADICTED
        rationale = "contradicting verification evidence decreased belief"
    else:
        posterior = hypothesis.belief
        state = HypothesisState.UNRESOLVED
        rationale = "verification remained unresolved; belief unchanged"

    updated = Hypothesis(
        hypothesis.hypothesis_id,
        hypothesis.statement,
        _clamp(posterior),
        state,
        dict(hypothesis.planning_predictions),
    )
    return updated, BeliefUpdate(
        hypothesis.hypothesis_id,
        hypothesis.belief,
        updated.belief,
        hypothesis.state,
        updated.state,
        bound,
        rationale,
    )
