"""Fail-closed workspace boundary for blind historical evaluations.

The workspace is an allowlist projection of a pinned checkout.  It never reads
historical reports and refuses to materialize anything outside the declared
blind input set.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import subprocess


@dataclass(frozen=True)
class HistoricalBenchmarkSpec:
    evaluation_id: str
    repository: str
    revision: str
    allowed_paths: tuple[str, ...] = ("README.md", "foundry.toml", "src")
    excluded_names: tuple[str, ...] = (
        "reports", "findings", "writeups", "leaderboard", "known-issues",
    )


@dataclass(frozen=True)
class BlindWorkspace:
    root: str
    revision: str
    input_fingerprint: str
    files: tuple[str, ...]


def arbitration_boost_2024() -> HistoricalBenchmarkSpec:
    return HistoricalBenchmarkSpec(
        "eval-immunefi-arbitration-2024",
        "immunefi-team/vaults",
        "49c1de26cda19c9e8a4aa311ba3b0dc864f34a25",
    )


def _git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
        text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("historical source must be a git checkout")
    return result.stdout.strip()


def _allowed(path: PurePosixPath, spec: HistoricalBenchmarkSpec) -> bool:
    text = path.as_posix()
    return any(text == p or text.startswith(p.rstrip("/") + "/") for p in spec.allowed_paths)


def materialize_blind_workspace(
    checkout: str | Path,
    destination: str | Path,
    spec: HistoricalBenchmarkSpec,
) -> BlindWorkspace:
    source = Path(checkout).resolve()
    destination = Path(destination).resolve()
    if not source.is_dir() or not (source / ".git").exists():
        raise ValueError("checkout must be a git working tree")
    actual = _git_revision(source)
    if actual != spec.revision:
        raise RuntimeError(
            f"historical revision mismatch: expected {spec.revision}, got {actual}"
        )
    if destination == source or source in destination.parents:
        raise ValueError("destination must not be inside the source checkout")

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    selected: list[str] = []
    for relative in sorted(spec.allowed_paths):
        candidate = source / relative
        if not candidate.exists():
            raise RuntimeError(f"required blind input is missing: {relative}")
        items = [candidate] if candidate.is_file() else sorted(p for p in candidate.rglob("*") if p.is_file())
        for item in items:
            rel = item.relative_to(source).as_posix()
            if not _allowed(PurePosixPath(rel), spec):
                raise RuntimeError(f"input escaped allowlist: {rel}")
            if any(part.lower() in {x.lower() for x in spec.excluded_names} for part in PurePosixPath(rel).parts):
                raise RuntimeError(f"oracle-like input is forbidden: {rel}")
            target = destination / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            selected.append(rel)

    digest = hashlib.sha256()
    for rel in sorted(selected):
        data = (destination / rel).read_bytes()
        digest.update(rel.encode("utf-8")); digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return BlindWorkspace(str(destination), actual, digest.hexdigest(), tuple(sorted(selected)))
