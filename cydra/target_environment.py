"""Target-specific environment discovery after program intake.

The target may declare requirements through repository manifests, but those
requirements remain declarations. CYDRA reports and verifies capabilities; it does
not automatically install or execute arbitrary target-supplied programs.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import shutil
from typing import Iterable


@dataclass(frozen=True)
class TargetRequirement:
    name: str
    kind: str
    version: str | None
    source: str
    required: bool = True


@dataclass(frozen=True)
class TargetCapability:
    requirement: TargetRequirement
    available: bool
    observed: str | None
    reason: str


@dataclass(frozen=True)
class TargetEnvironmentReport:
    root: str
    requirements: tuple[TargetRequirement, ...]
    capabilities: tuple[TargetCapability, ...]

    @property
    def ready(self) -> bool:
        return all(c.available for c in self.capabilities if c.requirement.required)

    @property
    def missing_required(self) -> tuple[str, ...]:
        return tuple(c.requirement.name for c in self.capabilities if c.requirement.required and not c.available)


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def discover_requirements(root: str | Path) -> tuple[TargetRequirement, ...]:
    """Extract declared target prerequisites from common repository manifests."""
    root = Path(root).resolve()
    found: list[TargetRequirement] = []
    package = root / "package.json"
    if package.is_file():
        data = _read_json(package)
        manager = data.get("packageManager")
        if isinstance(manager, str) and "@" in manager:
            tool, version = manager.split("@", 1)
            found.append(TargetRequirement(tool, "package-manager", version, "package.json:packageManager"))
        engines = data.get("engines", {})
        if isinstance(engines, dict):
            for tool in ("node", "pnpm", "npm", "yarn"):
                value = engines.get(tool)
                if isinstance(value, str):
                    found.append(TargetRequirement(tool, "runtime", value, f"package.json:engines.{tool}"))
        scripts = data.get("scripts", {})
        script_text = " ".join(str(v) for v in scripts.values()) if isinstance(scripts, dict) else ""
        if re.search(r"\bdocker(?:\s|$)|docker-compose|docker compose", script_text, re.I):
            found.append(TargetRequirement("docker", "execution-tool", None, "package.json:scripts"))

    for filename, tool, kind in ((".nvmrc", "node", "runtime"), (".node-version", "node", "runtime")):
        path = root / filename
        if path.is_file():
            try:
                version = path.read_text(encoding="utf-8").strip().splitlines()[0]
            except (OSError, IndexError):
                version = None
            if version:
                found.append(TargetRequirement(tool, kind, version, filename))

    if (root / "pnpm-lock.yaml").is_file():
        found.append(TargetRequirement("pnpm-lock.yaml", "lockfile", "present", "repository"))
    if (root / "foundry.toml").is_file():
        found.append(TargetRequirement("forge", "execution-tool", None, "foundry.toml"))
    if (root / "Cargo.toml").is_file():
        found.append(TargetRequirement("cargo", "execution-tool", None, "Cargo.toml"))

    unique: dict[tuple[str, str, str | None, str], TargetRequirement] = {}
    for item in found:
        unique[(item.name, item.kind, item.version, item.source)] = item
    return tuple(unique.values())


def _version(executable: str) -> str | None:
    path = shutil.which(executable)
    if path is None:
        return None
    try:
        result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0][:500] if result.returncode == 0 and text else None


def _numeric_version(value: str) -> tuple[int, ...] | None:
    match = re.search(r"\d+(?:\.\d+){0,2}", value)
    if not match:
        return None
    return tuple(int(part) for part in match.group(0).split("."))


def _matches_version(observed: str | None, required: str | None) -> bool:
    if required in (None, "present"):
        return observed is not None or required == "present"
    actual = _numeric_version(observed or "")
    if actual is None:
        return False
    required = required.strip()
    if required.startswith(">="):
        expected = _numeric_version(required[2:])
        return expected is not None and actual >= expected
    if required.startswith(">"):
        expected = _numeric_version(required[1:])
        return expected is not None and actual > expected
    if required.startswith("<="):
        expected = _numeric_version(required[2:])
        return expected is not None and actual <= expected
    if required.startswith("<"):
        expected = _numeric_version(required[1:])
        return expected is not None and actual < expected
    if required.startswith("^"):
        expected = _numeric_version(required[1:])
        return expected is not None and actual[0] == expected[0] and actual >= expected
    if required.startswith("~"):
        expected = _numeric_version(required[1:])
        return expected is not None and actual[:2] == expected[:2] and actual >= expected
    expected = _numeric_version(required)
    return expected is not None and actual[:len(expected)] == expected


def verify_requirements(root: str | Path, requirements: Iterable[TargetRequirement] | None = None) -> TargetEnvironmentReport:
    root = Path(root).resolve()
    requirements = tuple(requirements or discover_requirements(root))
    capabilities: list[TargetCapability] = []
    for requirement in requirements:
        if requirement.kind == "lockfile":
            available = (root / requirement.name).is_file()
            observed = "present" if available else None
        else:
            observed = _version(requirement.name)
            available = _matches_version(observed, requirement.version)
        reason = "declared target requirement satisfied" if available else "target requirement is missing or version-incompatible"
        capabilities.append(TargetCapability(requirement, available, observed, reason))
    return TargetEnvironmentReport(str(root), requirements, tuple(capabilities))


def format_report(report: TargetEnvironmentReport) -> str:
    lines = [f"TARGET ENVIRONMENT: {'READY' if report.ready else 'BLOCKED'}", f"root: {report.root}"]
    for capability in report.capabilities:
        req = capability.requirement
        declared = f" {req.version}" if req.version else ""
        observed = f" [{capability.observed}]" if capability.observed else ""
        lines.append(f"{'PASS' if capability.available else 'FAIL'} {req.name}{declared}{observed} — {req.source}")
    return "\n".join(lines)
