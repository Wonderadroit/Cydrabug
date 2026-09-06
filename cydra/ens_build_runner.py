"""ENS-specific canonical build verification runner.

The runner executes only the commands published by the ENS contest build
instructions, records independently observed identity/toolchain/hash data, and
serializes the resulting evidence without modifying source files directly.

Dependency materialization is staged through the generic target-environment
capability boundary: bootstrap tools are verified first, the target-declared
frozen install is then executed, and materialized tools such as tsgo are verified
before the remaining canonical validation commands run.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import argparse
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
from .ens_environment import authoritative_requirements
from .ens_target import AUDITED_REVISION, DEFAULT_REVISION
from .target_environment import (
    EnvironmentPreparation,
    TargetEnvironmentReport,
    prepare_target_environment,
    verify_requirements,
)


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
BOOTSTRAP_TOOLS = frozenset(("node", "pnpm"))
MATERIALIZATION_COMMAND = ("pnpm", "install", "--frozen-lockfile")


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
    environment: TargetEnvironmentReport | None = None
    command_outputs_recorded: bool = False
    preparation: EnvironmentPreparation | None = None

    @property
    def verified(self) -> bool:
        return self.receipt.verified and all(c.returncode == 0 for c in self.commands) and bool(self.environment and self.environment.ready)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt": asdict(self.receipt),
            "commands": [
                {"command": list(c.command), "returncode": c.returncode, "status": c.status}
                for c in self.commands
            ],
            "observed_head": self.observed_head,
            "observed_tree": self.observed_tree,
            "environment": {
                "root": self.environment.root,
                "requirements": [asdict(r) for r in self.environment.requirements],
                "capabilities": [
                    {
                        "requirement": asdict(c.requirement),
                        "available": c.available,
                        "observed": c.observed,
                        "reason": c.reason,
                    }
                    for c in self.environment.capabilities
                ],
                "ready": self.environment.ready,
                "missing_required": list(self.environment.missing_required),
            } if self.environment else None,
            "preparation": {
                "bootstrap": self.preparation.bootstrap.ready,
                "materialization_command": list(self.preparation.materialization_command),
                "materialization_returncode": self.preparation.materialization_returncode,
                "materialization_status": self.preparation.materialization_status,
                "final_ready": self.preparation.final.ready,
            } if self.preparation else None,
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


def _git_blob_sha(root: Path, name: str) -> str:
    """Read the immutable Git blob identity from the observed checkout."""
    return _git(root, "rev-parse", f"HEAD:{name}")


def _tool_version(root: Path, argv: Sequence[str]) -> str:
    executable = shutil.which(argv[0])
    if executable is None:
        return ""
    result = subprocess.run(
        list(argv), cwd=root, capture_output=True, text=True, timeout=30, check=False
    )
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if result.returncode == 0 and text else ""


def preflight_ens_environment(target: str | Path) -> TargetEnvironmentReport:
    """Verify authoritative ENS build prerequisites without executing target commands."""
    return verify_requirements(target, authoritative_requirements())


def _bootstrap_requirements() -> tuple:
    return tuple(r for r in authoritative_requirements() if r.name in BOOTSTRAP_TOOLS)


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

    requirements = authoritative_requirements()
    preparation = prepare_target_environment(
        root,
        bootstrap_requirements=_bootstrap_requirements(),
        final_requirements=requirements,
        materialization_command=MATERIALIZATION_COMMAND,
        timeout=timeout_per_command,
    )
    environment = preparation.final
    observed_head = _git(root, "rev-parse", "HEAD")
    observed_tree = _git(root, "rev-parse", "HEAD^{tree}")
    worktree_clean = _git(root, "status", "--porcelain") == ""
    node_version = _tool_version(root, ("node", "--version"))
    pnpm_version = _tool_version(root, ("pnpm", "--version"))
    tsgo_version = _tool_version(root, ("tsgo", "--version"))
    hashes: Mapping[str, str] = {name: _git_blob_sha(root, name) for name in BUILD_INPUTS}

    observations: list[CommandObservation] = [
        CommandObservation(
            MATERIALIZATION_COMMAND,
            preparation.materialization_returncode,
            preparation.materialization_status,
        )
    ]
    if preparation.ready:
        for command in CANONICAL_COMMANDS[1:]:
            observation = _run(root, command, timeout_per_command)
            observations.append(observation)
            if observation.returncode != 0:
                break

    by_name = {" ".join(o.command): o.returncode for o in observations}
    receipt = build_receipt_from_observations(
        node_version=node_version,
        pnpm_version=pnpm_version,
        tsgo_version=tsgo_version,
        frozen_install_exit_code=by_name.get("pnpm install --frozen-lockfile", 127),
        check_exit_code=by_name.get("pnpm check", 127),
        manager_build_exit_code=by_name.get("pnpm build:manager", 127),
        worktree_clean=worktree_clean,
        snapshot_commit=observed_head,
        snapshot_tree=observed_tree,
        file_hashes=hashes,
    )

    run = ENSBuildRun(receipt, tuple(observations), observed_head, observed_tree, environment, preparation=preparation)
    if receipt_path is not None:
        path = Path(receipt_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run


def expected_build_inputs() -> dict[str, str]:
    """Return canonical expected Git blob identities for build inputs."""
    return {
        "package.json": ENS_PACKAGE_JSON_SHA,
        "pnpm-lock.yaml": ENS_PNPM_LOCK_SHA,
        "pnpm-workspace.yaml": ENS_PNPM_WORKSPACE_SHA,
        ".npmrc": ENS_NPMRC_SHA,
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CYDRA's fixed ENS canonical build validation suite.")
    parser.add_argument("target", help="path to the ENS source checkout")
    parser.add_argument(
        "--receipt",
        default="evidence/ens-build.json",
        help="durable JSON evidence path (default: evidence/ens-build.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="timeout in seconds per canonical command (default: 1800)",
    )
    args = parser.parse_args(argv)

    try:
        run = run_ens_build(args.target, receipt_path=args.receipt, timeout_per_command=args.timeout)
    except (OSError, ValueError) as exc:
        print(f"ENS BUILD RUN: ERROR: {exc}")
        return 2

    print(f"ENS BUILD RUN: {'VERIFIED' if run.verified else 'NOT VERIFIED'}")
    print(f"snapshot: {run.observed_head}")
    print(f"tree: {run.observed_tree}")
    print(f"environment: {'READY' if run.environment and run.environment.ready else 'BLOCKED'}")
    if run.preparation:
        print(f"PREPARATION: {'PASS' if run.preparation.materialization_returncode == 0 else 'FAIL'} {' '.join(run.preparation.materialization_command)} -> {run.preparation.materialization_status} ({run.preparation.materialization_returncode})")
    if run.environment:
        for capability in run.environment.capabilities:
            print(f"PREREQUISITE: {'PASS' if capability.available else 'FAIL'} {capability.requirement.name} [{capability.observed or 'unavailable'}] — {capability.reason}")
    print(f"receipt: {Path(args.receipt).resolve()}")
    for observation in run.commands:
        print(f"{' '.join(observation.command)} -> {observation.status} ({observation.returncode})")
    if not run.verified:
        failures = run.receipt.failure_reasons()
        for reason in failures:
            print(f"RECEIPT FAILURE: {reason}")
    return 0 if run.verified else 1


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = [
    "AUDITED_REVISION",
    "CANONICAL_COMMANDS",
    "DEFAULT_REVISION",
    "ENS_PNPM_VERSION",
    "ENSBuildRun",
    "CommandObservation",
    "expected_build_inputs",
    "preflight_ens_environment",
    "run_ens_build",
]
