"""Target-specific environment discovery and capability verification.

Declarations come from the target repository and remain evidence, not authority
to execute or install arbitrary software. Discovery is deliberately conservative:
CYDRA reads common manifests, toolchain files, CI configuration, and setup/readme
instructions, then reports what the operator/runtime must provide.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Iterable


@dataclass(frozen=True)
class TargetRequirement:
    name: str
    kind: str
    version: str | None
    source: str
    required: bool = True
    authority: str = "PROJECT"


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
        return tuple(
            c.requirement.name
            for c in self.capabilities
            if c.requirement.required and not c.available
        )


_VERSIONED_TOOLS = ("node", "pnpm", "npm", "yarn", "python", "python3", "forge", "cargo")
_COMMAND_TOOLS = ("docker", "forge", "cargo", "pnpm", "npm", "yarn", "node", "python", "python3")
_SETUP_FILENAMES = {"CONTRIBUTING.md", "DEVELOPMENT.md", "SETUP.md", "INSTALL.md", "DEVELOPING.md"}


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _add(found: list[TargetRequirement], name: str, kind: str, version: str | None, source: str, *, authority: str = "PROJECT") -> None:
    found.append(TargetRequirement(name, kind, version, source, True, authority))


def _discover_manifest_requirements(root: Path, found: list[TargetRequirement]) -> None:
    package = root / "package.json"
    if package.is_file():
        data = _read_json(package)
        manager = data.get("packageManager")
        if isinstance(manager, str) and "@" in manager:
            tool, version = manager.rsplit("@", 1)
            if tool in {"pnpm", "npm", "yarn"} and version:
                _add(found, tool, "package-manager", version, "package.json:packageManager")
        engines = data.get("engines", {})
        if isinstance(engines, dict):
            for tool in ("node", "pnpm", "npm", "yarn"):
                value = engines.get(tool)
                if isinstance(value, str):
                    _add(found, tool, "runtime", value, f"package.json:engines.{tool}")
        scripts = data.get("scripts", {})
        if isinstance(scripts, dict):
            _discover_commands("package.json:scripts", " ".join(str(v) for v in scripts.values()), found)

    for filename, tool in ((".nvmrc", "node"), (".node-version", "node")):
        path = root / filename
        if path.is_file():
            version = _read_text(path).strip().splitlines()
            if version and version[0]:
                _add(found, tool, "runtime", version[0].strip(), filename)

    if (root / "pnpm-lock.yaml").is_file():
        _add(found, "pnpm-lock.yaml", "lockfile", "present", "repository")
    if (root / "package-lock.json").is_file():
        _add(found, "package-lock.json", "lockfile", "present", "repository")
    if (root / "yarn.lock").is_file():
        _add(found, "yarn.lock", "lockfile", "present", "repository")
    if (root / "foundry.toml").is_file():
        _add(found, "forge", "execution-tool", None, "foundry.toml")
    if (root / "Cargo.toml").is_file():
        _add(found, "cargo", "execution-tool", None, "Cargo.toml")
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        source = "pyproject.toml" if (root / "pyproject.toml").is_file() else "requirements.txt"
        _add(found, "python3", "runtime", None, source)


def _discover_commands(source: str, text: str, found: list[TargetRequirement]) -> None:
    """Extract tools only from explicit command-like text, never from prose."""
    lowered = text.lower()
    for tool in _COMMAND_TOOLS:
        if re.search(rf"(?<![\w-]){re.escape(tool)}(?:\s|$)", lowered):
            kind = "runtime" if tool in {"node", "python", "python3"} else "execution-tool"
            _add(found, tool, kind, None, source)


def _discover_readme_and_setup(root: Path, found: list[TargetRequirement]) -> None:
    candidates: list[Path] = []
    for path in root.glob("README*"):
        if path.is_file() and path.suffix.lower() in {"", ".md", ".txt"}:
            candidates.append(path)
    for filename in _SETUP_FILENAMES:
        path = root / filename
        if path.is_file():
            candidates.append(path)
    docs = root / "docs"
    if docs.is_dir():
        for path in docs.glob("*.md"):
            if any(token in path.stem.lower() for token in ("setup", "install", "develop", "build")):
                candidates.append(path)

    seen: set[Path] = set()
    for path in candidates:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        text = _read_text(path)
        if not text:
            continue
        blocks = re.findall(
            r"```(?:bash|sh|shell|console|zsh)?\s*\n(.*?)```",
            text,
            flags=re.I | re.S,
        )
        commands = "\n".join(blocks)
        commands += "\n" + "\n".join(
            line[2:].strip() for line in text.splitlines() if line.lstrip().startswith("$ ")
        )
        if commands.strip():
            _discover_commands(str(path.relative_to(root)), commands, found)


def _discover_ci_requirements(root: Path, found: list[TargetRequirement]) -> None:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in workflows.glob("*.y*ml"):
        text = _read_text(path)
        if not text:
            continue
        source = str(path.relative_to(root))
        if re.search(r"uses:\s*actions/setup-node(?:@|\s)", text):
            match = re.search(r"node-version:\s*[\"']?([^\s\"']+)", text)
            _add(found, "node", "runtime", match.group(1) if match else None, source)
        if re.search(r"uses:\s*pnpm/action-setup(?:@|\s)", text):
            match = re.search(r"version:\s*[\"']?([^\s\"']+)", text)
            _add(found, "pnpm", "package-manager", match.group(1) if match else None, source)
        if re.search(r"\bdocker(?:\s+compose|-compose)?\b", text, re.I):
            _add(found, "docker", "execution-tool", None, source)


def discover_requirements(root: str | Path) -> tuple[TargetRequirement, ...]:
    """Extract target prerequisites without executing or installing target software."""
    root = Path(root).resolve()
    found: list[TargetRequirement] = []
    _discover_manifest_requirements(root, found)
    _discover_readme_and_setup(root, found)
    _discover_ci_requirements(root, found)

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
    return expected is not None and actual[: len(expected)] == expected


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
