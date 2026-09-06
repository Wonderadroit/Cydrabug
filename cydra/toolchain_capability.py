"""Generic target-local toolchain capability resolution.

A required executable may be supplied by the target's dependency environment rather
than the host PATH. Resolution therefore prefers project-local executables before
falling back to host PATH, while version observation remains read-only. This module
never installs software and never treats a discovered executable as execution
authority.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


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


def observe_version(root: str | Path, name: str) -> str | None:
    """Observe an executable version using target-local resolution first."""
    executable = resolve_executable(root, name)
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, "--version"],
            cwd=Path(root).resolve(),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0][:500] if result.returncode == 0 and text else None
