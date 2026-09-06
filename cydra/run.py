"""Top-level CYDRA run entry point.

CYDRA advances one verified phase at a time. Phase 0 acquires the authoritative
program contract. Phase 1 classifies discovered project resources using
authoritative scope evidence and produces target acquisition candidates. Neither
phase clones, builds, tests, or grants authorization.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

from .live_contest import LiveContestAcquisition, acquire_live_contest
from .target_acquisition import TargetAcquisitionPlan, plan_target_acquisition


class RunBlocked(RuntimeError):
    """Raised when the current phase cannot safely advance."""


def canonicalize_immunefi_locator(locator: str) -> str:
    """Normalize an Immunefi program URL to the canonical information page."""
    parsed = urlparse(locator.strip())
    if parsed.scheme != "https" or parsed.hostname != "immunefi.com":
        raise ValueError("CYDRA requires an HTTPS Immunefi program URL")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] not in {"bug-bounty", "audit-competition"}:
        raise ValueError("URL is not a supported Immunefi program URL")
    return f"https://immunefi.com/{parts[0]}/{parts[1]}/information/"


def _acquire_phase_zero(locator: str, receipt_path: str | Path) -> LiveContestAcquisition:
    canonical = canonicalize_immunefi_locator(locator)
    result = acquire_live_contest(canonical, receipt_path=receipt_path)
    if not result.contract.ready_for_active_testing:
        raise RunBlocked("program intake is incomplete; required program resources remain unresolved")
    return result


def run(locator: str, *, receipt_path: str | Path = "evidence/live-contest.json") -> LiveContestAcquisition:
    """Execute Phase 0 only."""
    return _acquire_phase_zero(locator, receipt_path)


def run_phase_one(
    locator: str,
    *,
    receipt_path: str | Path = "evidence/live-contest.json",
) -> TargetAcquisitionPlan:
    """Execute Phase 1: classify target resources from authoritative scope evidence."""
    result = _acquire_phase_zero(locator, receipt_path)
    plan = plan_target_acquisition(result)
    if not plan.in_scope_candidates:
        raise RunBlocked("target/resource acquisition found no repository covered by authoritative scope evidence")
    return plan


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cydra-run",
        description="Run CYDRA from an Immunefi program URL, one verified phase at a time.",
    )
    parser.add_argument("locator", help="Immunefi program URL")
    parser.add_argument("--phase", type=int, choices=(0, 1), default=0)
    parser.add_argument("--receipt", default="evidence/live-contest.json")
    args = parser.parse_args(argv)

    try:
        if args.phase == 0:
            result = run(args.locator, receipt_path=args.receipt)
            print("CYDRA RUN: PHASE 0 COMPLETE")
            print(f"program: {result.contract.display_name}")
            print(f"contract fingerprint: {result.contract.fingerprint}")
            print(f"acquired pages: {len(result.acquired)}")
            print(f"discovered resources: {len(result.discovered)}")
            print(f"graph resources: {len(result.graph)}")
            print(f"advertised revision: {result.identity_evidence.advertised_revision if result.identity_evidence else None}")
            print("next phase: target/resource acquisition")
            print(f"receipt: {Path(args.receipt).resolve()}")
        else:
            plan = run_phase_one(args.locator, receipt_path=args.receipt)
            print("CYDRA RUN: PHASE 1 COMPLETE")
            print(f"program: {plan.program_id}")
            print(f"in-scope target candidates: {len(plan.in_scope_candidates)}")
            print(f"unresolved resources: {len(plan.unresolved_resources)}")
            for candidate in plan.in_scope_candidates:
                print(f"target: {candidate.locator}")
                print(f"scope evidence: {', '.join(candidate.matched_hints)}")
            print("next phase: source identity")
            print(f"phase-0 receipt: {Path(args.receipt).resolve()}")
    except RunBlocked as exc:
        print(f"CYDRA RUN: BLOCKED: {exc}")
        return 3
    except Exception as exc:
        print(f"CYDRA RUN: ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["RunBlocked", "canonicalize_immunefi_locator", "run", "run_phase_one"]
