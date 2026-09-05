"""Compiler-backed TypeScript source observations for CYDRA."""
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


class TypeScriptCompilerProvider:
    """Normalize compiler-backed TypeScript/TSX structure into CYDRA observations."""

    name = "typescript-compiler"

    def __init__(self, target_root: str | Path, *, node: str = "node", scope_resolver: Callable[[str], str] | None = None) -> None:
        self.target_root = Path(target_root).resolve()
        self.node = node
        self.scope_resolver = scope_resolver or (lambda _path: "UNKNOWN")
        self.helper = Path(__file__).with_name("typescript_observer.cjs")

    def observe(self, paths: Iterable[str], sources: Mapping[str, str]) -> Iterable[SourceObservation]:
        files = [
            {"path": path, "source": sources[path]}
            for path in sorted(set(paths))
            if path in sources and Path(path).suffix in {".ts", ".tsx", ".mts", ".cts"}
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
                    relationships = (SourceRelationship("imports" if kind is SourceObservationKind.IMPORT else "reexports", file_observation_ids[target_path]),)
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

        return tuple(observations)
