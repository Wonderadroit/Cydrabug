"""Explicit Observation -> Evidence -> Verification -> BeliefUpdate bridge.

Receipt authenticity and semantic meaning are separate boundaries. This module
requires the caller to declare how each observation outcome maps to the exact
hypotheses the observation was planned to discriminate. It never infers polarity
from confidence, ranking, or outcome names alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .execution_evidence import ExecutionEvidence
from .hypothesis import BeliefUpdate, Hypothesis, update_hypothesis
from .invariants import CandidateVerification, VerificationEvidence, VerificationRole, VerificationState


@dataclass(frozen=True)
class ObservationVerificationBinding:
    """Explicit semantic contract for one discriminating observation."""

    observation_name: str
    hypothesis_ids: tuple[str, str]
    outcome_roles: Mapping[str, tuple[VerificationRole, VerificationRole]]

    def __post_init__(self) -> None:
        if not self.observation_name.strip():
            raise ValueError("observation_name must not be empty")
        pair = tuple(self.hypothesis_ids)
        if len(pair) != 2 or pair[0] == pair[1] or any(not item.strip() for item in pair):
            raise ValueError("binding requires two distinct hypothesis IDs")
        object.__setattr__(self, "hypothesis_ids", pair)
        if not self.outcome_roles:
            raise ValueError("outcome_roles must not be empty")
        normalized = {}
        for outcome, roles in self.outcome_roles.items():
            if not isinstance(outcome, str) or not outcome.strip():
                raise ValueError("outcome names must be non-empty strings")
            roles = tuple(roles)
            if len(roles) != 2 or any(not isinstance(role, VerificationRole) for role in roles):
                raise ValueError("each outcome must explicitly map to two VerificationRole values")
            normalized[outcome] = roles
        object.__setattr__(self, "outcome_roles", normalized)


def _state_for_role(role: VerificationRole) -> VerificationState:
    if role == VerificationRole.SUPPORTS:
        return VerificationState.SUPPORTED
    if role == VerificationRole.CONTRADICTS:
        return VerificationState.CONTRADICTED
    return VerificationState.UNRESOLVED


def verification_from_execution_evidence(
    *, evidence: ExecutionEvidence, binding: ObservationVerificationBinding
) -> tuple[tuple[VerificationEvidence, VerificationEvidence], tuple[CandidateVerification, CandidateVerification]]:
    """Translate one exact receipt-bound outcome using only an explicit mapping."""
    if evidence.observation_name != binding.observation_name:
        raise ValueError("evidence observation does not match verification binding")
    if evidence.outcome not in binding.outcome_roles:
        raise ValueError(f"unmapped observation outcome: {evidence.outcome}")
    if evidence.polarity != "neutral":
        raise ValueError("execution evidence must reach this boundary with neutral polarity")

    semantic_evidence = tuple(
        VerificationEvidence(
            evidence_id=evidence.evidence_id,
            role=role,
            confidence=evidence.confidence,
            rationale=f"explicit outcome mapping: {evidence.outcome} -> {role.value}",
        )
        for role in binding.outcome_roles[evidence.outcome]
    )
    verifications = tuple(
        CandidateVerification(
            candidate_id=hypothesis_id,
            state=_state_for_role(role),
            evidence_ids=(evidence.evidence_id,),
            supporting_ids=(evidence.evidence_id,) if role == VerificationRole.SUPPORTS else (),
            contradicting_ids=(evidence.evidence_id,) if role == VerificationRole.CONTRADICTS else (),
            confidence=evidence.confidence,
        )
        for hypothesis_id, role in zip(binding.hypothesis_ids, binding.outcome_roles[evidence.outcome])
    )
    return semantic_evidence, verifications


def apply_observation_evidence(
    *, hypotheses: Sequence[Hypothesis], evidence: ExecutionEvidence,
    binding: ObservationVerificationBinding,
) -> tuple[tuple[Hypothesis, ...], tuple[BeliefUpdate, ...]]:
    """Apply one explicitly mapped observation to its exact two hypotheses."""
    expected = set(binding.hypothesis_ids)
    selected = {item.hypothesis_id: item for item in hypotheses if item.hypothesis_id in expected}
    if set(selected) != expected:
        raise ValueError("verification binding references hypotheses that were not supplied")
    semantic_evidence, verifications = verification_from_execution_evidence(
        evidence=evidence, binding=binding
    )
    updated = []
    updates = []
    for hypothesis_id, semantic, verification in zip(binding.hypothesis_ids, semantic_evidence, verifications):
        new_hypothesis, update = update_hypothesis(selected[hypothesis_id], verification, (semantic,))
        updated.append(new_hypothesis)
        updates.append(update)
    return tuple(updated), tuple(updates)
