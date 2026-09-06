"""Live Immunefi contest acquisition orchestration."""
from __future__ import annotations

from dataclasses import dataclass, replace
import html
import json
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse
import re

from .immunefi_live import PublicHttpFetcher
from .program_intake import (
    AcquiredResource,
    AcquisitionState,
    ImmunefiAcquisitionAdapter,
    ProgramContract,
    ProgramResource,
    ResourceDiscovery,
    ResourceKind,
    ScopeStatus,
    bounded_reference_plan,
    expand_resource_dependency_graph,
)
from .source_identity import SourceIdentityReceipt
from .source_lineage import (
    LineageStatus,
    SourceCandidate,
    SourceIdentityResolution,
    resolve_source_identity,
)


def _extract_revision_assertion(content: str) -> str | None:
    """Extract only a revision explicitly labelled as the audited revision."""
    normalized = html.unescape(re.sub(r"<[^>]*>", " ", content))
    patterns = (
        r"(?is)audited\s+revision\s*(?:[—–:-]\s*)?(?:commit\s+hash\s*)?(?:[:—–-]\s*)?`?\s*([0-9a-f]{40})(?![0-9a-f])",
        r"(?is)audited\s+revision\s*(?:[—–:-]\s*)?commit\s+hash\s*[:—–-]\s*`?\s*([0-9a-f]{40})(?![0-9a-f])",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return match.group(1).lower()
    return None


@dataclass(frozen=True)
class AcquisitionIdentityEvidence:
    """Source-identity facts observed during passive program acquisition."""

    repository_locator: str | None = None
    advertised_revision: str | None = None
    declared_lineage_revision: str | None = None
    acquired_revision: str | None = None
    independent_verification: bool = False
    status: str = "UNRESOLVED"
    reason: str = "source identity requires independent repository/build verification"


@dataclass(frozen=True)
class LiveContestAcquisition:
    locator: str
    contract: ProgramContract
    acquired: tuple[AcquiredResource, ...]
    discovered: tuple[ResourceDiscovery, ...]
    graph: tuple[ProgramResource, ...]
    identity_evidence: AcquisitionIdentityEvidence | None = None
    source_resolution: SourceIdentityResolution | None = None

    @property
    def ready_for_active_testing(self) -> bool:
        if not self.contract.ready_for_active_testing:
            return False
        if self.source_resolution is not None and not self.source_resolution.ready_for_analysis:
            return False
        for resource in self.graph:
            if resource.kind is ResourceKind.REPOSITORY:
                if resource.scope is not ScopeStatus.IN_SCOPE:
                    return False
                if resource.state is not AcquisitionState.ACQUIRED:
                    return False
            if resource.required and resource.state is not AcquisitionState.ACQUIRED:
                return False
        return True

    def resolve_source_candidates(
        self,
        candidates: tuple[SourceCandidate, ...] | list[SourceCandidate],
    ) -> "LiveContestAcquisition":
        """Apply generic lineage reasoning to independently collected evidence."""
        advertised = self.identity_evidence.advertised_revision if self.identity_evidence else None
        if advertised is None:
            raise ValueError("no advertised audited revision is available")
        resolution = resolve_source_identity(advertised, candidates)
        selected = resolution.selected_locator
        evidence = self.identity_evidence or AcquisitionIdentityEvidence()
        selected_candidate = next((c for c in candidates if c.locator == selected), None)
        updated_evidence = replace(
            evidence,
            repository_locator=selected,
            advertised_revision=advertised,
            acquired_revision=(selected_candidate.observed_revision if selected_candidate else None),
            independent_verification=resolution.exact_identity_verified,
            status=resolution.status.value,
            reason=resolution.reason,
        )
        return replace(self, identity_evidence=updated_evidence, source_resolution=resolution)

    def resolve_source_receipts(
        self,
        receipts: Sequence[SourceIdentityReceipt],
        *,
        provenance_candidates: Sequence[SourceCandidate] = (),
    ) -> "LiveContestAcquisition":
        """Bridge exact acquisition receipts into the generic lineage resolver.

        Failed acquisition is retained as evidence rather than discarded. This
        lets CYDRA distinguish an unavailable advertised object from a wrong
        object and combine that observation with independently established fork
        or ancestry provenance.
        """
        candidates = tuple(receipt.to_candidate() for receipt in receipts)
        candidates += tuple(provenance_candidates)
        return self.resolve_source_candidates(candidates)

    def to_dict(self) -> dict[str, object]:
        return {
            "locator": self.locator,
            "program_contract": json.loads(self.contract.to_json()),
            "acquired": [
                {"locator": item.locator, "content_sha256": item.content_sha256,
                 "acquisition_adapter": item.acquisition_adapter, "version": item.version}
                for item in self.acquired
            ],
            "discovered": [
                {"parent_resource_id": item.parent_resource_id, "locator": item.locator,
                 "kind": item.kind.value, "authority": item.authority.value,
                 "required": item.required, "reason": item.reason}
                for item in self.discovered
            ],
            "identity_evidence": (
                {"repository_locator": self.identity_evidence.repository_locator,
                 "advertised_revision": self.identity_evidence.advertised_revision,
                 "declared_lineage_revision": self.identity_evidence.declared_lineage_revision,
                 "acquired_revision": self.identity_evidence.acquired_revision,
                 "independent_verification": self.identity_evidence.independent_verification,
                 "status": self.identity_evidence.status, "reason": self.identity_evidence.reason}
                if self.identity_evidence is not None else None
            ),
            "source_resolution": (
                {"advertised_revision": self.source_resolution.advertised_revision,
                 "status": self.source_resolution.status.value,
                 "selected_locator": self.source_resolution.selected_locator,
                 "exact_identity_verified": self.source_resolution.exact_identity_verified,
                 "reason": self.source_resolution.reason,
                 "evidence": [{"kind": item.kind.value, "source": item.source,
                               "detail": item.detail, "supports": item.supports}
                              for item in self.source_resolution.evidence]}
                if self.source_resolution is not None else None
            ),
            "graph": [
                {"resource_id": item.resource_id, "kind": item.kind.value, "locator": item.locator,
                 "authority": item.authority.value, "state": item.state.value, "scope": item.scope.value,
                 "content_sha256": item.content_sha256, "version": item.version,
                 "parent_resource_id": item.parent_resource_id, "required": item.required,
                 "reason": item.reason}
                for item in self.graph
            ],
            "ready_for_active_testing": self.ready_for_active_testing,
        }


def acquire_live_contest(locator: str, *, fetcher: PublicHttpFetcher | None = None,
                         max_depth: int = 2, receipt_path: str | Path | None = None) -> LiveContestAcquisition:
    """Acquire a bounded Immunefi program and its contextual resource graph."""
    parsed = urlparse(locator)
    if parsed.scheme != "https" or parsed.hostname != "immunefi.com":
        raise ValueError("live contest locator must be an HTTPS Immunefi URL")

    http = fetcher or PublicHttpFetcher()
    adapter = ImmunefiAcquisitionAdapter(http)
    pages = adapter.acquire_program_pages(locator)
    contract = adapter.acquire_contract(locator)
    acquired_by_id = {resource.resource_id: page for resource, page in zip(contract.resources, pages)}
    discovered: list[ResourceDiscovery] = []
    for resource in contract.resources:
        page = acquired_by_id.get(resource.resource_id)
        if page is not None:
            discovered.extend(bounded_reference_plan(parent=resource, acquired=page, max_depth=max_depth))
    graph = expand_resource_dependency_graph(roots=contract.resources, acquired=acquired_by_id,
                                             fetcher=None, max_depth=max_depth)

    advertised_revision = next((
        revision for page in pages
        for revision in (_extract_revision_assertion(page.content),)
        if revision is not None
    ), None)
    repository_locators = tuple(item.locator for item in discovered if item.kind is ResourceKind.REPOSITORY)
    candidates = tuple(SourceCandidate(locator=item) for item in repository_locators)
    source_resolution = (resolve_source_identity(advertised_revision, candidates)
                         if advertised_revision is not None else None)
    selected = source_resolution.selected_locator if source_resolution else None
    identity_evidence = AcquisitionIdentityEvidence(
        repository_locator=selected,
        advertised_revision=advertised_revision,
        independent_verification=(source_resolution.exact_identity_verified if source_resolution else False),
        status=(source_resolution.status.value if source_resolution else "UNRESOLVED"),
        reason=(source_resolution.reason if source_resolution else
                "no authoritative audited revision was semantically extracted from acquired program material"),
    )
    result = LiveContestAcquisition(locator=locator, contract=contract, acquired=pages,
                                    discovered=tuple(discovered), graph=tuple(graph),
                                    identity_evidence=identity_evidence, source_resolution=source_resolution)
    if receipt_path is not None:
        path = Path(receipt_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Passively acquire a live Immunefi contest contract and resource graph.")
    parser.add_argument("locator", help="canonical Immunefi information/scope/resources URL")
    parser.add_argument("--receipt", default="evidence/live-contest.json")
    parser.add_argument("--max-depth", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        result = acquire_live_contest(args.locator, max_depth=args.max_depth, receipt_path=args.receipt)
    except Exception as exc:
        print(f"LIVE CONTEST ACQUISITION: ERROR: {exc}")
        return 2
    print("LIVE CONTEST ACQUISITION: COMPLETE")
    print(f"program: {result.contract.display_name}")
    print(f"contract fingerprint: {result.contract.fingerprint}")
    print(f"acquired pages: {len(result.acquired)}")
    print(f"discovered resources: {len(result.discovered)}")
    print(f"graph resources: {len(result.graph)}")
    print(f"source identity: {result.source_resolution.status.value if result.source_resolution else 'UNRESOLVED'}")
    print(f"active testing ready: {result.ready_for_active_testing}")
    print(f"receipt: {Path(args.receipt).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["AcquisitionIdentityEvidence", "LiveContestAcquisition", "acquire_live_contest"]
