"""Fail-closed acceptance of Foundry build-info as compiler AST evidence.

This module accepts an already-existing checkout and successful Foundry build.  It
does not materialize repositories, execute a build, or infer a Solidity compiler
version from Forge.  Only ASTs bound to an accepted receipt leave this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping
from types import MappingProxyType

from .external_execution import ExternalExecutionGateway
from .execution_request import ExecutionRequest
from .foundry_execution import FoundryBuildExecutionResult


INITIAL_VAULTS_REPOSITORY = "immunefi-team/vaults"
INITIAL_VAULTS_REVISION = "49c1de26cda19c9e8a4aa311ba3b0dc864f34a25"

_PROHIBITED_PARTS = ("report", "finding", "leaderboard", "remediation", "writeup", "known_issue", "known-issue")


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _canonical_fingerprint(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    return f"foundry-build-receipt:{_sha256_bytes(encoded)}"


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("path escapes checkout root") from exc


def _reject_prohibited_path(path: str) -> None:
    normalized = path.lower().replace("_", "-")
    if any(token in normalized for token in _PROHIBITED_PARTS):
        raise ValueError("prohibited report/finding/leaderboard/remediation-like build input")


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(("git", *args), cwd=root, text=True, capture_output=True, check=False, timeout=20)
    except OSError as exc:
        raise ValueError("checkout is not a readable Git worktree") from exc
    if result.returncode:
        raise ValueError(f"Git checkout verification failed: {' '.join(args)}")
    return result.stdout.strip()


def _source_inventory(root: Path) -> tuple[tuple[str, str], ...]:
    files: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.sol")):
        relative = _relative(root, path)
        if ".git" in Path(relative).parts or "out" in Path(relative).parts or "cache" in Path(relative).parts:
            continue
        _reject_prohibited_path(relative)
        files.append((relative, _sha256_bytes(path.read_bytes())))
    if not files:
        raise ValueError("checkout has no Solidity source files")
    return tuple(files)


def _inventory_fingerprint(files: Iterable[tuple[str, str]]) -> str:
    digest = sha256()
    for path, content_hash in files:
        digest.update(path.encode())
        digest.update(b"\0")
        digest.update(content_hash.encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _required_mapping(value: object, message: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(message)
    return value


def _compiler_metadata(document: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
    versions: set[str] = set()
    for key in ("compiler_version", "solcVersion", "solc_version"):
        value = document.get(key)
        if isinstance(value, str) and value.strip():
            versions.add(value.strip())
    compiler = document.get("compiler")
    if isinstance(compiler, Mapping) and isinstance(compiler.get("version"), str) and compiler["version"].strip():
        versions.add(compiler["version"].strip())
    output = document.get("output")
    if isinstance(output, Mapping) and isinstance(output.get("version"), str) and output["version"].strip():
        versions.add(output["version"].strip())
    if len(versions) != 1:
        raise ValueError("build-info must contain one unambiguous Solidity compiler version")
    settings = _required_mapping(_required_mapping(document.get("input"), "build-info input is missing").get("settings"), "build-info compiler settings are missing")
    return next(iter(versions)), dict(settings)


@dataclass(frozen=True)
class CompilerAstUnit:
    """One accepted compiler-emitted AST, addressable by its checkout source path."""

    source_path: str
    source_sha256: str
    ast: str
    build_info_path: str
    build_info_sha256: str
    receipt_fingerprint: str


@dataclass(frozen=True)
class FoundryBuildReceipt:
    repository: str
    expected_revision: str
    head: str
    source_inventory: tuple[tuple[str, str], ...]
    source_fingerprint: str
    foundry_toml_sha256: str
    command: tuple[str, ...]
    returncode: int
    forge_version: str
    build_info_paths: tuple[str, ...]
    build_info_sha256: tuple[tuple[str, str], ...]
    solc_version: str
    compiler_settings: Mapping[str, Any]
    fingerprint: str

    def canonical_payload(self) -> dict[str, object]:
        return {
            "repository": self.repository, "expected_revision": self.expected_revision, "head": self.head,
            "source_inventory": [list(item) for item in self.source_inventory], "source_fingerprint": self.source_fingerprint,
            "foundry_toml_sha256": self.foundry_toml_sha256, "command": list(self.command),
            "returncode": self.returncode, "forge_version": self.forge_version,
            "build_info_paths": list(self.build_info_paths), "build_info_sha256": [list(item) for item in self.build_info_sha256],
            "solc_version": self.solc_version, "compiler_settings": dict(self.compiler_settings), "fingerprint": self.fingerprint,
        }

    def to_json(self) -> str:
        return json.dumps(self.canonical_payload(), sort_keys=True, indent=2) + "\n"


@dataclass(frozen=True)
class AcceptedFoundryBuild:
    """Receipt-bound compiler artifacts; use ``compiler_asts`` with AST extraction."""

    receipt: FoundryBuildReceipt
    compiler_asts: tuple[CompilerAstUnit, ...]


def validate_foundry_build_receipt(payload: Mapping[str, object]) -> FoundryBuildReceipt:
    if not isinstance(payload, Mapping):
        raise TypeError("receipt payload must be a mapping")
    supplied = payload.get("fingerprint")
    body = dict(payload); body.pop("fingerprint", None)
    if not isinstance(supplied, str) or supplied != _canonical_fingerprint(body):
        raise ValueError("foundry build receipt fingerprint does not match canonical payload")
    inventory = tuple((str(path), str(digest)) for path, digest in payload["source_inventory"])
    hashes = tuple((str(path), str(digest)) for path, digest in payload["build_info_sha256"])
    settings = MappingProxyType(dict(_required_mapping(payload["compiler_settings"], "receipt compiler settings are invalid")))
    receipt = FoundryBuildReceipt(str(payload["repository"]), str(payload["expected_revision"]), str(payload["head"]), inventory, str(payload["source_fingerprint"]), str(payload["foundry_toml_sha256"]), tuple(payload["command"]), int(payload["returncode"]), str(payload["forge_version"]), tuple(payload["build_info_paths"]), hashes, str(payload["solc_version"]), settings, supplied)
    if receipt.source_fingerprint != _inventory_fingerprint(inventory):
        raise ValueError("receipt source fingerprint does not match source inventory")
    return receipt

def accepted_ast_evidence(build: AcceptedFoundryBuild):
    if not isinstance(build, AcceptedFoundryBuild):
        raise TypeError("provenance-backed AST projection requires AcceptedFoundryBuild")
    receipt = validate_foundry_build_receipt(json.loads(build.receipt.to_json()))
    expected = dict(receipt.build_info_sha256)
    evidence = []
    from .ast_dataflow import extract_ast_relationships
    for unit in build.compiler_asts:
        if unit.receipt_fingerprint != receipt.fingerprint or expected.get(unit.build_info_path) != unit.build_info_sha256:
            raise ValueError("compiler AST unit is not bound to the accepted receipt")
        ast = json.loads(unit.ast)
        for item in extract_ast_relationships(ast, unit.source_path):
            evidence.append(replace(item, metadata={"foundry_receipt": receipt.fingerprint, "build_info_sha256": unit.build_info_sha256, "source_sha256": unit.source_sha256}))
    return tuple(evidence)

def project_accepted_ast_evidence(model, build: AcceptedFoundryBuild):
    return model.project_ast_evidence(list(accepted_ast_evidence(build)))


def accept_foundry_build_info(
    *,
    checkout: str | Path,
    repository: str,
    expected_revision: str,
    expected_request: ExecutionRequest,
    execution_result: FoundryBuildExecutionResult,
    execution_gateway: ExternalExecutionGateway,
    build_info_dir: str | Path = "out/build-info",
) -> AcceptedFoundryBuild:
    """Accept one provenance-complete Foundry build-info artifact or reject it.

    Forge and artifact provenance must come from the gateway-owned execution
    result. ``solc_version`` is read exclusively from the accepted build-info
    document.
    """
    root = Path(checkout).resolve()
    if not repository.strip() or not expected_revision.strip():
        raise ValueError("repository and expected_revision must not be empty")
    if not isinstance(execution_gateway, ExternalExecutionGateway):
        raise TypeError("Foundry acceptance requires the external execution gateway")
    if not isinstance(expected_request, ExecutionRequest):
        raise TypeError("Foundry acceptance requires a canonical execution request")
    if not isinstance(execution_result, FoundryBuildExecutionResult):
        raise TypeError("Foundry acceptance requires a gateway-owned Foundry execution result")
    if expected_request.adapter != "foundry" or expected_request.target != str(root) or expected_request.command != ("forge", "build", "--build-info"):
        raise ValueError("Foundry execution request does not match accepted build")
    if execution_result.request_digest != expected_request.digest:
        raise ValueError("Foundry execution result does not match the expected execution request")
    execution_gateway.require_trusted_result(execution_result)
    if execution_result.outcome != "BUILD_SUCCEEDED" or execution_result.returncode != 0:
        raise ValueError("Foundry build result was not successful")
    if Path(execution_result.target).resolve() != root:
        raise ValueError("Foundry execution target does not match checkout")
    if tuple(execution_result.command) != ("forge", "build", "--build-info"):
        raise ValueError("Foundry execution command does not match accepted build")
    if len(execution_result.artifact_hashes) != 1:
        raise ValueError("trusted Foundry result has missing or ambiguous build-info")
    if not (root / "foundry.toml").is_file():
        raise ValueError("checkout is missing foundry.toml")
    head = _git(root, "rev-parse", "HEAD")
    if head != expected_revision:
        raise ValueError("checkout HEAD does not match expected revision")
    if _git(root, "status", "--porcelain"):
        raise ValueError("checkout must be clean before build-info acceptance")
    command = tuple(execution_result.command)

    inventory = _source_inventory(root)
    inventory_by_path = dict(inventory)
    build_dir = (root / build_info_dir).resolve() if not Path(build_info_dir).is_absolute() else Path(build_info_dir).resolve()
    relative_build_dir = _relative(root, build_dir)
    _reject_prohibited_path(relative_build_dir)
    if not build_dir.is_dir():
        raise ValueError("Foundry build-info directory is missing")
    artifacts = tuple(sorted(path for path in build_dir.rglob("*.json") if path.is_file()))
    if not artifacts:
        raise ValueError("Foundry build-info is missing")
    if len(artifacts) != 1:
        raise ValueError("Foundry build-info is ambiguous")

    artifact = artifacts[0]
    relative_artifact = _relative(root, artifact)
    recorded_path, recorded_hash = execution_result.artifact_hashes[0]
    if execution_result.build_info_dir != relative_build_dir or recorded_path != relative_artifact:
        raise ValueError("build-info artifact does not match trusted Foundry result")
    _reject_prohibited_path(relative_artifact)
    artifact_bytes = artifact.read_bytes()
    artifact_hash = _sha256_bytes(artifact_bytes)
    if recorded_hash != artifact_hash:
        raise ValueError("build-info artifact hash does not match trusted Foundry result")
    try:
        document = json.loads(artifact_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Foundry build-info is not valid JSON") from exc
    document = _required_mapping(document, "Foundry build-info root must be a mapping")
    solc_version, settings = _compiler_metadata(document)
    input_sources = _required_mapping(_required_mapping(document.get("input"), "build-info input is missing").get("sources"), "build-info input sources are missing")
    output_sources = _required_mapping(_required_mapping(document.get("output"), "build-info output is missing").get("sources"), "build-info output sources are missing")
    source_id_to_path = document.get("source_id_to_path")
    if source_id_to_path is not None:
        source_id_to_path = _required_mapping(source_id_to_path, "build-info source ID mapping is invalid")
        normalized_source_ids = {str(key): str(value) for key, value in source_id_to_path.items()}
        if len(set(normalized_source_ids.values())) != len(normalized_source_ids) or set(normalized_source_ids.values()) != set(input_sources):
            raise ValueError("build-info source ID mapping is inconsistent")

    ast_units: list[CompilerAstUnit] = []
    if set(input_sources) != set(output_sources) or set(input_sources) != set(inventory_by_path):
        raise ValueError("build-info source-unit mapping does not match checkout inventory")
    for source_path in sorted(input_sources):
        _reject_prohibited_path(source_path)
        source = _required_mapping(input_sources[source_path], "build-info source input is invalid")
        content = source.get("content")
        if not isinstance(content, str) or _sha256_bytes(content.encode()) != inventory_by_path[source_path]:
            raise ValueError("build-info source content does not match checkout source")
        output = _required_mapping(output_sources[source_path], "build-info source output is invalid")
        if source_id_to_path is not None and str(output.get("id")) not in normalized_source_ids or source_id_to_path is not None and normalized_source_ids[str(output.get("id"))] != source_path:
            raise ValueError("build-info output source ID does not map to source path")
        ast = output.get("ast")
        if not isinstance(ast, Mapping) or not isinstance(ast.get("nodeType"), str):
            raise ValueError("build-info source unit is missing compiler AST")
        ast_units.append(CompilerAstUnit(source_path, inventory_by_path[source_path], json.dumps(ast, sort_keys=True, separators=(",", ":")), relative_artifact, artifact_hash, ""))

    source_fingerprint = _inventory_fingerprint(inventory)
    foundry_hash = _sha256_bytes((root / "foundry.toml").read_bytes())
    receipt_payload = {
        "repository": repository, "expected_revision": expected_revision, "head": head,
        "source_inventory": list(inventory), "source_fingerprint": source_fingerprint,
        "foundry_toml_sha256": foundry_hash, "command": list(command),
        "returncode": execution_result.returncode, "forge_version": execution_result.forge_version,
        "build_info_paths": [relative_artifact], "build_info_sha256": [[relative_artifact, artifact_hash]],
        "solc_version": solc_version, "compiler_settings": dict(settings),
    }
    receipt = FoundryBuildReceipt(
        repository, expected_revision, head, inventory, source_fingerprint, foundry_hash,
        command, execution_result.returncode, execution_result.forge_version, (relative_artifact,),
        ((relative_artifact, artifact_hash),), solc_version, dict(settings),
        _canonical_fingerprint(receipt_payload),
    )
    ast_units = [replace(unit, receipt_fingerprint=receipt.fingerprint) for unit in ast_units]
    return AcceptedFoundryBuild(receipt, tuple(ast_units))
