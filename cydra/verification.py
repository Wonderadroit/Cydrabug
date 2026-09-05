"""Variant-aware verification boundary for invariant experiments.

Execution results are observations, not truth. This module converts explicitly
classified, provenance-bound variant observations into CandidateVerification;
it never executes tests or promotes a candidate without observed evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .invariants import CandidateVerification, VerificationEvidence, VerificationRole, VerificationState


@dataclass(frozen=True)
class VariantObservation:
    """One independently identified experiment variant."""

    variant_id: str
    evidence_id: str
    outcome: str
    mechanism_fingerprint: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        for field in ("variant_id", "evidence_id", "outcome", "mechanism_fingerprint"):
            if not getattr(self, field).strip():
                raise ValueError(f"{field} must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


def verify_candidate_from_variants(
    candidate_id: str,
    observations: Iterable[VariantObservation],
) -> tuple[CandidateVerification, tuple[VerificationEvidence, ...]]:
    """Classify a candidate from variant observations without executing anything.

    A supported result requires at least two distinct variants, all with the
    preserved outcome, and a common mechanism fingerprint. A preserved result
    contradicts the violation hypothesis. Mixed outcomes or mechanisms remain
    unresolved. Identical repeated executions do not count as distinct variants.
    """
    if not candidate_id.strip():
        raise ValueError("candidate_id must not be empty")
    items = tuple(observations)
    if not items:
        return CandidateVerification(candidate_id, VerificationState.UNRESOLVED, (), (), (), 0.0), ()
    if len({item.evidence_id for item in items}) != len(items):
        raise ValueError("variant observations require unique evidence IDs")

    evidence = tuple(
        VerificationEvidence(
            item.evidence_id,
            VerificationRole.SUPPORTS if item.outcome == "INVARIANT_VIOLATED" else
            VerificationRole.CONTRADICTS if item.outcome == "INVARIANT_PRESERVED" else
            VerificationRole.NEUTRAL,
            item.confidence,
            f"variant={item.variant_id}; mechanism={item.mechanism_fingerprint}; outcome={item.outcome}",
        )
        for item in items
    )
    ids = tuple(item.evidence_id for item in items)
    violating = tuple(item.evidence_id for item in items if item.outcome == "INVARIANT_VIOLATED")
    preserved = tuple(item.evidence_id for item in items if item.outcome == "INVARIANT_PRESERVED")
    distinct_variants = {item.variant_id for item in items}
    mechanisms = {item.mechanism_fingerprint for item in items}

    if len(distinct_variants) < 2:
        return CandidateVerification(candidate_id, VerificationState.UNRESOLVED, ids, (), (), min(item.confidence for item in items)), evidence
    if violating and preserved:
        return CandidateVerification(candidate_id, VerificationState.UNRESOLVED, ids, (), (), min(item.confidence for item in items)), evidence
    if not violating and preserved:
        return CandidateVerification(candidate_id, VerificationState.CONTRADICTED, ids, (), preserved, min(item.confidence for item in items)), evidence
    if violating and len(mechanisms) == 1:
        confidence = min(item.confidence for item in items)
        return CandidateVerification(candidate_id, VerificationState.SUPPORTED, ids, violating, (), confidence), evidence
    return CandidateVerification(candidate_id, VerificationState.UNRESOLVED, ids, (), (), min(item.confidence for item in items)), evidence
