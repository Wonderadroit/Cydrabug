"""Top-level CYDRA run entry point.

Project #1 is intentionally advanced one phase at a time. This module owns
only the first boundary: an operator supplies an Immunefi program URL and
CYDRA passively acquires the authoritative program contract. It does not
invent authorization, acquire a repository, build the target, or begin
security reasoning before the intake gate is satisfied.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

from .live_contest import LiveContestAcquisition, acquire_live_contest


class RunBlocked(RuntimeError):
    """Raised when the current phase cannot safely advance."""


def canonicalize_immunefi_locator(locator: str) -> str:
    """Normalize an Immunefi program URL to the canonical information page.

    The caller may provide the program root, information, scope, or resources
    page. We deliberately refuse non-Immunefi hosts and unrelated paths.
    """
    parsed = urlparse(locator.strip())
    if parsed.scheme != "https" or parsed.hostname != "immunefi.com":
        raise ValueError("CYDRA requires an HTTPS Immunefi program URL")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] not in {"bug-bounty", "audit-competition"}:
        raise ValueError("URL is not a supported Immunefi program URL")

    return f"https://immunefi.com/{parts[0]}/{parts[1]}/information/"


def run(locator: str, *, receipt_path: str | Path = "evidence/live-contest.json") -> LiveContestAcquisition:
    """Execute the current CYDRA phase and stop at its boundary.

    Phase 0 is program intake. Later phases must be added explicitly rather
    than silently performed here. This makes a failed phase reproducible and
    prevents operator-provided shortcuts from bypassing CYDRA's gates.
    """
    canonical = canonicalize_immunefi_locator(locator)
    result = acquire_live_contest(canonical, receipt_path=receipt_path)

    if not result.contract.ready_for_active_testing:
        raise RunBlocked(
            "program intake is incomplete; required program resources remain unresolved"
        )

    # The repository is intentionally not acquired here. A discovered project
    # resource is contextual evidence until source identity and scope are
    # independently verified by the next phase.
    return result


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cydra-run",
        description="Run CYDRA from an Immunefi program URL, one verified phase at a time.",
    )
    parser.add_argument("locator", help="Immunefi program URL")
    parser.add_argument("--receipt", default="evidence/live-contest.json")
    args = parser.parse_args(argv)

    try:
        result = run(args.locator, receipt_path=args.receipt)
    except RunBlocked as exc:
        print(f"CYDRA RUN: BLOCKED: {exc}")
        return 3
    except Exception as exc:
        print(f"CYDRA RUN: ERROR: {exc}")
        return 2

    print("CYDRA RUN: PHASE 0 COMPLETE")
    print(f"program: {result.contract.display_name}")
    print(f"contract fingerprint: {result.contract.fingerprint}")
    print(f"acquired pages: {len(result.acquired)}")
    print(f"discovered resources: {len(result.discovered)}")
    print(f"graph resources: {len(result.graph)}")
    print(f"advertised revision: {result.identity_evidence.advertised_revision if result.identity_evidence else None}")
    print("next phase: target/resource acquisition")
    print(f"receipt: {Path(args.receipt).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["RunBlocked", "canonicalize_immunefi_locator", "run"]
