"""ENS-specific canonical build verification runner.

The runner executes only the commands published by the ENS contest build
instructions, records independently observed identity/toolchain/hash data, and
serializes the resulting evidence without modifying the target checkout.

It is intentionally not a generic command runner and does not install tools.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Mapping, Sequence

from .ens_build_identity import (
    ENS_NPMRC_SHA,
    ENS_PACKAGE_JSON_SHA,
    ENS_PNPM_LOCK_SHA,
    ENS_PNPM_VERSION,
    ENS_PNPM_WORKSPACE_SHA,
)
from .ens_build_receipt import ENSBuildReceipt, build_receipt_from_observations
from .ens_target import AUDITED_REVISION, DEFAULT_REVISION


CANONICAL_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("pnpm", "install", "--frozen-lockfile"),
    ("pnpm", "check"),
    ("pnpm", "build:manager"),
    ("pnpm", "typecheck:manager"),
    ("pnpm", "test:manager"),
    ("pnpm", "build:portal"),
    ("pnpm", "typecheck:portal"),
    ("pnpm", "test:portal"),
    ("pnpm", "test:all"),
)

# E2E is deliberately excluded: the contest requires Docker for E2E and this
# runner must report the capability boundary rather than silently pretending it ran.
REQUIRED_COMMAND_NAMES = frozenset(" ".join(c) for c in CANONICAL_COMMANDS)
BUILD_INPUTS = ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", ".npmrc")


@dataclass(frozen=True)
class CommandObservation:
    command: tuple[str, ...]
    returncode: int
    status: str


@dataclass(frozen=True)
class ENSBuildRun:
    receipt: ENSBuildReceipt
    commands: tuple[CommandObservation, ...]
    observed_head: str
    observed_tree: str
    command_outputs_recorded: bool = False

    @property
    def verified(self) -> bool:
        return self.receipt.verified and all(c.returncode == 0 for c in self.commands)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt": asdict(self.receipt),
            "commands": [
                {"command": list(c.command), "returncode": c.returncode, "status": c.status}
                for c in self.commands
            ],
            "observed_head": self.observed_head,
            "observed_tree": self.observed_tree,
            "command_outputs_recorded": self.command_outputs_recorded,
            "verified": self.verified,
        }


def _run(root: Path, argv: Sequence[str], timeout: int) -> CommandObservation:
    executable = shutil.which(argv[0])
    if executable is None:
        return CommandObservation(tuple(argv), 127, "TOOLCHAIN_UNAVAILABLE")
    try:
        result = subprocess.run(
            list(argv), cwd=root, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return CommandObservation(tuple(argv), 124, "TIMEOUT")
    return CommandObservation(tuple(argv), result.returncode, "SUCCEEDED" if result.returncode == 0 else "FAILED")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, timeout=30, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _sha256(root: Path, name: str) -> str:
    path = root / name
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tool_version(root: Path, argv: Sequence[str]) -> str:
    executable = shutil.which(argv[0])
    if executable is None:
        return ""
    result = subprocess.run(
        list(argv), cwd=root, capture_output=True, text=True, timeout=30, check=False
    )
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if result.returncode == 0 and text else ""


def run_ens_build(
    target: str | Path,
    *,
    receipt_path: str | Path | None = None,
    timeout_per_command: int = 1800,
) -> ENSBuildRun:
    """Run the fixed ENS validation suite and persist a durable evidence receipt."""
    root = Path(target).resolve()
    if not (root / ".git").exists() or not (root / "package.json").is_file():
        raise ValueError(f"not an ENS source checkout: {root}")

    observed_head = _git(root, "rev-parse", "HEAD")
    observed_tree = _git(root, "rev-parse", "HEAD^{tree}")
    worktree_clean = _git(root, "status", "--porcelain") == ""
    node_version = _tool_version(root, ("node", "--version"))
    pnpm_version = _tool_version(root, ("pnpm", "--version"))
    hashes: Mapping[str, str] = {name: _sha256(root, name) for name in BUILD_INPUTS}

    observations: list[CommandObservation] = []
    for command in CANONICAL_COMMANDS:
        observation = _run(root, command, timeout_per_command)
        observations.append(observation)
        if observation.returncode != 0:
            break

    by_name = {" ".join(o.command): o.returncode for o in observations}
    receipt = build_receipt_from_observations(
        node_version=node_version,
        pnpm_version=pnpm_version,
        frozen_install_exit_code=by_name.get("pnpm install --frozen-lockfile", 127),
        check_exit_code=by_name.get("pnpm check", 127),
        manager_build_exit_code=by_name.get("pnpm build:manager", 127),
        worktree_clean=worktree_clean,
        snapshot_commit=observed_head,
        snapshot_tree=observed_tree,
        file_hashes=hashes,
    )

    run = ENSBuildRun(receipt, tuple(observations), observed_head, observed_tree)
    if receipt_path is not None:
        path = Path(receipt_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run


def expected_build_inputs() -> dict[str, str]:
    """Return canonical expected hashes for the four immutable build inputs."""
    return {
        "package.json": ENS_PACKAGE_JSON_SHA,
        "pnpm-lock.yaml": ENS_PNPM_LOCK_SHA,
        "pnpm-workspace.yaml": ENS_PNPM_WORKSPACE_SHA,
        ".npmrc": ENS_NPMRC_SHA,
    }


__all__ = [
    "AUDITED_REVISION",
    "CANONICAL_COMMANDS",
    "DEFAULT_REVISION",
    "ENS_PNPM_VERSION",
    "ENSBuildRun",
    "CommandObservation",
    "expected_build_inputs",
    "run_ens_build",
]
