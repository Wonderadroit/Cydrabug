"""Measure CYDRA's existing security-reasoning pipeline over ENS evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .foundry_reasoning import discover_foundry_invariant_candidates
from .foundry_build_info import AcceptedFoundryBuild
from .system_model import SystemModel


def _candidate_record(candidate: Any) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "statement": candidate.statement,
        "confidence": candidate.confidence,
        "metadata": dict(candidate.metadata),
    }


def _hypothesis_record(hypothesis: Any) -> dict[str, Any]:
    return {
        "hypothesis_id": hypothesis.hypothesis_id,
        "statement": hypothesis.statement,
        "belief": hypothesis.belief,
        "state": getattr(hypothesis.state, "value", str(hypothesis.state)),
    }


def _observation_record(observation: Any) -> dict[str, Any]:
    return {
        "name": observation.name,
        "outcomes": list(observation.outcomes),
        "cost": observation.cost,
        "authorized": observation.authorized,
        "domain": observation.domain,
        "discriminates_hypothesis_ids": list(observation.discriminates_hypothesis_ids),
        "target_ids": list(observation.target_ids),
        "rationale": observation.rationale,
    }


def _accepted_build_from_json(payload: dict[str, Any]) -> AcceptedFoundryBuild:
    """Rehydrate an AcceptedFoundryBuild without weakening its trust boundary."""
    if not isinstance(payload, dict):
        raise TypeError("build-info evidence must be a JSON object")
    try:
        return AcceptedFoundryBuild(**payload)
    except TypeError as exc:
        raise ValueError(
            "the supplied JSON is not a serialized AcceptedFoundryBuild; "
            "run the existing Foundry build-info acceptance pipeline first"
        ) from exc


def run_experiment(build_path: str | Path) -> dict[str, Any]:
    """Run the existing reasoning chain against a previously accepted build."""
    path = Path(build_path).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    build = _accepted_build_from_json(payload)
    model = SystemModel()
    result = discover_foundry_invariant_candidates(model, build)

    categories: dict[str, int] = {}
    for candidate in result.candidates:
        category = str(candidate.metadata.get("category", "unknown"))
        categories[category] = categories.get(category, 0) + 1

    return {
        "build": {
            "revision": getattr(build, "revision", ""),
            "build_info_sha256": getattr(build, "build_info_sha256", ""),
            "compiler_version": getattr(build, "compiler_version", ""),
            "source_count": len(getattr(build, "sources", {})),
        },
        "system_model": {
            "nodes": len(model.nodes),
            "edges": len(model.edges),
            "evidence_edges": len(result.evidence_edges),
        },
        "candidates": {
            "total": len(result.candidates),
            "categories": categories,
            "items": [_candidate_record(item) for item in result.candidates],
        },
        "hypotheses": {
            "total": len(result.hypotheses),
            "items": [_hypothesis_record(item) for item in result.hypotheses],
        },
        "planner": {
            "observations": len(result.observations),
            "items": [_observation_record(item) for item in result.observations],
            "next_plan": None if result.next_plan is None else {
                "observation_name": result.next_plan.observation_name,
                "expected_information_gain": result.next_plan.expected_information_gain,
                "cost": result.next_plan.cost,
                "gain_per_cost": result.next_plan.gain_per_cost,
                "execution_id": result.next_plan.execution_id,
                "execution_request_digest": result.next_plan.execution_request_digest,
            },
        },
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description="Measure CYDRA reasoning over accepted Foundry evidence.")
    parser.add_argument("build", help="serialized AcceptedFoundryBuild JSON")
    parser.add_argument("--output", help="optional JSON report path")
    args = parser.parse_args()
    try:
        report = run_experiment(args.build)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ENS REASONING EXPERIMENT: ERROR: {exc}")
        return 2
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
