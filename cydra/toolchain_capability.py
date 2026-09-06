"""Generic target-local toolchain capability resolution.

A required executable may be supplied by the target's dependency environment rather
than the host PATH. Resolution therefore prefers project-local executables before
falling back to host PATH. Capability probing distinguishes absence, launch failure,
and successful usability without installing or mutating software.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class CapabilityProbe:
    """Read-only observation of one executable capability."""

    name: str
    executable: str | None
    state: str
    observed_version: str | None
    returncode: int | None
    diagnostic: str | None



def _local_candidates(root: Path, name: str) -> tuple[Path, ...]:
    """Return deterministic project-local executable candidates.

    Node workspaces commonly place binaries under the individual package's
    ``node_modules/.bin`` rather than the workspace root. We inspect package
    directories explicitly instead of recursively walking arbitrary node_modules
    trees. The target's dependency layout is therefore observed, not guessed.
    """
    candidates: list[Path] = [root / "node_modules" / ".bin" / name]
    try:
        package_files = sorted(root.glob("**/package.json"))
    except OSError:
        package_files = []
    for package_file in package_files:
        if "node_modules" in package_file.parts:
            continue
        candidates.append(package_file.parent / "node_modules" / ".bin" / name)
    return tuple(dict.fromkeys(candidates))


def resolve_executable(root: str | Path, name: str) -> str | None:
    """Resolve a target executable without mutating the target environment."""
    root = Path(root).resolve()
    for local in _local_candidates(root, name):
        if local.is_file():
            return str(local)
    return shutil.which(name)


def probe_executable(root: str | Path, name: str) -> CapabilityProbe:
    """Probe a resolved executable and preserve the distinction between states.

    ``--version`` is intentionally used as a read-only usability probe. A binary
    that exists but exits non-zero, panics, or cannot be launched is not reported as
    missing. Diagnostic output is bounded so capability evidence remains durable.
    """
    executable = resolve_executable(root, name)
    if executable is None:
        return CapabilityProbe(name, None, "MISSING", None, None, "executable not found")
    try:
        result = subprocess.run(
            [executable, "--version"],
            cwd=Path(root).resolve(),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CapabilityProbe(name, executable, "UNUSABLE", None, 124, f"version probe timed out: {exc}")
    except OSError as exc:
        return CapabilityProbe(name, executable, "UNUSABLE", None, 127, f"version probe could not launch: {exc}")
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    diagnostic = (stderr or stdout or None)
    if result.returncode != 0:
        return CapabilityProbe(name, executable, "UNUSABLE", None, result.returncode, diagnostic[:1000] if diagnostic else "version probe failed")
    version = stdout.splitlines()[0][:500] if stdout else None
    if not version:
        return CapabilityProbe(name, executable, "UNUSABLE", None, result.returncode, "version probe produced no version")
    return CapabilityProbe(name, executable, "USABLE", version, result.returncode, None)


def observe_version(root: str | Path, name: str) -> str | None:
    """Backward-compatible version observation using target-local resolution first."""
    probe = probe_executable(root, name)
    return probe.observed_version if probe.state == "USABLE" else None


__all__ = ["CapabilityProbe", "observe_version", "probe_executable", "resolve_executable"]
