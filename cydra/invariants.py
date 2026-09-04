"""Invariant candidates and evidence-bound verification.

Candidates are observations about implementation relationships, not vulnerability
claims. Verification preserves explicit support/contradiction and never resolves
an invariant from confidence alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .system_model import SystemModel


class InvariantStatus(str, Enum):
    ASSERTED = "asserted"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class VerificationState(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"


class VerificationRole(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class Invariant:
    invariant_id: str
    statement: str
    status: InvariantStatus = InvariantStatus.UNKNOWN
    source_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("statement must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class InvariantCandidate:
    candidate_id: str
    statement: str
    source_ids: tuple[str, ...]
    confidence: float
    evidence_count: int
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("statement must not be empty")
        if not self.source_ids:
            raise ValueError("candidate requires at least one source")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")


@dataclass(frozen=True)
class VerificationEvidence:
    evidence_id: str
    role: VerificationRole
    confidence: float = 1.0
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class CandidateVerification:
    candidate_id: str
    state: VerificationState
    evidence_ids: tuple[str, ...]
    supporting_ids: tuple[str, ...]
    contradicting_ids: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        evidence = set(self.evidence_ids)
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must not be empty")
        if not set(self.supporting_ids).issubset(evidence):
            raise ValueError("supporting evidence IDs must be part of evidence_ids")
        if not set(self.contradicting_ids).issubset(evidence):
            raise ValueError("contradicting evidence IDs must be part of evidence_ids")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.state == VerificationState.SUPPORTED and not self.supporting_ids:
            raise ValueError("supported verification requires supporting evidence")
        if self.state == VerificationState.CONTRADICTED and not self.contradicting_ids:
            raise ValueError("contradicted verification requires contradicting evidence")
        if self.state == VerificationState.UNRESOLVED and (self.supporting_ids or self.contradicting_ids):
            raise ValueError("unresolved verification cannot contain supporting or contradicting evidence")


@dataclass
class InvariantRegistry:
    invariants: dict[str, Invariant] = field(default_factory=dict)

    def add(self, invariant: Invariant) -> None:
        if invariant.invariant_id in self.invariants:
            raise ValueError(f"duplicate invariant: {invariant.invariant_id}")
        self.invariants[invariant.invariant_id] = invariant

    def get(self, invariant_id: str) -> Invariant | None:
        return self.invariants.get(invariant_id)

    def by_status(self, status: InvariantStatus) -> list[Invariant]:
        return [item for item in self.invariants.values() if item.status == status]


def _source(edge) -> str:
    return f"{edge.attributes.get('provenance', '')}:{edge.attributes.get('ast_node_id', 'unknown')}"


def _candidate(edge, statement: str, category: str, evidence_count: int = 1, source_ids=None, **metadata):
    return InvariantCandidate(
        candidate_id=f"candidate:{edge.source}:{edge.relation}:{edge.target}:{edge.attributes.get('ast_node_id', 'unknown')}",
        statement=statement,
        source_ids=tuple(source_ids or (_source(edge),)),
        confidence=float(edge.attributes.get("confidence", 0.0)),
        evidence_count=evidence_count,
        metadata={"category": category, "relation": edge.relation, **metadata},
    )


def candidates_from_system_model(model: SystemModel) -> tuple[InvariantCandidate, ...]:
    """Generate conservative candidates from evidence-backed canonical edges."""
    candidates: list[InvariantCandidate] = []
    edges = sorted(model.edges, key=lambda e: (e.source, e.relation, e.target, str(e.attributes.get("ast_node_id", ""))))
    for edge in edges:
        if not edge.attributes.get("evidence_backed") or not edge.attributes.get("candidate"):
            continue
        source = model.nodes.get(edge.source)
        target = model.nodes.get(edge.target)
        if source is None or target is None or not edge.attributes.get("provenance"):
            continue
        if edge.relation == "precondition":
            candidates.append(_candidate(edge, f"successful execution of {source.label} requires {target.label}", "precondition"))
        elif edge.relation == "assertion":
            candidates.append(_candidate(edge, f"execution of {source.label} asserts {target.label}", "assertion"))
        elif edge.relation == "transition_expression":
            expression = edge.attributes.get("expression")
            if not isinstance(expression, str) or not expression:
                continue
            candidates.append(_candidate(edge, f"execution of {source.label} updates {target.label} using {expression}", "state_transition_expression", operation=edge.attributes.get("operation"), expression=expression, rhs_expression=edge.attributes.get("rhs_expression"), dependency_ids=edge.attributes.get("dependency_ids", [])))

    transitions: dict[str, list] = {}
    for edge in edges:
        if edge.relation == "transition_expression" and edge.attributes.get("evidence_backed") and edge.attributes.get("candidate"):
            transitions.setdefault(edge.target, []).append(edge)
    for state_id, group in sorted(transitions.items()):
        functions = sorted({edge.source for edge in group})
        if len(functions) < 2:
            continue
        state = model.nodes.get(state_id)
        if state is None:
            continue
        sources = tuple(_source(edge) for edge in group)
        confidence = min(float(edge.attributes.get("confidence", 0.0)) for edge in group)
        cid = "candidate:cross-function-state-consistency:" + state_id + ":" + ":".join(functions)
        candidates.append(InvariantCandidate(cid, f"updates to shared state {state.label} across {len(functions)} functions must preserve a coherent state relationship", sources, confidence, len(group), {"category": "cross_function_state_consistency", "shared_state": state_id, "function_ids": functions}))

    for function_id, function in sorted(model.nodes.items()):
        if function.kind != "function":
            continue
        reads = [e for e in edges if e.source == function_id and e.relation == "reads" and e.attributes.get("evidence_backed") and e.attributes.get("candidate")]
        writes = [e for e in edges if e.source == function_id and e.relation == "writes" and e.attributes.get("evidence_backed") and e.attributes.get("candidate")]
        for read in reads:
            for write in writes:
                if read.target == write.target or read.target not in model.nodes or write.target not in model.nodes:
                    continue
                rnode, wnode = model.nodes[read.target], model.nodes[write.target]
                cid = f"candidate:state-dependency:{function_id}:reads:{read.target}:writes:{write.target}"
                candidates.append(InvariantCandidate(cid, f"execution of {function.label} changes {wnode.label} using information read from {rnode.label}", (_source(read), _source(write)), min(float(read.attributes.get("confidence", 0.0)), float(write.attributes.get("confidence", 0.0))), 2, {"category": "state_dependency_transition", "source_function": function_id, "read_state": read.target, "written_state": write.target}))

        obligations = [e for e in edges if e.source == function_id and e.relation in {"precondition", "assertion"} and e.attributes.get("evidence_backed") and e.attributes.get("candidate")]
        for obligation in obligations:
            predicate = model.nodes.get(obligation.target)
            if predicate is None:
                continue
            for write in writes:
                state = model.nodes.get(write.target)
                if state is None:
                    continue
                cid = f"candidate:transition-obligation:{function_id}:guard:{obligation.target}:write:{write.target}"
                candidates.append(InvariantCandidate(cid, f"execution of {function.label} under {predicate.label} has an evidenced transition affecting {state.label}", (_source(obligation), _source(write)), min(float(obligation.attributes.get("confidence", 0.0)), float(write.attributes.get("confidence", 0.0))), 2, {"category": "transition_obligation", "source_function": function_id, "guard": obligation.target, "written_state": write.target}))
    return tuple(candidates)
