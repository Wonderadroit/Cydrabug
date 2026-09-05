"""CYDRA host-to-Ubuntu bootstrap for the first supported production runtime.

This module is intentionally explicit: it may inspect the host, verify that the
named PRoot-Distro container exists, and launch CYDRA inside it. Installation of
CYDRA's own base packages is opt-in; target-supplied software is never installed
by this module.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from typing import Sequence

DEFAULT_CONTAINER = "ubuntu"
GUEST_WORKSPACE = "/workspace/cydrabug"
BASE_PACKAGES = ("python3", "python3-venv", "git", "ca-certificates")


@dataclass(frozen=True)
class BootstrapPlan:
    container: str
    repository: Path
    guest_repository: str
    shared_home: bool
    command: tuple[str, ...]


def _require_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"required host command not found: {name}")
    return executable


def _container_exists(container: str) -> bool:
    """Determine whether the named PRoot-Distro container is installed."""
    _require_executable("proot-distro")
    result = subprocess.run(
        ["proot-distro", "list", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False

    # PRoot-Distro marks the active/default installed distribution with ``*``
    # in some versions even in quiet output. Treat that marker as presentation,
    # not part of the container identity.
    installed = {
        line.strip().lstrip("*").strip()
        for line in result.stdout.splitlines()
        if line.strip()
    }
    return container in installed


def build_plan(
    repository: str | os.PathLike[str],
    *,
    container: str = DEFAULT_CONTAINER,
    command: Sequence[str] = ("python3", "-m", "cydra.doctor"),
) -> BootstrapPlan:
    """Build a deterministic host-side PRoot launch plan without executing it.

    With ``--shared-home``, PRoot-Distro exposes the host home at its original
    absolute path. It does not remap that path to ``/root``. Preserve the
    absolute repository path for repositories under the host home so the plan
    matches the actual supported runtime topology.
    """
    repo = Path(repository).expanduser().resolve()
    if not repo.is_dir():
        raise ValueError(f"repository directory does not exist: {repo}")

    home = Path.home().resolve()
    try:
        repo.relative_to(home)
    except ValueError:
        guest_repository = GUEST_WORKSPACE
        bind = f"{repo}:{guest_repository}"
        launch = (
            "proot-distro",
            "login",
            container,
            "--bind",
            bind,
            "--work-dir",
            guest_repository,
            "--",
            *tuple(command),
        )
        return BootstrapPlan(container, repo, guest_repository, False, launch)

    guest_repository = repo.as_posix()
    launch = (
        "proot-distro",
        "login",
        container,
        "--shared-home",
        "--work-dir",
        guest_repository,
        "--",
        *tuple(command),
    )
    return BootstrapPlan(container, repo, guest_repository, True, launch)


def verify_host(container: str = DEFAULT_CONTAINER) -> tuple[bool, str]:
    """Verify the host launcher and named PRoot-Distro container installation."""
    _require_executable("proot-distro")
    if not _container_exists(container):
        return False, f"PRoot-Distro container not installed: {container}"
    return True, f"PRoot-Distro container installed: {container}"


def run_plan(plan: BootstrapPlan) -> int:
    """Execute an already-constructed explicit launch plan."""
    return subprocess.run(list(plan.command), check=False).returncode


def install_base(container: str = DEFAULT_CONTAINER) -> int:
    """Install only CYDRA-owned base prerequisites after explicit operator request."""
    ok, reason = verify_host(container)
    if not ok:
        raise RuntimeError(reason)
    command = (
        "proot-distro",
        "login",
        container,
        "--",
        "apt-get",
        "update",
    )
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        return result.returncode
    return subprocess.run(
        (
            "proot-distro",
            "login",
            container,
            "--",
            "apt-get",
            "install",
            "-y",
            *BASE_PACKAGES,
        ),
        check=False,
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cydra-bootstrap")
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--repository", default=str(Path.cwd()))
    parser.add_argument("--status", action="store_true", help="verify the host launcher and container")
    parser.add_argument("--doctor", action="store_true", help="run CYDRA doctor inside the container")
    parser.add_argument("--shell", action="store_true", help="open a shell in the CYDRA workspace inside the container")
    parser.add_argument("--install-base", action="store_true", help="explicitly install CYDRA-owned base packages in the container")
    args = parser.parse_args(argv)

    if args.install_base:
        return install_base(args.container)

    ok, reason = verify_host(args.container)
    print(reason)
    if not ok:
        return 2

    command = ("python3", "-m", "cydra.doctor") if args.doctor else ("bash",) if args.shell else ("python3", "-m", "cydra.doctor")
    plan = build_plan(args.repository, container=args.container, command=command)
    if args.status:
        print(f"repository: {plan.repository}")
        print(f"guest repository: {plan.guest_repository}")
        print(f"shared home: {plan.shared_home}")
        print("launch:", " ".join(plan.command))
        return 0
    return run_plan(plan)


if __name__ == "__main__":
    raise SystemExit(main())