"""Small operator-facing entry point for CYDRA environment verification."""
from __future__ import annotations

import argparse

from .ens_environment import authoritative_requirements as ens_requirements
from .runtime import detect_runtime, format_report as format_runtime
from .target_environment import (
    TargetRequirement,
    format_report as format_target,
    verify_requirements,
)


_PROFILES = {
    "ens": ens_requirements,
}


def _requirements_for_profile(profile: str | None) -> tuple[TargetRequirement, ...] | None:
    if profile is None:
        return None
    try:
        provider = _PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"unknown target profile: {profile}") from exc
    return provider()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cydra-doctor")
    parser.add_argument("--target", help="local target checkout to inspect after intake")
    parser.add_argument(
        "--target-profile",
        choices=tuple(_PROFILES),
        help="authoritative target profile selected by intake",
    )
    args = parser.parse_args(argv)

    runtime = detect_runtime()
    print(format_runtime(runtime))
    if not runtime.ready:
        return 2

    if args.target:
        requirements = _requirements_for_profile(args.target_profile)
        target = verify_requirements(args.target, requirements)
        print(format_target(target))
        return 0 if target.ready else 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
