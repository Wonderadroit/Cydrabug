"""Translate verified invariants into explicit, falsifiable hypotheses."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .invariants import InvariantCandidate, VerificationState
from .planner import Hypothesis, Observation
from .system_model import Edge, Node, SystemModel


@dataclass(frozen=True)
class InvariantHypothesis:
    hypothesis_id: str
    invariant_id: str
    statement: str
    confidence: float


def _canonical_verified_invariant(model: SystemModel, candidate: InvariantCandidate) -> Node | None:
    node = model.nodes.get(candidate.candidate_id)
    if node is None or node.kind != "invariant" or node.label != candidate.statement:
        return None
    if node.attributes.get("verification_state") != VerificationState.SUPPORTED.value:
        return None
    supporting_ids = tuple(node.attributes.get("supporting_evidence_ids", ()))
    if not supporting_ids:
        return None
    verified_edges = {
        edge.target for edge in model.edges
        if edge.source == candidate.candidate_id and edge.relation == "verified_by"
        and edge.target in model.nodes and model.nodes[edge.target].kind == "evidence"
    }
    expected_edges = {item if item.startswith("evidence:") else f"evidence:{item}" for item in supporting_ids}
    if not expected_edges.issubset(verified_edges):
        return None
    return node


def hypotheses_from_verified_invariants(model: SystemModel, candidates: list[InvariantCandidate]) -> list[InvariantHypothesis]:
    results = []
    for candidate in candidates:
        node = _canonical_verified_invariant(model, candidate)
        if node is not None:
            results.append(InvariantHypothesis(
                f"hypothesis:{candidate.candidate_id}", candidate.candidate_id,
                f"Violation of invariant: {candidate.statement}",
                float(node.attributes.get("verification_confidence", candidate.confidence)),
            ))
    return results


def planner_hypotheses_from_verified_invariants(
    model: SystemModel,
    candidates: list[InvariantCandidate],
    explicit_hypotheses: Mapping[str, Hypothesis],
) -> list[tuple[InvariantHypothesis, Hypothesis]]:
    verified = hypotheses_from_verified_invariants(model, candidates)
    return [
        (InvariantHypothesis(f"hypothesis:{hypothesis.name}", item.invariant_id, item.statement, item.confidence), hypothesis)
        for item in verified if (hypothesis := explicit_hypotheses.get(item.invariant_id)) is not None
    ]


def competing_hypotheses_from_candidates(
    candidates: list[InvariantCandidate], *, max_candidates: int | None = None,
) -> tuple[list[Hypothesis], list[Observation]]:
    """Create symmetric, bounded hypotheses and observations for each candidate.

    Discovery confidence is evidence quality, not truth probability. Both competing
    explanations therefore begin at 0.5 and must be separated by observation.
    """
    if max_candidates is not None and max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    active = candidates if max_candidates is None else candidates[:max_candidates]
    hypotheses, observations = [], []
    for candidate in active:
        base = candidate.candidate_id
        holds = Hypothesis(
            name=f"invariant-holds:{base}", probability=0.5,
            predictions={f"verify-invariant:{base}": {"INVARIANT_PRESERVED": .85, "INVARIANT_VIOLATED": .10, "INCONCLUSIVE": .05}},
        )
        violated = Hypothesis(
            name=f"invariant-violated:{base}", probability=0.5,
            predictions={f"verify-invariant:{base}": {"INVARIANT_PRESERVED": .10, "INVARIANT_VIOLATED": .85, "INCONCLUSIVE": .05}},
        )
        target_ids = tuple(
            value for key in ("source_function", "written_state", "predicate_node", "ast_node_id", "precondition_relation")
            for value in (candidate.metadata.get(key),)
            if isinstance(value, str) and value
        )
        observations.append(Observation(
            name=f"verify-invariant:{base}",
            outcomes=["INVARIANT_PRESERVED", "INVARIANT_VIOLATED", "INCONCLUSIVE"],
            cost=1.0, authorized=True, domain="target",
            discriminates_hypothesis_ids=(holds.hypothesis_id, violated.hypothesis_id),
            target_ids=target_ids,
            rationale=("Verify the discovered invariant at its evidence-backed source and "
                       "state-transition target; discovery confidence describes evidence quality, not truth."),
        ))
        hypotheses.extend((holds, violated))
    return hypotheses, observations


def persist_invariant_hypotheses(model: SystemModel, hypotheses: list[InvariantHypothesis]) -> None:
    for hypothesis in hypotheses:
        invariant = model.nodes.get(hypothesis.invariant_id)
        if invariant is None or invariant.kind != "invariant":
            raise KeyError(f"invariant node missing: {hypothesis.invariant_id}")
        if invariant.attributes.get("verification_state") != VerificationState.SUPPORTED.value:
            raise ValueError("invariant must be explicitly supported before hypothesis bridging")
        expected = f"Violation of invariant: {invariant.label}"
        if hypothesis.statement != expected:
            raise ValueError("hypothesis statement is not bound to the canonical invariant")
        supporting_ids = tuple(invariant.attributes.get("supporting_evidence_ids", ()))
        if not supporting_ids:
            raise ValueError("supported invariant is missing supporting evidence IDs")
        verified_edges = {edge.target for edge in model.edges if edge.source == hypothesis.invariant_id and edge.relation == "verified_by"}
        expected_edges = {item if item.startswith("evidence:") else f"evidence:{item}" for item in supporting_ids}
        if not expected_edges.issubset(verified_edges):
            raise ValueError("supported invariant is missing explicit verification evidence edges")
        node = model.nodes.get(hypothesis.hypothesis_id)
        if node is None:
            model.add_node(Node(hypothesis.hypothesis_id, "hypothesis", hypothesis.statement, {
                "invariant_id": hypothesis.invariant_id, "confidence": hypothesis.confidence, "provenance": "verified_invariant"}))
        elif node.kind != "hypothesis":
            raise ValueError(f"hypothesis ID conflicts with non-hypothesis node: {hypothesis.hypothesis_id}")
        elif node.label != hypothesis.statement:
            if not {"probability", "predictions", "state", "subject_id"}.issubset(node.attributes):
                raise ValueError("existing hypothesis label conflicts with canonical invariant bridge")
            model.update_node_attributes(node.node_id, {"invariant_id": hypothesis.invariant_id, "invariant_statement": hypothesis.statement, "invariant_confidence": hypothesis.confidence, "provenance": "verified_invariant"})
        else:
            model.update_node_attributes(node.node_id, {"invariant_id": hypothesis.invariant_id, "invariant_statement": hypothesis.statement, "invariant_confidence": hypothesis.confidence, "provenance": "verified_invariant"})
        model.add_edge(Edge(hypothesis.invariant_id, "informs", hypothesis.hypothesis_id, {"provenance": "verified_invariant", "rationale": "supported invariant bridge"}))
