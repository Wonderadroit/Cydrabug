"""Phase 1 target/resource classification for Immunefi acquisitions.

This module turns authoritative scope evidence into target acquisition
candidates. Discovery order, repository kind, and public availability never
establish target identity by themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import urlparse

from .live_contest import LiveContestAcquisition
from .program_intake import ProgramResource, ResourceKind, ScopeStatus


_PATH_ROOTS = (
    "apps", "packages", "workers", "services", "src", "lib", "server",
    "client", "contracts", "crates", "cmd", "internal", "modules", "programs",
)


@dataclass(frozen=True)
class ScopeAssetEvidence:
    """One asset identity declared by authoritative scope material."""

    asset_name: str
    source_resource_id: str
    path_hints: tuple[str, ...]
    basis: str


@dataclass(frozen=True)
class ScopeEvidence:
    source_resource_id: str
    path_hints: tuple[str, ...]
    basis: str
    assets: tuple[ScopeAssetEvidence, ...] = ()


@dataclass(frozen=True)
class TargetResourceCandidate:
    resource_id: str
    locator: str
    scope: ScopeStatus
    acquisition_role: str
    matched_hints: tuple[str, ...]
    evidence: ScopeEvidence
    reason: str
    asset_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetAcquisitionPlan:
    program_id: str
    candidates: tuple[TargetResourceCandidate, ...]
    unresolved_resources: tuple[str, ...]
    unresolved_assets: tuple[ScopeAssetEvidence, ...] = ()

    @property
    def in_scope_candidates(self) -> tuple[TargetResourceCandidate, ...]:
        return tuple(c for c in self.candidates if c.scope is ScopeStatus.IN_SCOPE)

    @property
    def ready_for_source_identity(self) -> bool:
        # Do not advance while an authoritative asset has no resolved target
        # candidate. Unknown contextual repositories are harmless context, but
        # missing target coverage is an acquisition evidence gap.
        return bool(self.in_scope_candidates) and not self.unresolved_assets


class _TableCellParser(HTMLParser):
    """Small dependency-free parser for authoritative HTML table cells."""

    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cells: list[str] = []
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"td", "th"}:
            self.in_cell = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self.in_cell:
            value = re.sub(r"\s+", " ", " ".join(self._buffer)).strip()
            self.cells.append(value)
            self.in_cell = False
            self._buffer = []


def _visible_text(content: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def _extract_asset_names(content: str) -> tuple[str, ...]:
    """Extract declared scope asset names without embedding program-specific names."""
    parser = _TableCellParser()
    try:
        parser.feed(content)
    except Exception:
        parser.cells = []

    names: list[str] = []
    # Immunefi scope tables are Target | Name | Added on. Once the Name
    # column is encountered, every third cell is the target name until the
    # next major scope table. This is structural evidence, not target naming.
    cells = parser.cells
    for index, cell in enumerate(cells):
        if cell.lower() == "name" and index > 0:
            for candidate in cells[index + 1 :]:
                if candidate.lower() in {"added on", "target", "name", "impacts in scope"}:
                    continue
                if re.fullmatch(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", candidate):
                    continue
                if candidate and candidate not in names:
                    names.append(candidate)
                if len(names) >= 1 and candidate.lower() == "target":
                    break
            if names:
                break

    # Fallback for fetched/sanitized content where HTML table cells are gone.
    if not names:
        text = _visible_text(content)
        marker = re.search(r"Assets in Scope(.*?)(?:Impacts in Scope|Public Disclosure|Out of scope)", text, re.I)
        if marker:
            section = marker.group(1)
            names.extend(
                dict.fromkeys(
                    m.group(1).strip()
                    for m in re.finditer(r"(?:Target\s+)?Name\s+(.+?)\s+(?:Added on\s+)?\d{1,2}\s+[A-Za-z]+\s+\d{4}", section, re.I)
                )
            )

    return tuple(names)


def extract_scope_evidence(scope_resource: ProgramResource, content: str) -> ScopeEvidence:
    """Extract authoritative asset identities and conservative path hints."""
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

    assets = tuple(
        ScopeAssetEvidence(
            asset_name=name,
            source_resource_id=scope_resource.resource_id,
            path_hints=tuple(sorted(hints)),
            basis="authoritative Immunefi scope asset declaration",
        )
        for name in _extract_asset_names(content)
    )
    return ScopeEvidence(
        source_resource_id=scope_resource.resource_id,
        path_hints=tuple(sorted(hints)),
        basis="authoritative Immunifi scope material; path hints are evidence, not identity",
        assets=assets,
    )


def _repository_path(locator: str) -> str:
    parsed = urlparse(locator)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return ""
    if len(parts) >= 4 and parts[2].lower() in {"pull", "issues", "discussions"}:
        return ""
    tail = parts[2:]
    if tail and tail[0].lower() in {"tree", "blob"}:
        tail = tail[2:]
    return "/".join(tail).strip("/").lower()


def _asset_matches_hint(asset: ScopeAssetEvidence, hint: str) -> bool:
    """Conservatively associate an asset with a path when the published name overlaps."""
    normalized_name = re.sub(r"[^a-z0-9]+", " ", asset.asset_name.lower()).split()
    path_tokens = set(re.sub(r"[^a-z0-9]+", " ", hint.lower()).split())
    aliases = {"explorer": {"portal"}, "worker": {"workers", "worker"}}
    for token in normalized_name:
        if token in path_tokens:
            return True
        if path_tokens & aliases.get(token, set()):
            return True
    return False


def classify_repository(resource: ProgramResource, evidence: ScopeEvidence) -> TargetResourceCandidate:
    if resource.kind is not ResourceKind.REPOSITORY:
        raise ValueError("target classification requires a repository resource")

    repository_path = _repository_path(resource.locator)
    matched = tuple(
        hint for hint in evidence.path_hints
        if repository_path == hint.lower() or repository_path.startswith(hint.lower() + "/")
    )
    matched_assets = tuple(
        asset.asset_name
        for asset in evidence.assets
        if any(_asset_matches_hint(asset, hint) for hint in matched)
    )

    if matched:
        return TargetResourceCandidate(
            resource.resource_id,
            resource.locator,
            ScopeStatus.IN_SCOPE,
            "TARGET",
            matched,
            evidence,
            "repository path is covered by authoritative scope path evidence",
            matched_assets,
        )

    return TargetResourceCandidate(
        resource.resource_id,
        resource.locator,
        ScopeStatus.UNKNOWN,
        "CONTEXT_OR_UNRESOLVED",
        (),
        evidence,
        "no authoritative scope path matched; repository remains unresolved and cannot be promoted by discovery order",
        (),
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
    matched_assets = {name for candidate in candidates for name in candidate.asset_names}
    unresolved_assets = tuple(asset for asset in evidence.assets if asset.asset_name not in matched_assets)
    unresolved = tuple(c.resource_id for c in candidates if c.scope is ScopeStatus.UNKNOWN)
    return TargetAcquisitionPlan(result.contract.program_id, candidates, unresolved, unresolved_assets)


__all__ = [
    "ScopeAssetEvidence",
    "ScopeEvidence",
    "TargetAcquisitionPlan",
    "TargetResourceCandidate",
    "classify_repository",
    "extract_scope_evidence",
    "plan_target_acquisition",
]
