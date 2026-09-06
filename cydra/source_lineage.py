"""Project-agnostic source identity and lineage reasoning."""
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
    kind: EvidenceKind
    source: str
    detail: str
    supports: bool

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.detail.strip():
            raise ValueError("source and detail must not be empty")


@dataclass(frozen=True)
class SourceCandidate:
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
    """Resolve authoritative source identity from independently supplied evidence."""
    revision = advertised_revision.strip().lower()
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("advertised_revision must be a full 40-character Git SHA")

    candidates = tuple(candidates)
    evidence: list[SourceEvidence] = []
    contradictory_candidates: list[SourceCandidate] = []

    for candidate in candidates:
        if candidate.contradictory_identity:
            evidence.append(SourceEvidence(
                EvidenceKind.IDENTITY_CONTRADICTION,
                candidate.locator,
                "candidate contains evidence contradicting the advertised source identity",
                False,
            ))
            contradictory_candidates.append(candidate)
            continue

        exact_object = candidate.advertised_revision_available
        observed_revision_matches = (
            candidate.observed_revision is not None
            and candidate.observed_revision.strip().lower() == revision
        )
        exact_head = candidate.observed_head_matches and observed_revision_matches

        # A positive HEAD-match claim paired with a different observed revision is
        # itself contradictory evidence. Do not let the positive flag conceal the
        # stronger observed identity mismatch.
        if candidate.observed_head_matches and not observed_revision_matches:
            evidence.append(SourceEvidence(
                EvidenceKind.IDENTITY_CONTRADICTION,
                candidate.locator,
                "candidate claims an exact HEAD match but its observed revision differs from the advertised revision",
                False,
            ))
            contradictory_candidates.append(candidate)
            continue

        if exact_object:
            evidence.append(SourceEvidence(
                EvidenceKind.EXACT_GIT_OBJECT,
                candidate.locator,
                f"advertised Git object {revision} is independently available",
                True,
            ))
        else:
            evidence.append(SourceEvidence(
                EvidenceKind.OBJECT_ABSENT,
                candidate.locator,
                f"advertised Git object {revision} is not independently available",
                False,
            ))

        if candidate.observed_head_matches:
            evidence.append(SourceEvidence(
                EvidenceKind.EXACT_HEAD_MATCH,
                candidate.locator,
                "candidate reports an exact HEAD match; observed revision equality is checked independently",
                exact_head,
            ))

        if exact_object and exact_head:
            return SourceIdentityResolution(
                revision, LineageStatus.VERIFIED, candidate.locator, True,
                tuple(evidence), "exact advertised Git identity independently verified",
            )

        if candidate.declared_lineage:
            evidence.append(SourceEvidence(
                EvidenceKind.DECLARED_LINEAGE, candidate.locator,
                "candidate explicitly declares lineage to the advertised revision", True,
            ))
        if candidate.lineage_to_advertised:
            evidence.append(SourceEvidence(
                EvidenceKind.ANCESTRY_RELATION, candidate.locator,
                "independent evidence indicates lineage to the advertised revision", True,
            ))
        if candidate.content_matches:
            evidence.append(SourceEvidence(
                EvidenceKind.CONTENT_MATCH, candidate.locator,
                "candidate content matches supplied identity evidence", True,
            ))

    provenance = [
        c for c in candidates
        if not c.contradictory_identity and (c.declared_lineage or c.lineage_to_advertised)
    ]
    if provenance:
        return SourceIdentityResolution(
            revision, LineageStatus.PROVENANCE_SUPPORTED, provenance[0].locator, False,
            tuple(evidence),
            "source lineage is supported, but exact advertised Git identity is not independently verified",
        )

    if candidates and all(c.contradictory_identity for c in candidates):
        return SourceIdentityResolution(
            revision, LineageStatus.MISMATCH, None, False, tuple(evidence),
            "all discovered source candidates contradict the advertised identity",
        )

    if contradictory_candidates and len(contradictory_candidates) == len(candidates):
        return SourceIdentityResolution(
            revision, LineageStatus.MISMATCH, None, False, tuple(evidence),
            "all discovered source candidates contradict the advertised identity",
        )

    return SourceIdentityResolution(
        revision, LineageStatus.UNRESOLVED, None, False, tuple(evidence),
        "insufficient evidence to resolve the authoritative source identity",
    )


__all__ = [
    "EvidenceKind", "LineageStatus", "SourceCandidate", "SourceEvidence",
    "SourceIdentityResolution", "resolve_source_identity",
]
