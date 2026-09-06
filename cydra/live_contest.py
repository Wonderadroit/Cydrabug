"""Live Immunefi contest acquisition orchestration.

This module composes existing passive intake primitives. It does not clone,
test, build, or grant authorization to any target. Its output is a durable
program-intake record suitable for the later target/source/build gates.
"""
from __future__ import annotations

from dataclasses import dataclass
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


def _extract_revision_assertion(content: str) -> str | None:
    """Extract a 40-hex Git revision asserted by acquired program material.

    This is evidence extraction only. A matching Git object must be verified
    independently by the source-identity layer.
    """
    patterns = (
        r"(?i)(?:audited|audit(?:ed)?\s+revision|commit|revision)[^0-9a-f]{0,80}"
        r"([0-9a-f]{40})",
        r"(?<![0-9a-f])([0-9a-f]{40})(?![0-9a-f])",
    )

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1).lower()

    return None


@dataclass(frozen=True)
class AcquisitionIdentityEvidence:
    """Source-identity facts observed during passive program acquisition.

    These are observations only. They do not establish cryptographic source
    identity, build identity, or authorization to test a discovered resource.
    """

    repository_locator: str | None = None
    advertised_revision: str | None = None
    declared_lineage_revision: str | None = None
    acquired_revision: str | None = None
    independent_verification: bool = False
    status: str = "UNRESOLVED"
    reason: str = (
        "source identity requires independent repository/build verification"
    )


@dataclass(frozen=True)
class LiveContestAcquisition:
    locator: str
    contract: ProgramContract
    acquired: tuple[AcquiredResource, ...]
    discovered: tuple[ResourceDiscovery, ...]
    graph: tuple[ProgramResource, ...]
    identity_evidence: AcquisitionIdentityEvidence | None = None

    @property
    def ready_for_active_testing(self) -> bool:
        if not self.contract.ready_for_active_testing:
            return False

        for resource in self.graph:
            if resource.kind is ResourceKind.REPOSITORY:
                if resource.scope is not ScopeStatus.IN_SCOPE:
                    return False
                if resource.state is not AcquisitionState.ACQUIRED:
                    return False

            if resource.required:
                if resource.state is not AcquisitionState.ACQUIRED:
                    return False

        return True

    def to_dict(self) -> dict[str, object]:
        return {
            "locator": self.locator,
            "program_contract": json.loads(self.contract.to_json()),
            "acquired": [
                {
                    "locator": item.locator,
                    "content_sha256": item.content_sha256,
                    "acquisition_adapter": item.acquisition_adapter,
                    "version": item.version,
                }
                for item in self.acquired
            ],
            "discovered": [
                {
                    "parent_resource_id": item.parent_resource_id,
                    "locator": item.locator,
                    "kind": item.kind.value,
                    "authority": item.authority.value,
                    "required": item.required,
                    "reason": item.reason,
                }
                for item in self.discovered
            ],
            "identity_evidence": (
                {
                    "repository_locator": self.identity_evidence.repository_locator,
                    "advertised_revision": self.identity_evidence.advertised_revision,
                    "declared_lineage_revision": (
                        self.identity_evidence.declared_lineage_revision
                    ),
                    "acquired_revision": self.identity_evidence.acquired_revision,
                    "independent_verification": (
                        self.identity_evidence.independent_verification
                    ),
                    "status": self.identity_evidence.status,
                    "reason": self.identity_evidence.reason,
                }
                if self.identity_evidence is not None
                else None
            ),
            "graph": [
                {
                    "resource_id": item.resource_id,
                    "kind": item.kind.value,
                    "locator": item.locator,
                    "authority": item.authority.value,
                    "state": item.state.value,
                    "scope": item.scope.value,
                    "content_sha256": item.content_sha256,
                    "version": item.version,
                    "parent_resource_id": item.parent_resource_id,
                    "required": item.required,
                    "reason": item.reason,
                }
                for item in self.graph
            ],
            "ready_for_active_testing": self.ready_for_active_testing,
        }


def acquire_live_contest(
    locator: str,
    *,
    fetcher: PublicHttpFetcher | None = None,
    max_depth: int = 2,
    receipt_path: str | Path | None = None,
) -> LiveContestAcquisition:
    """Acquire a bounded Immunefi program and its contextual resource graph."""
    parsed = urlparse(locator)
    if parsed.scheme != "https" or parsed.hostname != "immunefi.com":
        raise ValueError("live contest locator must be an HTTPS Immunefi URL")

    http = fetcher or PublicHttpFetcher()
    adapter = ImmunefiAcquisitionAdapter(http)
    pages = adapter.acquire_program_pages(locator)
    contract = adapter.acquire_contract(locator)

    acquired_by_id = {
        resource.resource_id: page
        for resource, page in zip(contract.resources, pages)
    }
    discovered: list[ResourceDiscovery] = []
    for resource in contract.resources:
        page = acquired_by_id.get(resource.resource_id)
        if page is None:
            continue
        discovered.extend(
            bounded_reference_plan(
                parent=resource,
                acquired=page,
                max_depth=max_depth,
            )
        )

    graph = expand_resource_dependency_graph(
        roots=contract.resources,
        acquired=acquired_by_id,
        fetcher=None,
        max_depth=max_depth,
    )
    advertised_revision = None
    for page in pages:
        advertised_revision = _extract_revision_assertion(page.content)
        if advertised_revision is not None:
            break

    # Do not infer source identity from discovery order or from the generic
    # ResourceKind.REPOSITORY classification. At this phase, a repository can
    # be a target, dependency, documentation project, audit material, or a PR
    # referenced by the authoritative pages. None of those roles is established
    # merely by being discovered first. The target/source-identity phase must
    # classify the repository from authoritative scope/provenance evidence and
    # independently verify the resulting revision/build identity.
    identity_evidence = AcquisitionIdentityEvidence(
        repository_locator=None,
        advertised_revision=advertised_revision,
        reason=(
            "no discovered repository is promoted to source identity during "
            "passive intake; target/resource classification and independent "
            "repository/build verification are required"
        ),
    )

    result = LiveContestAcquisition(
        locator=locator,
        contract=contract,
        acquired=pages,
        discovered=tuple(discovered),
        graph=tuple(graph),
        identity_evidence=identity_evidence,
    )
    if receipt_path is not None:
        path = Path(receipt_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return result


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Passively acquire a live Immunefi contest contract and resource graph."
    )
    parser.add_argument(
        "locator",
        help="canonical Immunefi information/scope/resources URL",
    )
    parser.add_argument("--receipt", default="evidence/live-contest.json")
    parser.add_argument("--max-depth", type=int, default=2)
    args = parser.parse_args(argv)

    try:
        result = acquire_live_contest(
            args.locator,
            max_depth=args.max_depth,
            receipt_path=args.receipt,
        )
    except Exception as exc:
        print(f"LIVE CONTEST ACQUISITION: ERROR: {exc}")
        return 2

    print("LIVE CONTEST ACQUISITION: COMPLETE")
    print(f"program: {result.contract.display_name}")
    print(f"contract fingerprint: {result.contract.fingerprint}")
    print(f"acquired pages: {len(result.acquired)}")
    print(f"discovered resources: {len(result.discovered)}")
    print(f"graph resources: {len(result.graph)}")
    print(f"active testing ready: {result.ready_for_active_testing}")
    print(f"receipt: {Path(args.receipt).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["LiveContestAcquisition", "acquire_live_contest"]
