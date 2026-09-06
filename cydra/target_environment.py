"""Target-specific environment discovery and capability verification.

Declarations come from the target repository and remain evidence, not authority
to execute or install arbitrary software. Discovery is deliberately conservative:
CYDRA reads common manifests, toolchain files, CI configuration, and setup/readme
instructions, then reports what the operator/runtime must provide.

Environment preparation is staged: bootstrap capabilities are verified first,
then an explicitly supplied target-declared materialization command may run, and
only afterward are materialized capabilities verified. CYDRA never invents or
substitutes a materialization command.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Iterable, Sequence

from .toolchain_capability import probe_executable


@dataclass(frozen=True)
class TargetRequirement:
    name: str
    kind: str
    version: str | None
    source: str
    required: bool = True
    authority: str = "PROJECT"
    purpose: str = "canonical-build"


@dataclass(frozen=True)
class TargetCapability:
    requirement: TargetRequirement
    available: bool
    observed: str | None
    reason: str
    state: str = "UNKNOWN"
    executable: str | None = None
    diagnostic: str | None = None


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

    def capabilities_for(self, purpose: str) -> tuple[TargetCapability, ...]:
        return tuple(c for c in self.capabilities if c.requirement.purpose == purpose)

    def ready_for(self, purpose: str) -> bool:
        scoped = self.capabilities_for(purpose)
        return bool(scoped) and all(c.available for c in scoped)


@dataclass(frozen=True)
class EnvironmentPreparation:
    bootstrap: TargetEnvironmentReport
    materialization_command: tuple[str, ...]
    materialization_returncode: int
    materialization_status: str
    final: TargetEnvironmentReport

    @property
    def ready(self) -> bool:
        return self.bootstrap.ready and self.materialization_returncode == 0 and self.final.ready


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


def _add(found: list[TargetRequirement], name: str, kind: str, version: str | None, source: str, *, authority: str = "PROJECT", required: bool = True, purpose: str = "canonical-build") -> None:
    found.append(TargetRequirement(name, kind, version, source, required, authority, purpose))


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

    for filename in ("pnpm-lock.yaml", "package-lock.json", "yarn.lock"):
        if (root / filename).is_file():
            _add(found, filename, "lockfile", "present", "repository")
    if (root / "foundry.toml").is_file():
        _add(found, "forge", "execution-tool", None, "foundry.toml")
    if (root / "Cargo.toml").is_file():
        _add(found, "cargo", "execution-tool", None, "Cargo.toml")
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        source = "pyproject.toml" if (root / "pyproject.toml").is_file() else "requirements.txt"
        _add(found, "python3", "runtime", None, source)


def _discover_commands(source: str, text: str, found: list[TargetRequirement], *, purpose: str = "canonical-build") -> None:
    lowered = text.lower()
    for tool in _COMMAND_TOOLS:
        if re.search(rf"(?<![\w-]){re.escape(tool)}(?:\s|$)", lowered):
            kind = "runtime" if tool in {"node", "python", "python3"} else "execution-tool"
            _add(found, tool, kind, None, source, purpose=purpose)


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
        blocks = re.findall(r"```(?:bash|sh|shell|console|zsh)?\s*\n(.*?)```", text, flags=re.I | re.S)
        commands = "\n".join(blocks)
        commands += "\n" + "\n".join(line[2:].strip() for line in text.splitlines() if line.lstrip().startswith("$ "))
        if commands.strip():
            _discover_commands(str(path.relative_to(root)), commands, found)


def _workflow_value(text: str, action: str, key: str) -> str | None:
    """Read a value from the setup block belonging to one GitHub Action."""
    action_re = re.compile(rf"^\s*-?\s*uses:\s*{re.escape(action)}@[^\n]*$", re.I | re.M)
    match = action_re.search(text)
    if not match:
        return None
    remainder = text[match.end():]
    next_action = re.search(r"^\s*-?\s*uses:\s*[^\n]+$", remainder, re.I | re.M)
    body = remainder[: next_action.start()] if next_action else remainder
    value = re.search(rf"^\s*{re.escape(key)}:\s*[\"']?([^\s\"']+)", body, flags=re.I | re.M)
    return value.group(1) if value else None


def _discover_ci_requirements(root: Path, found: list[TargetRequirement]) -> None:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in workflows.glob("*.y*ml"):
        text = _read_text(path)
        if not text:
            continue
        source = str(path.relative_to(root))
        purpose = "e2e" if re.search(r"(?:^|[^\w])e2e(?:[^\w]|$)", path.stem, re.I) else "ci"
        if re.search(r"uses:\s*actions/setup-node(?:@|\s)", text):
            _add(found, "node", "runtime", _workflow_value(text, "actions/setup-node", "node-version"), source, required=False, purpose=purpose)
        if re.search(r"uses:\s*pnpm/action-setup(?:@|\s)", text):
            _add(found, "pnpm", "package-manager", _workflow_value(text, "pnpm/action-setup", "version"), source, required=False, purpose=purpose)
        if re.search(r"\bdocker(?:\s+compose|-compose)?\b", text, re.I):
            _add(found, "docker", "execution-tool", None, source, required=False, purpose="e2e" if purpose == "e2e" else "ci")


def discover_requirements(root: str | Path) -> tuple[TargetRequirement, ...]:
    root = Path(root).resolve()
    found: list[TargetRequirement] = []
    _discover_manifest_requirements(root, found)
    _discover_readme_and_setup(root, found)
    _discover_ci_requirements(root, found)
    unique: dict[tuple[str, str, str | None, str, str], TargetRequirement] = {}
    for item in found:
        unique[(item.name, item.kind, item.version, item.source, item.purpose)] = item
    return tuple(unique.values())


def _numeric_version(value: str) -> tuple[int, ...] | None:
    match = re.search(r"\d+(?:\.\d+){0,2}", value)
    if not match:
        return None
    return tuple(int(part) for part in match.group(0).split("."))


def _matches_version(observed: str | None, required: str | None) -> bool:
    if required in (None, "present"):
        return observed is not None or required == "present"
    required = required.strip()
    if not _numeric_version(required):
        return False
    actual = _numeric_version(observed or "")
    if actual is None:
        return False
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
            state = "MATERIALIZED" if available else "MISSING"
            executable = None
            diagnostic = None
        else:
            probe = probe_executable(root, requirement.name)
            observed = probe.observed_version
            available = _matches_version(observed, requirement.version)
            state = probe.state
            executable = probe.executable
            diagnostic = probe.diagnostic
        if available:
            reason = "declared target requirement satisfied"
        elif state == "UNUSABLE":
            reason = "executable is materialized but the read-only capability probe failed"
        elif state == "MISSING":
            reason = "target requirement is missing"
        elif requirement.version and not _numeric_version(requirement.version):
            reason = "non-numeric CI/channel declaration; does not establish a canonical version"
        else:
            reason = "target requirement is version-incompatible"
        capabilities.append(TargetCapability(requirement, available, observed, reason, state, executable, diagnostic))
    return TargetEnvironmentReport(str(root), requirements, tuple(capabilities))


def prepare_target_environment(
    root: str | Path,
    *,
    bootstrap_requirements: Iterable[TargetRequirement],
    final_requirements: Iterable[TargetRequirement],
    materialization_command: Sequence[str],
    timeout: int = 1800,
) -> EnvironmentPreparation:
    """Materialize target dependencies only after bootstrap capabilities pass.

    The command is supplied by the target-specific adapter. This function never
    invents an install command, changes it, or substitutes another toolchain.
    """
    root = Path(root).resolve()
    bootstrap = verify_requirements(root, bootstrap_requirements)
    command = tuple(materialization_command)
    if not bootstrap.ready:
        return EnvironmentPreparation(bootstrap, command, 127, "BOOTSTRAP_BLOCKED", verify_requirements(root, final_requirements))
    if not command:
        return EnvironmentPreparation(bootstrap, command, 127, "MATERIALIZATION_COMMAND_MISSING", verify_requirements(root, final_requirements))
    try:
        result = subprocess.run(
            list(command), cwd=root, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return EnvironmentPreparation(bootstrap, command, 124, "TIMEOUT", verify_requirements(root, final_requirements))
    except OSError:
        return EnvironmentPreparation(bootstrap, command, 127, "TOOLCHAIN_UNAVAILABLE", verify_requirements(root, final_requirements))
    status = "SUCCEEDED" if result.returncode == 0 else "FAILED"
    final = verify_requirements(root, final_requirements)
    return EnvironmentPreparation(bootstrap, command, result.returncode, status, final)


def format_report(report: TargetEnvironmentReport) -> str:
    lines = [f"TARGET ENVIRONMENT: {'READY' if report.ready else 'BLOCKED'}", f"root: {report.root}"]
    for purpose in sorted({c.requirement.purpose for c in report.capabilities}):
        scoped = report.capabilities_for(purpose)
        status = "READY" if report.ready_for(purpose) else "BLOCKED"
        lines.append(f"{purpose}: {status}")
        for capability in scoped:
            req = capability.requirement
            declared = f" {req.version}" if req.version else ""
            observed = f" [{capability.observed}]" if capability.observed else ""
            required = "required" if req.required else "informational"
            lines.append(f"  {'PASS' if capability.available else 'FAIL'} {req.name}{declared}{observed} ({required}) — {capability.reason}")
            lines.append(f"    state={capability.state} executable={capability.executable or 'none'}")
            if capability.diagnostic:
                lines.append(f"    diagnostic={capability.diagnostic[:300]}")
    return "\n".join(lines)
