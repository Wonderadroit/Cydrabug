"""Project-agnostic source identity and lineage reasoning.

CYDRA must not assume that a program's advertised Git revision is directly
fetchable from the first repository it discovers. Programs may publish forks,
snapshots, mirrors, tags, or other source locators. This module evaluates the
evidence supplied by acquisition adapters without itself knowing a platform or
project.

Important distinction:
    VERIFIED             = the advertised Git object is independently verified.
    PROVENANCE_SUPPORTED = evidence supports the declared lineage, but exact
                           Git identity is not independently proven.
    MISMATCH             = reliable evidence contradicts the advertised identity.
    UNRESOLVED            = evidence is insufficient to decide.

A declaration such as a commit message is evidence, never cryptographic proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LineageStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PROVENANCE_SUPPORTED = "PROVENANCE_SUPPORTED"
    MISMATCH = "MISMATCH"
    UNRESOLVED = "UNRESOLVED"


class EvidenceKind(str, Enum):
    EXACT_GIT_OBJECT = "EXACT_GIT_OBJECT"
    EXACT_HEAD_MATCH = "EXACT_HEAD_MATCH"
    DECLARED_LINEAGE = "DECLARED_LINEAGE"
    ANCESTRY_RELATION = "ANCESTRY_RELATION"
    CONTENT_MATCH = "CONTENT_MATCH"
    OBJECT_ABSENT = "OBJECT_ABSENT"
    IDENTITY_CONTRADICTION = "IDENTITY_CONTRADICTION"


@dataclass(frozen=True)
class SourceEvidence:
    """One independently collected fact about a source candidate."""

    kind: EvidenceKind
    source: str
    detail: str
    supports: bool

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.detail.strip():
            raise ValueError("detail must not be empty")


@dataclass(frozen=True)
class SourceCandidate:
    """A discovered source candidate and its observed Git identity."""

    locator: str
    observed_revision: str | None = None
    advertised_revision_available: bool = False
    observed_head_matches: bool = False
    lineage_to_advertised: bool = False
    declared_lineage: bool = False
    content_matches: bool = False
    contradictory_identity: bool = False

    def __post_init__(self) -> None:
        if not self.locator.strip():
            raise ValueError("locator must not be empty")


@dataclass(frozen=True)
class SourceIdentityResolution:
    """Fail-closed judgment over one or more source candidates."""

    advertised_revision: str
    status: LineageStatus
    selected_locator: str | None
    exact_identity_verified: bool
    evidence: tuple[SourceEvidence, ...]
    reason: str

    @property
    def ready_for_analysis(self) -> bool:
        return self.status is LineageStatus.VERIFIED


def resolve_source_identity(
    advertised_revision: str,
    candidates: tuple[SourceCandidate, ...] | list[SourceCandidate],
) -> SourceIdentityResolution:
    """Resolve source identity from evidence without platform-specific rules.

    Exact Git availability is decisive only when the observed revision itself
    equals the advertised revision. A repository merely containing some Git
    object while HEAD points elsewhere cannot be promoted to VERIFIED.
    Declared lineage, ancestry, or content similarity can support provenance,
    but cannot independently promote a candidate to VERIFIED.
    """
    revision = advertised_revision.strip().lower()
    if not revision:
        raise ValueError("advertised_revision must not be empty")

    candidates = tuple(candidates)
    evidence: list[SourceEvidence] = []

    for candidate in candidates:
        if candidate.contradictory_identity:
            evidence.append(SourceEvidence(
                EvidenceKind.IDENTITY_CONTRADICTION,
                candidate.locator,
                "candidate contains evidence contradicting the advertised source identity",
                False,
            ))
            continue

        exact_object = candidate.advertised_revision_available
        observed_matches = candidate.observed_head_matches
        observed_revision_matches = (
            candidate.observed_revision is not None
            and candidate.observed_revision.strip().lower() == revision
        )

        if exact_object:
            evidence.append(SourceEvidence(
                EvidenceKind.EXACT_GIT_OBJECT,
                candidate.locator,
                f"advertised Git object {revision} is independently available",
                True,
            ))
            if observed_matches and observed_revision_matches:
                evidence.append(SourceEvidence(
                    EvidenceKind.EXACT_HEAD_MATCH,
                    candidate.locator,
                    "observed checkout HEAD exactly matches the advertised revision",
                    True,
                ))
                return SourceIdentityResolution(
                    advertised_revision=revision,
                    status=LineageStatus.VERIFIED,
                    selected_locator=candidate.locator,
                    exact_identity_verified=True,
                    evidence=tuple(evidence),
                    reason="exact advertised Git identity independently verified",
                )
            if observed_matches and not observed_revision_matches:
                evidence.append(SourceEvidence(
                    EvidenceKind.IDENTITY_CONTRADICTION,
                    candidate.locator,
                    "candidate reports HEAD matching an identity different from the advertised revision",
                    False,
                ))
        else:
            evidence.append(SourceEvidence(
                EvidenceKind.OBJECT_ABSENT,
                candidate.locator,
                f"advertised Git object {revision} is not independently available",
                False,
            ))

        if candidate.declared_lineage:
            evidence.append(SourceEvidence(
                EvidenceKind.DECLARED_LINEAGE,
                candidate.locator,
                "candidate explicitly declares lineage to the advertised revision",
                True,
            ))
        if candidate.lineage_to_advertised:
            evidence.append(SourceEvidence(
                EvidenceKind.ANCESTRY_RELATION,
                candidate.locator,
                "independent evidence indicates a lineage relation to the advertised revision",
                True,
            ))
        if candidate.content_matches:
            evidence.append(SourceEvidence(
                EvidenceKind.CONTENT_MATCH,
                candidate.locator,
                "candidate content matches the supplied identity evidence",
                True,
            ))

    provenance_candidates = [
        c for c in candidates
        if not c.contradictory_identity
        and (c.declared_lineage or c.lineage_to_advertised)
    ]
    if provenance_candidates:
        selected = provenance_candidates[0]
        return SourceIdentityResolution(
            advertised_revision=revision,
            status=LineageStatus.PROVENANCE_SUPPORTED,
            selected_locator=selected.locator,
            exact_identity_verified=False,
            evidence=tuple(evidence),
            reason=(
                "source lineage is supported by provenance evidence, but the "
                "advertised Git identity is not independently verified"
            ),
        )

    contradictions = [c for c in candidates if c.contradictory_identity]
    if contradictions and candidates and all(c.contradictory_identity for c in candidates):
        return SourceIdentityResolution(
            advertised_revision=revision,
            status=LineageStatus.MISMATCH,
            selected_locator=None,
            exact_identity_verified=False,
            evidence=tuple(evidence),
            reason="all discovered source candidates contradict the advertised identity",
        )

    return SourceIdentityResolution(
        advertised_revision=revision,
        status=LineageStatus.UNRESOLVED,
        selected_locator=None,
        exact_identity_verified=False,
        evidence=tuple(evidence),
        reason="insufficient evidence to resolve the authoritative source identity",
    )


__all__ = [
    "EvidenceKind",
    "LineageStatus",
    "SourceCandidate",
    "SourceEvidence",
    "SourceIdentityResolution",
    "resolve_source_identity",
]
