"""Compiler-backed TypeScript-family source observations for CYDRA."""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Callable

from .source_provider import (
    ObservationStrength,
    SourceObservation,
    SourceObservationKind,
    SourceRelationship,
)


class SourceProviderUnavailable(RuntimeError):
    """Raised when the provider cannot obtain its required semantic tool."""


_KIND_MAP = {kind.value: kind for kind in SourceObservationKind}
_SOURCE_SUFFIXES = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}


class TypeScriptCompilerProvider:
    """Normalize compiler-backed TypeScript/JavaScript structure into CYDRA observations."""

    name = "typescript-compiler"

    def __init__(self, target_root: str | Path, *, node: str = "node", scope_resolver: Callable[[str], str] | None = None) -> None:
        self.target_root = Path(target_root).resolve()
        self.node = node
        self.scope_resolver = scope_resolver or (lambda _path: "UNKNOWN")
        self.helper = Path(__file__).with_name("typescript_observer.cjs")

    @staticmethod
    def _symbol_key(identity: object) -> tuple[str, str] | None:
        if not isinstance(identity, Mapping):
            return None
        qualified = identity.get("qualified_name")
        declaration_path = identity.get("declaration_path")
        if not qualified or not declaration_path:
            return None
        return str(qualified), str(Path(str(declaration_path)).resolve())

    def observe(self, paths: Iterable[str], sources: Mapping[str, str]) -> Iterable[SourceObservation]:
        files = [
            {"path": path, "source": sources[path]}
            for path in sorted(set(paths))
            if path in sources and Path(path).suffix.lower() in _SOURCE_SUFFIXES
        ]
        if not files:
            return ()

        completed = subprocess.run(
            [self.node, str(self.helper)],
            cwd=self.target_root,
            input=json.dumps({"target_root": str(self.target_root), "files": files}),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 42:
            raise SourceProviderUnavailable(
                "target TypeScript Compiler API is unavailable; "
                "@typescript/native-preview/tsgo is not silently substituted "
                "because its native API is a separate, still-evolving capability"
                f": {completed.stderr.strip()}"
            )
        if completed.returncode != 0:
            raise SourceProviderUnavailable(
                f"TypeScript observer failed with exit code {completed.returncode}: {completed.stderr.strip()}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise SourceProviderUnavailable("TypeScript observer returned invalid JSON") from error

        version = str(payload.get("compiler_version", "unknown"))
        supplied_paths = {str(Path(item["path"]).as_posix()): item["path"] for item in files}
        absolute_to_relative = {
            str((self.target_root / item["path"]).resolve()): item["path"] for item in files
        }
        file_observation_ids = {
            path: f"file:{path}:1:{path}" for path in supplied_paths.values()
        }

        observations: list[SourceObservation] = []
        for item in payload.get("observations", []):
            raw_path = str(item["path"])
            absolute_path = str(Path(raw_path).resolve())
            path = absolute_to_relative.get(absolute_path, raw_path)
            if path not in sources:
                continue
            kind = _KIND_MAP.get(str(item["kind"]))
            if kind is None:
                continue
            line = int(item.get("line", 1))
            name = str(item["name"])
            attributes = dict(item.get("attributes", {}))
            attributes["line"] = line
            relationships: tuple[SourceRelationship, ...] = ()

            resolved = attributes.get("resolved_path")
            if kind in {SourceObservationKind.IMPORT, SourceObservationKind.EXPORT} and resolved:
                resolved_path = str(Path(str(resolved)).resolve())
                target_path = absolute_to_relative.get(resolved_path)
                if target_path is not None:
                    relationships = (SourceRelationship(
                        "imports" if kind is SourceObservationKind.IMPORT else "reexports",
                        file_observation_ids[target_path],
                    ),)
                else:
                    attributes["resolution_status"] = "RESOLVED_EXTERNAL"

            source_hash = hashlib.sha256(sources[path].encode("utf-8")).hexdigest()
            observations.append(SourceObservation(
                observation_id=f"{kind.value}:{path}:{line}:{name}",
                kind=kind,
                path=path,
                name=name,
                attributes=attributes,
                provider=self.name,
                tool="typescript-compiler-api",
                tool_version=version,
                strength=ObservationStrength.COMPILER,
                provenance=(f"sha256:{source_hash}", f"target-root:{self.target_root}"),
                scope_state=self.scope_resolver(path),
                relationships=relationships,
            ))

        # Bind call observations to function observations only when the compiler
        # supplied symbol identities for both the caller and callee. Expression
        # text alone is deliberately insufficient evidence for a semantic edge.
        symbol_to_function_id: dict[tuple[str, str], str] = {}
        for observation in observations:
            if observation.kind is not SourceObservationKind.FUNCTION:
                continue
            key = self._symbol_key(observation.attributes.get("symbol_identity"))
            if key is not None:
                symbol_to_function_id.setdefault(key, observation.observation_id)

        enriched: list[SourceObservation] = []
        for observation in observations:
            if observation.kind is not SourceObservationKind.CALL:
                enriched.append(observation)
                continue

            attributes = dict(observation.attributes)
            caller_key = self._symbol_key(attributes.get("caller_symbol_identity"))
            callee_key = self._symbol_key(attributes.get("callee_symbol_identity"))
            caller_id = symbol_to_function_id.get(caller_key) if caller_key else None
            callee_id = symbol_to_function_id.get(callee_key) if callee_key else None

            if caller_key and caller_id:
                attributes["caller_relationship_status"] = "RESOLVED_INTERNAL"
            elif caller_key:
                attributes["caller_relationship_status"] = "RESOLVED_EXTERNAL"
            else:
                attributes["caller_relationship_status"] = "UNRESOLVED"

            if callee_key and callee_id:
                attributes["callee_relationship_status"] = "RESOLVED_INTERNAL"
            elif callee_key:
                attributes["callee_relationship_status"] = "RESOLVED_EXTERNAL"
            else:
                attributes["callee_relationship_status"] = "UNRESOLVED"

            if caller_id and callee_id:
                caller_observation = next(
                    item for item in observations if item.observation_id == caller_id
                )
                relationship = SourceRelationship(
                    relation="calls",
                    target_observation_id=callee_id,
                    attributes={
                        "evidence_observation_id": observation.observation_id,
                        "relationship_basis": "typescript-typechecker-symbol-identity",
                        "caller_symbol": caller_key[0],
                        "callee_symbol": callee_key[0],
                    },
                )
                caller_relationships = tuple(caller_observation.relationships) + (relationship,)
                observations = [
                    SourceObservation(
                        observation_id=item.observation_id,
                        kind=item.kind,
                        path=item.path,
                        name=item.name,
                        attributes=item.attributes,
                        provider=item.provider,
                        tool=item.tool,
                        tool_version=item.tool_version,
                        strength=item.strength,
                        provenance=item.provenance,
                        scope_state=item.scope_state,
                        relationships=caller_relationships if item.observation_id == caller_id else item.relationships,
                    )
                    for item in observations
                ]

            enriched.append(SourceObservation(
                observation_id=observation.observation_id,
                kind=observation.kind,
                path=observation.path,
                name=observation.name,
                attributes=attributes,
                provider=observation.provider,
                tool=observation.tool,
                tool_version=observation.tool_version,
                strength=observation.strength,
                provenance=observation.provenance,
                scope_state=observation.scope_state,
                relationships=observation.relationships,
            ))

        return tuple(enriched)
