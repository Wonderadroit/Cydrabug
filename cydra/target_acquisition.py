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
from .program_intake import ProgramResource, ResourceKind, ScopeStatus, canonical_resource_id


_PATH_ROOTS = (
    "apps", "packages", "workers", "services", "src", "lib", "server",
    "client", "contracts", "crates", "cmd", "internal", "modules", "programs",
)
_GENERIC_ASSET_TOKENS = {"app", "apps", "file", "files", "the", "target", "name", "scope"}


@dataclass(frozen=True)
class ScopeAssetEvidence:
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
        return bool(self.in_scope_candidates) and not self.unresolved_assets


class _TableParser(HTMLParser):
    """Dependency-free parser that preserves table and row/column structure."""

    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] = []
        self._row: list[str] = []
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self.in_table = True
            self._table = []
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self._row = []
        elif tag in {"td", "th"} and self.in_row:
            self.in_cell = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self.in_cell:
            value = re.sub(r"\s+", " ", " ".join(self._buffer)).strip()
            self._row.append(value)
            self.in_cell = False
            self._buffer = []
        elif tag == "tr" and self.in_row:
            if self._row:
                self._table.append(self._row)
            self.in_row = False
            self._row = []
        elif tag == "table" and self.in_table:
            if self._table:
                self.tables.append(self._table)
            self.in_table = False
            self._table = []


