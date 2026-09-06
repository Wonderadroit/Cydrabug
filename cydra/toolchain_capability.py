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


def resolve_executable(root: str | Path, name: str) -> str | None:
    """Resolve a target executable without mutating the target environment."""
    root = Path(root).resolve()
    local = root / "node_modules" / ".bin" / name
    if local.is_file():
        return str(local)
    path = shutil.which(name)
    return path


def observe_version(root: str | Path, name: str) -> str | None:
    """Observe an executable version using the target-local resolution first."""
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
