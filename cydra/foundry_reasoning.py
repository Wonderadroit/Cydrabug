"""Bridge trusted Foundry evidence into conservative experiment planning.

This module connects authenticated compiler evidence to the existing reasoning
machinery. Discovery produces candidates and symmetric competing hypotheses;
verification remains an explicit later boundary.
"""
from __future__ import annotations

from dataclasses import dataclass

from .foundry_build_info import AcceptedFoundryBuild, project_accepted_ast_evidence
from .invariants import InvariantCandidate, candidates_from_system_model
from .invariant_hypothesis_bridge import competing_hypotheses_from_candidates
from .planner import Hypothesis, Observation, Plan, choose_next_observation
from .system_model import SystemModel


@dataclass(frozen=True)
class FoundryReasoningResult:
    """Canonical evidence projection, candidates, competing hypotheses and plan."""

    evidence_edges: tuple[object, ...]
    candidates: tuple[InvariantCandidate, ...]
    hypotheses: tuple[Hypothesis, ...]
    observations: tuple[Observation, ...]
    next_plan: Plan | None


def discover_foundry_invariant_candidates(
    model: SystemModel,
    build: AcceptedFoundryBuild,
) -> FoundryReasoningResult:
    """Project an accepted Foundry build and derive the next falsifiable test.

    The accepted-build boundary remains responsible for compiler/artifact
    authenticity. Discovery confidence is never converted into belief: each
    candidate produces symmetric 0.5/0.5 holds-vs-violated hypotheses. The
    returned plan is only a plan; it carries no execution authority.
    """
    evidence_edges = tuple(project_accepted_ast_evidence(model, build))
    candidates = tuple(candidates_from_system_model(model))
    hypotheses, observations = competing_hypotheses_from_candidates(list(candidates))
    next_plan = choose_next_observation(hypotheses, observations)
    return FoundryReasoningResult(
        evidence_edges=evidence_edges,
        candidates=candidates,
        hypotheses=tuple(hypotheses),
        observations=tuple(observations),
        next_plan=next_plan,
    )
