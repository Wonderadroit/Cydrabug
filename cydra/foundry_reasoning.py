"""Bridge trusted Foundry evidence into conservative invariant discovery.

This module deliberately stops at candidate generation. Compiler-derived AST
relationships are evidence for the SystemModel; they are not security claims
and are not treated as verified invariants.
"""
from __future__ import annotations

from dataclasses import dataclass

from .foundry_build_info import AcceptedFoundryBuild, project_accepted_ast_evidence
from .invariants import InvariantCandidate, candidates_from_system_model
from .system_model import SystemModel


@dataclass(frozen=True)
class FoundryReasoningResult:
    """Canonical model projection plus conservative invariant candidates."""

    evidence_edges: tuple[object, ...]
    candidates: tuple[InvariantCandidate, ...]


def discover_foundry_invariant_candidates(
    model: SystemModel,
    build: AcceptedFoundryBuild,
) -> FoundryReasoningResult:
    """Project an accepted Foundry build and derive evidence-backed candidates.

    The accepted-build boundary remains responsible for compiler/artifact
    authenticity. This function only connects that trusted evidence to the
    existing invariant-discovery machinery. It never marks a candidate
    verified, creates a vulnerability claim, or converts discovery confidence
    into belief.
    """
    evidence_edges = tuple(project_accepted_ast_evidence(model, build))
    candidates = tuple(candidates_from_system_model(model))
    return FoundryReasoningResult(evidence_edges=evidence_edges, candidates=candidates)
