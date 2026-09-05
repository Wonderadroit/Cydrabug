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

from .immunefi_live import PublicHttpFetcher
from .program_intake import (
    AcquiredResource,
    ImmunefiAcquisitionAdapter,
    ProgramContract,
    ProgramResource,
    ResourceDiscovery,
    bounded_reference_plan,
    expand_resource_dependency_graph,
)


@dataclass(frozen=True)
class LiveContestAcquisition:
    locator: str
    contract: ProgramContract
    acquired: tuple[AcquiredResource, ...]
    discovered: tuple[ResourceDiscovery, ...]
    graph: tuple[ProgramResource, ...]

    @property
    def ready_for_active_testing(self) -> bool:
        return self.contract.ready_for_active_testing and all(
            resource.state.value == "ACQUIRED" or not resource.required
            for resource in self.graph
        )

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
        discovered.extend(bounded_reference_plan(parent=resource, acquired=page, max_depth=max_depth))

    graph = expand_resource_dependency_graph(
        roots=contract.resources,
        acquired=acquired_by_id,
        fetcher=None,
        max_depth=max_depth,
    )
    result = LiveContestAcquisition(
        locator=locator,
        contract=contract,
        acquired=pages,
        discovered=tuple(discovered),
        graph=tuple(graph),
    )
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
