"""Top-level CYDRA run entry point.

CYDRA advances one verified phase at a time. Phase 0 acquires the authoritative
program contract. Phase 1 classifies discovered project resources using
authoritative scope evidence. Phase 2 acquires those authoritative repositories
and verifies exact source identity before later build/observation phases.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

from .live_contest import LiveContestAcquisition, acquire_live_contest
from .source_identity import (
    SourceIdentityReceipt,
    acquire_and_verify_source,
    repository_locator,
    target_path,
)
from .target_acquisition import TargetAcquisitionPlan, plan_target_acquisition


class RunBlocked(RuntimeError):
    """Raised when the current phase cannot safely advance."""


@dataclass(frozen=True)
class SourceIdentityPlan:
    program_id: str
    advertised_revision: str
    receipts: tuple[SourceIdentityReceipt, ...]

    @property
    def ready_for_next_phase(self) -> bool:
        return bool(self.receipts) and all(item.verified for item in self.receipts)


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
    if plan.unresolved_assets:
        names = ", ".join(asset.asset_name for asset in plan.unresolved_assets)
        raise RunBlocked("authoritative scope assets remain unresolved: " + names)
    return plan


def run_phase_two(
    locator: str,
    *,
    receipt_path: str | Path = "evidence/live-contest.json",
    workspace: str | Path = "evidence/source",
) -> SourceIdentityPlan:
    """Execute Phase 2: acquire and verify authoritative source identity."""
    result = _acquire_phase_zero(locator, receipt_path)
    plan = plan_target_acquisition(result)
    if not plan.in_scope_candidates:
        raise RunBlocked("source identity has no authoritative target candidates")
    if plan.unresolved_assets:
        names = ", ".join(asset.asset_name for asset in plan.unresolved_assets)
        raise RunBlocked("authoritative scope assets remain unresolved: " + names)

    advertised = result.identity_evidence.advertised_revision if result.identity_evidence else None
    if not advertised:
        raise RunBlocked("authoritative audited revision is unresolved")

    grouped: dict[str, list[str]] = {}
    for candidate in plan.in_scope_candidates:
        repo = repository_locator(candidate.locator)
        path = target_path(candidate.locator)
        if path:
            grouped.setdefault(repo, []).append(path)
        else:
            grouped.setdefault(repo, [])

    receipts: list[SourceIdentityReceipt] = []
    base = Path(workspace).resolve() / plan.program_id
    for index, (repo, paths) in enumerate(sorted(grouped.items())):
        checkout = base / f"repository-{index}"
        receipts.append(
            acquire_and_verify_source(
                repo,
                advertised,
                checkout,
                target_paths=tuple(sorted(set(paths))),
            )
        )

    identity_plan = SourceIdentityPlan(plan.program_id, advertised, tuple(receipts))
    if not identity_plan.ready_for_next_phase:
        failures = "; ".join(f"{item.status}: {item.reason}" for item in identity_plan.receipts)
        raise RunBlocked("source identity is not verified: " + failures)
    return identity_plan


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cydra-run",
        description="Run CYDRA from an Immunefi program URL, one verified phase at a time.",
    )
    parser.add_argument("locator", help="Immunefi program URL")
    parser.add_argument("--phase", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--receipt", default="evidence/live-contest.json")
    parser.add_argument("--workspace", default="evidence/source")
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
        elif args.phase == 1:
            plan = run_phase_one(args.locator, receipt_path=args.receipt)
            print("CYDRA RUN: PHASE 1 COMPLETE")
            print(f"program: {plan.program_id}")
            print(f"in-scope target candidates: {len(plan.in_scope_candidates)}")
            print(f"unresolved resources: {len(plan.unresolved_resources)}")
            for candidate in plan.in_scope_candidates:
                assets = ", ".join(candidate.asset_names) or "unlabeled authoritative asset"
                print(f"target: {candidate.locator}")
                print(f"asset: {assets}")
                print(f"scope evidence: {', '.join(candidate.matched_hints)}")
            print("next phase: source identity")
            print(f"phase-0 receipt: {Path(args.receipt).resolve()}")
        else:
            identity = run_phase_two(
                args.locator,
                receipt_path=args.receipt,
                workspace=args.workspace,
            )
            print("CYDRA RUN: PHASE 2 COMPLETE")
            print(f"program: {identity.program_id}")
            print(f"advertised revision: {identity.advertised_revision}")
            for receipt in identity.receipts:
                print(f"repository: {receipt.repository}")
                print(f"checkout: {receipt.checkout_path}")
                print(f"observed revision: {receipt.observed_revision}")
                print(f"status: {receipt.status}")
                print(f"target paths: {', '.join(receipt.target_paths) or '(repository root)'}")
            print("next phase: target environment")
    except RunBlocked as exc:
        print(f"CYDRA RUN: BLOCKED: {exc}")
        return 3
    except Exception as exc:
        print(f"CYDRA RUN: ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = [
    "RunBlocked",
    "SourceIdentityPlan",
    "canonicalize_immunefi_locator",
    "run",
    "run_phase_one",
    "run_phase_two",
]
