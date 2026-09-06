"""Phase 1 target/resource classification for Immunefi acquisitions.

This module turns authoritative scope evidence into target acquisition
candidates. Discovery order, repository kind, and public availability never
establish target identity by themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse

from .live_contest import LiveContestAcquisition
from .program_intake import ProgramResource, ResourceKind, ScopeStatus


_PATH_ROOTS = (
    "apps", "packages", "workers", "services", "src", "lib", "server",
    "client", "contracts", "crates", "cmd", "internal", "modules", "programs",
)


@dataclass(frozen=True)
class ScopeEvidence:
    source_resource_id: str
    path_hints: tuple[str, ...]
    basis: str


@dataclass(frozen=True)
class TargetResourceCandidate:
    resource_id: str
    locator: str
    scope: ScopeStatus
    acquisition_role: str
    matched_hints: tuple[str, ...]
    evidence: ScopeEvidence
    reason: str


@dataclass(frozen=True)
class TargetAcquisitionPlan:
    program_id: str
    candidates: tuple[TargetResourceCandidate, ...]
    unresolved_resources: tuple[str, ...]

    @property
    def in_scope_candidates(self) -> tuple[TargetResourceCandidate, ...]:
        return tuple(c for c in self.candidates if c.scope is ScopeStatus.IN_SCOPE)

    @property
    def ready_for_source_identity(self) -> bool:
        # Contextual/unknown repositories are not authority blockers. They are
        # deliberately preserved as unresolved context while at least one
        # repository has been positively classified from authoritative scope.
        return bool(self.in_scope_candidates)


def _visible_text(content: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def extract_scope_evidence(scope_resource: ProgramResource, content: str) -> ScopeEvidence:
    """Extract conservative repository path hints from authoritative scope text."""
    if scope_resource.kind is not ResourceKind.SCOPE:
        raise ValueError("scope evidence must come from a SCOPE resource")

    text = _visible_text(content)
    hints: set[str] = set()
    root_pattern = "|".join(re.escape(root) for root in _PATH_ROOTS)
    pattern = rf"(?<![\w.-])((?:{root_pattern})/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+)"
    for match in re.finditer(pattern, text):
        value = match.group(1).strip("./")
        if value:
            hints.add(value.rstrip("/"))

    return ScopeEvidence(
        source_resource_id=scope_resource.resource_id,
        path_hints=tuple(sorted(hints)),
        basis="authoritative Immunefi scope material; path hints extracted conservatively from published asset descriptions",
    )


def _repository_path(locator: str) -> str:
    parsed = urlparse(locator)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return ""
    # Pull requests/issues/discussions are contextual project material, never
    # source-target paths.
    if len(parts) >= 4 and parts[2].lower() in {"pull", "issues", "discussions"}:
        return ""
    tail = parts[2:]
    if tail and tail[0].lower() in {"tree", "blob"}:
        tail = tail[2:]
    return "/".join(tail).strip("/").lower()


def classify_repository(resource: ProgramResource, evidence: ScopeEvidence) -> TargetResourceCandidate:
    if resource.kind is not ResourceKind.REPOSITORY:
        raise ValueError("target classification requires a repository resource")

    repository_path = _repository_path(resource.locator)
    matched = tuple(
        hint for hint in evidence.path_hints
        if repository_path == hint.lower() or repository_path.startswith(hint.lower() + "/")
    )

    if matched:
        return TargetResourceCandidate(
            resource.resource_id,
            resource.locator,
            ScopeStatus.IN_SCOPE,
            "TARGET",
            matched,
            evidence,
            "repository path is covered by an explicit path hint extracted from authoritative scope evidence",
        )

    return TargetResourceCandidate(
        resource.resource_id,
        resource.locator,
        ScopeStatus.UNKNOWN,
        "CONTEXT_OR_UNRESOLVED",
        (),
        evidence,
        "no authoritative scope path matched; repository remains unresolved and cannot be promoted by discovery order",
    )


def plan_target_acquisition(result: LiveContestAcquisition) -> TargetAcquisitionPlan:
    scope_resources = [r for r in result.graph if r.kind is ResourceKind.SCOPE]
    if not scope_resources:
        raise ValueError("target acquisition requires an acquired authoritative SCOPE resource")

    scope_resource = scope_resources[0]
    acquired = next((item for item in result.acquired if item.locator == scope_resource.locator), None)
    if acquired is None:
        raise ValueError("authoritative SCOPE resource has no acquired content")

    evidence = extract_scope_evidence(scope_resource, acquired.content)
    candidates = tuple(
        classify_repository(resource, evidence)
        for resource in result.graph
        if resource.kind is ResourceKind.REPOSITORY
    )
    unresolved = tuple(c.resource_id for c in candidates if c.scope is ScopeStatus.UNKNOWN)
    return TargetAcquisitionPlan(result.contract.program_id, candidates, unresolved)


__all__ = [
    "ScopeEvidence",
    "TargetAcquisitionPlan",
    "TargetResourceCandidate",
    "classify_repository",
    "extract_scope_evidence",
    "plan_target_acquisition",
]
