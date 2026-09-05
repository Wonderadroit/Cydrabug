"""Small operator-facing entry point for CYDRA environment verification."""
from __future__ import annotations

import argparse

from .runtime import detect_runtime, format_report as format_runtime
from .target_environment import format_report as format_target, verify_requirements


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cydra-doctor")
    parser.add_argument("--target", help="local target checkout to inspect after intake")
    args = parser.parse_args(argv)

    runtime = detect_runtime()
    print(format_runtime(runtime))
    if not runtime.ready:
        return 2

    if args.target:
        target = verify_requirements(args.target)
        print(format_target(target))
        return 0 if target.ready else 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
