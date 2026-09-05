"""Gateway-owned Foundry build execution and durable result rehydration."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json, shutil, subprocess
from typing import Mapping

from .execution_request import ExecutionRequest


def _hash(value: bytes) -> str:
    return sha256(value).hexdigest()

def _relative(root: Path, path: Path) -> str:
    try: return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc: raise ValueError("artifact escapes Foundry project root") from exc

@dataclass(frozen=True)
class FoundryBuildExecutionResult:
    execution_id: str
    request_digest: str
    outcome: str
    target: str
    command: tuple[str, ...]
    returncode: int
    stdout_sha256: str
    stderr_sha256: str
    forge_path: str
    forge_version: str
    build_info_dir: str
    artifact_hashes: tuple[tuple[str, str], ...]
    adapter: str = "foundry"

    def canonical_payload(self):
        return {"execution_id": self.execution_id, "request_digest": self.request_digest,
                "adapter": self.adapter, "outcome": self.outcome, "target": self.target,
                "command": list(self.command), "returncode": self.returncode,
                "stdout_sha256": self.stdout_sha256, "stderr_sha256": self.stderr_sha256,
                "forge_path": self.forge_path, "forge_version": self.forge_version,
                "build_info_dir": self.build_info_dir,
                "artifact_hashes": [list(x) for x in self.artifact_hashes]}

class FoundryBuildAdapter:
    """Runs only gateway-authorized ``forge build --build-info`` requests."""
    def __init__(self): self._capability = None; self.execute_calls = 0
    def _bind_gateway_capability(self, capability):
        if self._capability is not None: raise RuntimeError("Foundry adapter is already capability-bound")
        self._capability = capability
    def _validate_request(self, request):
        if request.adapter != "foundry" or request.command != ("forge", "build", "--build-info"):
            raise ValueError("Foundry adapter requires exact forge build --build-info request")
    def _result(self, request, root, returncode, stdout, stderr, forge_path, forge_version):
        build_dir = root / "out" / "build-info"
        artifacts = ()
        if returncode == 0:
            if not build_dir.is_dir(): raise RuntimeError("successful Foundry build did not emit build-info")
            paths = tuple(sorted(p for p in build_dir.rglob("*.json") if p.is_file()))
            if len(paths) != 1: raise RuntimeError("Foundry build-info output is missing or ambiguous")
            artifacts = tuple((_relative(root, p), _hash(p.read_bytes())) for p in paths)
        return FoundryBuildExecutionResult(request.execution_id, request.digest,
            "BUILD_SUCCEEDED" if returncode == 0 else "BUILD_FAILED", str(root), tuple(request.command), returncode,
            _hash(stdout.encode()), _hash(stderr.encode()), forge_path, forge_version,
            _relative(root, build_dir), artifacts)
    def execute(self, *, request, authorization, gateway_capability):
        if gateway_capability is not self._capability: raise PermissionError("Foundry execution requires gateway capability")
        self._validate_request(request); self.execute_calls += 1
        root = Path(request.target).resolve(); forge = shutil.which("forge")
        if forge is None: raise RuntimeError("forge executable is unavailable")
        version = subprocess.run((forge, "--version"), cwd=root, text=True, capture_output=True, check=False)
        if version.returncode or not (version.stdout or version.stderr).strip(): raise RuntimeError("unable to observe Forge identity")
        run = subprocess.run(request.command, cwd=root, text=True, capture_output=True, check=False)
        return self._result(request, root, run.returncode, run.stdout, run.stderr, str(Path(forge).resolve()), (version.stdout or version.stderr).strip())
    def rehydrate_result(self, *, payload: Mapping[str, object], request):
        required = {"execution_id","request_digest","adapter","outcome","target","command","returncode","stdout_sha256","stderr_sha256","forge_path","forge_version","build_info_dir","artifact_hashes"}
        if set(payload) != required: raise ValueError("Foundry durable result payload is incomplete")
        if payload["execution_id"] != request.execution_id or payload["request_digest"] != request.digest or payload["adapter"] != "foundry": raise ValueError("Foundry durable result does not match request")
        self._validate_request(request)
        result = FoundryBuildExecutionResult(str(payload["execution_id"]), str(payload["request_digest"]), str(payload["outcome"]), str(payload["target"]), tuple(payload["command"]), int(payload["returncode"]), str(payload["stdout_sha256"]), str(payload["stderr_sha256"]), str(payload["forge_path"]), str(payload["forge_version"]), str(payload["build_info_dir"]), tuple((str(p),str(h)) for p,h in payload["artifact_hashes"]), str(payload["adapter"]))
        if result.command != request.command or Path(result.target).resolve() != Path(request.target).resolve(): raise ValueError("Foundry durable result command or target mismatch")
        if result.outcome == "BUILD_SUCCEEDED" and (result.returncode != 0 or len(result.artifact_hashes) != 1): raise ValueError("successful Foundry durable result is incomplete")
        return result
