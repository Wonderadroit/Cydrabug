"""Narrow ENS experiment for measuring compiler-backed TypeScript-family source reconstruction."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import argparse
import json
from pathlib import Path

from .ens_target import scoped_assets
from .source_ingestion import project_source_observations
from .source_provider import SourceObservationKind
from .typescript_provider import TypeScriptCompilerProvider


@dataclass(frozen=True)
class ENSObservationExperimentResult:
    inventory_files: int
    supplied_source_files: int
    observation_count: int
    node_count: int
    edge_count: int
    observations_by_kind: dict[str, int]
    resolved_imports: int
    unresolved_imports: int
    resolved_exports: int
    unresolved_exports: int
    internal_relationships: int
    external_resolutions: int
    call_observations: int
    internally_resolved_call_observations: int
    internal_call_relationships: int
    call_resolution_matrix: dict[str, int]
    compiler_version: str

    def as_dict(self) -> dict[str, object]:
        return {
            "inventory_files": self.inventory_files,
            "supplied_source_files": self.supplied_source_files,
            "observation_count": self.observation_count,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "observations_by_kind": dict(sorted(self.observations_by_kind.items())),
            "resolved_imports": self.resolved_imports,
            "unresolved_imports": self.unresolved_imports,
            "resolved_exports": self.resolved_exports,
            "unresolved_exports": self.unresolved_exports,
            "internal_relationships": self.internal_relationships,
            "external_resolutions": self.external_resolutions,
            "call_observations": self.call_observations,
            "internally_resolved_call_observations": self.internally_resolved_call_observations,
            "internal_call_relationships": self.internal_call_relationships,
            "call_resolution_matrix": dict(sorted(self.call_resolution_matrix.items())),
            "compiler_version": self.compiler_version,
        }


def _scope_resolver(path: str) -> str:
    normalized = Path(path).as_posix()
    for root in scoped_assets():
        if normalized == root or normalized.startswith(root.rstrip("/") + "/"):
            return "IN_SCOPE"
    return "UNKNOWN"


def run_ens_source_observation_experiment(
    target_root: str | Path,
    inventory_path: str | Path,
) -> ENSObservationExperimentResult:
    """Run the compiler-backed observer over the frozen ENS source inventory.

    This measures source reconstruction only. It does not perform active target
    testing and does not establish audited-source identity.
    """
    root = Path(target_root).resolve()
    inventory = Path(inventory_path).resolve()
    paths = tuple(line.strip() for line in inventory.read_text().splitlines() if line.strip())
    sources: dict[str, str] = {}
    for relative in paths:
        source_path = root / relative
        if source_path.is_file() and source_path.suffix in {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}:
            sources[relative] = source_path.read_text(encoding="utf-8")

    provider = TypeScriptCompilerProvider(root, scope_resolver=_scope_resolver)
    observations = tuple(provider.observe(paths, sources))
    system = project_source_observations(observations)

    kinds = Counter(observation.kind.value for observation in observations)
    resolved_imports = sum(
        observation.kind is SourceObservationKind.IMPORT
        and observation.attributes.get("resolution_status") == "RESOLVED"
        for observation in observations
    )
    unresolved_imports = sum(
        observation.kind is SourceObservationKind.IMPORT
        and observation.attributes.get("resolution_status") == "UNRESOLVED"
        for observation in observations
    )
    resolved_exports = sum(
        observation.kind is SourceObservationKind.EXPORT
        and observation.attributes.get("resolution_status") == "RESOLVED"
        for observation in observations
    )
    unresolved_exports = sum(
        observation.kind is SourceObservationKind.EXPORT
        and observation.attributes.get("resolution_status") == "UNRESOLVED"
        for observation in observations
    )
    external_resolutions = sum(
        observation.attributes.get("resolution_status") == "RESOLVED_EXTERNAL"
        for observation in observations
    )
    internal_relationships = sum(len(observation.relationships) for observation in observations)
    call_observations = sum(
        observation.kind is SourceObservationKind.CALL for observation in observations
    )
    internally_resolved_call_observations = sum(
        observation.kind is SourceObservationKind.CALL
        and observation.attributes.get("callee_relationship_status") == "RESOLVED_INTERNAL"
        and observation.attributes.get("caller_relationship_status") == "RESOLVED_INTERNAL"
        for observation in observations
    )
    internal_call_relationships = sum(
        relationship.relation == "calls"
        for observation in observations
        for relationship in observation.relationships
    )

    call_resolution_matrix = Counter()
    for observation in observations:
        if observation.kind is not SourceObservationKind.CALL:
            continue
        caller = str(observation.attributes.get("caller_relationship_status", "UNKNOWN"))
        callee = str(observation.attributes.get("callee_relationship_status", "UNKNOWN"))
        call_resolution_matrix[f"caller={caller};callee={callee}"] += 1

    compiler_versions = {
        observation.tool_version
        for observation in observations
        if observation.tool_version is not None
    }
    compiler_version = next(iter(compiler_versions), "unknown") if len(compiler_versions) <= 1 else "MIXED"

    return ENSObservationExperimentResult(
        inventory_files=len(paths),
        supplied_source_files=len(sources),
        observation_count=len(observations),
        node_count=len(system.nodes),
        edge_count=len(system.edges),
        observations_by_kind=dict(kinds),
        resolved_imports=resolved_imports,
        unresolved_imports=unresolved_imports,
        resolved_exports=resolved_exports,
        unresolved_exports=unresolved_exports,
        internal_relationships=internal_relationships,
        external_resolutions=external_resolutions,
        call_observations=call_observations,
        internally_resolved_call_observations=internally_resolved_call_observations,
        internal_call_relationships=internal_call_relationships,
        call_resolution_matrix=dict(call_resolution_matrix),
        compiler_version=compiler_version,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure ENS TypeScript-family source observations")
    parser.add_argument("target_root", type=Path)
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    result = run_ens_source_observation_experiment(args.target_root, args.inventory)
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