def _visible_text(content: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def _asset_tokens(value: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _label_matches_asset(label: str, asset_name: str) -> bool:
    """Match explicit labels without generic words creating cross-bindings."""
    label_tokens = _asset_tokens(label) - _GENERIC_ASSET_TOKENS
    asset_tokens = _asset_tokens(asset_name) - _GENERIC_ASSET_TOKENS
    if label_tokens & asset_tokens:
        return True
    aliases = {"explorer": {"portal"}, "worker": {"workers", "worker"}}
    return any(token in aliases.get(asset_token, set()) for asset_token in asset_tokens for token in label_tokens)


def _extract_asset_names(content: str) -> tuple[str, ...]:
    """Extract asset names only from the authoritative asset table structure."""
    parser = _TableParser()
    try:
        parser.feed(content)
    except Exception:
        parser.tables = []

    names: list[str] = []
    for table in parser.tables:
        header_index = None
        name_index = None
        for row_index, row in enumerate(table):
            normalized = [cell.lower() for cell in row]
            if "name" in normalized and "target" in normalized:
                header_index = row_index
                name_index = normalized.index("name")
                break
        if header_index is None or name_index is None:
            continue

        for candidate_row in table[header_index + 1 :]:
            if len(candidate_row) <= name_index:
                continue
            candidate = candidate_row[name_index].strip()
            if not candidate or candidate.lower() in {"name", "target", "added on"}:
                continue
            if re.fullmatch(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", candidate):
                continue
            if candidate not in names:
                names.append(candidate)
        if names:
            break

    if not names:
        text = _visible_text(content)
        marker = re.search(r"Assets in Scope(.*?)(?:Impacts in Scope|Public Disclosure|Out of scope)", text, re.I)
        section = marker.group(1) if marker else ""
        pattern = re.compile(r"(?:Target\s+)?Name\s+(.+?)\s+Added on\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}", re.I)
        names.extend(dict.fromkeys(match.group(1).strip() for match in pattern.finditer(section)))

    return tuple(names)


def _asset_matches_hint(asset: ScopeAssetEvidence | str, hint: str) -> bool:
    """Conservatively associate an asset with a path when evidence overlaps."""
    asset_name = asset.asset_name if isinstance(asset, ScopeAssetEvidence) else asset
    normalized_name = _asset_tokens(asset_name) - _GENERIC_ASSET_TOKENS
    path_tokens = _asset_tokens(hint)
    aliases = {"explorer": {"portal"}, "worker": {"workers", "worker"}}
    for token in normalized_name:
        if token in path_tokens:
            if token in {"manager", "transaction", "smart", "account", "explorer", "worker", "workers"}:
                if token == "manager" and hint.startswith("packages/"):
                    continue
                if token == "transaction" and not hint.startswith("packages/"):
                    continue
                if token in {"worker", "workers"} and not hint.startswith("workers/"):
                    continue
            return True
        if path_tokens & aliases.get(token, set()):
            return True
    return False


def _asset_path_associations(content: str, assets: tuple[str, ...], hints: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """Recover explicit asset-to-path associations from scope evidence."""
    text = _visible_text(content)
    associations: dict[str, set[str]] = {asset: set() for asset in assets}

    path_pattern = r"(?P<path>(?:" + "|".join(re.escape(root) for root in _PATH_ROOTS) + r")/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)\s*\((?P<label>[^)]+)\)"
    for match in re.finditer(path_pattern, text):
        path = match.group("path").strip("./").rstrip("/")
        label = match.group("label").strip().lower()
        for asset in assets:
            if _label_matches_asset(label, asset):
                associations[asset].add(path)

    for asset in assets:
        if associations[asset]:
            continue
        for hint in hints:
            if _asset_matches_hint(asset, hint):
                associations[asset].add(hint)

    return {asset: tuple(sorted(values)) for asset, values in associations.items()}


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

    asset_names = _extract_asset_names(content)
    sorted_hints = tuple(sorted(hints))
    associations = _asset_path_associations(content, asset_names, sorted_hints)
    assets = tuple(
        ScopeAssetEvidence(
            asset_name=name,
            source_resource_id=scope_resource.resource_id,
            path_hints=associations.get(name, ()),
            basis="authoritative Immunefi scope asset declaration",
        )
        for name in asset_names
    )
    return ScopeEvidence(
        source_resource_id=scope_resource.resource_id,
        path_hints=sorted_hints,
        basis="authoritative Immunefi scope material; path hints are evidence, not identity",
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


def classify_repository(resource: ProgramResource, evidence: ScopeEvidence) -> TargetResourceCandidate:
    if resource.kind is not ResourceKind.REPOSITORY:
        raise ValueError("target classification requires a repository resource")

    repository_path = _repository_path(resource.locator)
    matched = tuple(hint for hint in evidence.path_hints if repository_path == hint.lower() or repository_path.startswith(hint.lower() + "/"))
    matched_assets = tuple(asset.asset_name for asset in evidence.assets if any(hint in asset.path_hints for hint in matched))

    if matched:
        return TargetResourceCandidate(resource.resource_id, resource.locator, ScopeStatus.IN_SCOPE, "TARGET", matched, evidence, "repository path is covered by authoritative scope path evidence", matched_assets)

    return TargetResourceCandidate(resource.resource_id, resource.locator, ScopeStatus.UNKNOWN, "CONTEXT_OR_UNRESOLVED", (), evidence, "no authoritative scope path matched; repository remains unresolved and cannot be promoted by discovery order", ())


def _candidate_lineage(locator: str, matched_hint: str) -> str | None:
    parsed = urlparse(locator)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        return None
    marker = "/" + matched_hint.strip("/")
    path = parsed.path
    index = path.lower().find(marker.lower())
    if index < 0:
        return None
    prefix = path[:index].rstrip("/")
    if not prefix:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{prefix}"


def _infer_missing_asset_candidates(candidates: tuple[TargetResourceCandidate, ...], evidence: ScopeEvidence, unresolved_assets: tuple[ScopeAssetEvidence, ...]) -> tuple[TargetResourceCandidate, ...]:
    inferred: list[TargetResourceCandidate] = []
    for asset in unresolved_assets:
        asset_hints = asset.path_hints
        lineage_map: dict[str, set[str]] = {}
        for candidate in candidates:
            if candidate.scope is not ScopeStatus.IN_SCOPE:
                continue
            for matched_hint in candidate.matched_hints:
                lineage = _candidate_lineage(candidate.locator, matched_hint)
                if lineage is not None:
                    lineage_map.setdefault(lineage, set()).add(matched_hint)
        if len(lineage_map) != 1 or not asset_hints:
            continue

        lineage, _ = next(iter(lineage_map.items()))
        template = next(candidate for candidate in candidates if any(_candidate_lineage(candidate.locator, hint) == lineage for hint in candidate.matched_hints))
        source_hint = next(hint for hint in template.matched_hints if _candidate_lineage(template.locator, hint) == lineage)
        target_hint = asset_hints[0]
        marker = "/" + source_hint.strip("/")
        replacement = "/" + target_hint.strip("/")
        inferred_locator = template.locator.replace(marker, replacement, 1)
        inferred.append(TargetResourceCandidate(
            resource_id=canonical_resource_id(ResourceKind.REPOSITORY, inferred_locator),
            locator=inferred_locator,
            scope=ScopeStatus.IN_SCOPE,
            acquisition_role="TARGET_INFERRED_PATH",
            matched_hints=(target_hint,),
            evidence=evidence,
            reason=("authoritative asset path was not linked directly; target path was derived from a unique already-observed repository lineage and must be independently verified in the source-identity phase"),
            asset_names=(asset.asset_name,),
        ))
    return tuple(inferred)


def plan_target_acquisition(result: LiveContestAcquisition) -> TargetAcquisitionPlan:
    scope_resources = [r for r in result.graph if r.kind is ResourceKind.SCOPE]
    if not scope_resources:
        raise ValueError("target acquisition requires an acquired authoritative SCOPE resource")

    scope_resource = scope_resources[0]
    acquired = next((item for item in result.acquired if item.locator == scope_resource.locator), None)
    if acquired is None:
        raise ValueError("authoritative SCOPE resource has no acquired content")

    evidence = extract_scope_evidence(scope_resource, acquired.content)
    candidates = tuple(classify_repository(resource, evidence) for resource in result.graph if resource.kind is ResourceKind.REPOSITORY)
    matched_assets = {name for candidate in candidates for name in candidate.asset_names}
    unresolved_assets = tuple(asset for asset in evidence.assets if asset.asset_name not in matched_assets)

    inferred = _infer_missing_asset_candidates(candidates, evidence, unresolved_assets)
    candidates = candidates + inferred
    matched_assets = {name for candidate in candidates for name in candidate.asset_names}
    unresolved_assets = tuple(asset for asset in evidence.assets if asset.asset_name not in matched_assets)
    unresolved = tuple(c.resource_id for c in candidates if c.scope is ScopeStatus.UNKNOWN)
    return TargetAcquisitionPlan(result.contract.program_id, candidates, unresolved, unresolved_assets)


__all__ = ["ScopeAssetEvidence", "ScopeEvidence", "TargetAcquisitionPlan", "TargetResourceCandidate", "classify_repository", "extract_scope_evidence", "plan_target_acquisition"]
