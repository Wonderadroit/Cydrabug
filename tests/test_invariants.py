from cydra.invariants import (
    CandidateVerification,
    Invariant,
    InvariantRegistry,
    InvariantStatus,
    VerificationState,
    VerificationRole,
    VerificationEvidence,
    candidates_from_system_model,
)
from cydra.system_model import Edge, Node, SystemModel


def _model() -> SystemModel:
    model = SystemModel()
    model.add_node(Node("function:f", "function", "withdraw"))
    model.add_node(Node("state:a", "state_variable", "shares", {"ast_node_id": 10}))
    model.add_node(Node("state:b", "state_variable", "totalAssets", {"ast_node_id": 11}))
    model.add_node(Node("predicate:p", "data_flow", "caller_is_owner"))
    evidence = {"evidence_backed": True, "candidate": True, "provenance": "compiler.json", "confidence": 0.8, "ast_node_id": 20}
    model.add_edge(Edge("function:f", "reads", "state:b", {**evidence, "ast_node_id": 21}))
    model.add_edge(Edge("function:f", "writes", "state:a", {**evidence, "ast_node_id": 22}))
    model.add_edge(Edge("function:f", "precondition", "predicate:p", {**evidence, "ast_node_id": 23}))
    model.add_edge(Edge("function:f", "transition_expression", "state:a", {**evidence, "ast_node_id": 24, "expression": "shares - amount", "operation": "sub"}))
    return model


def test_candidates_require_evidence_backed_edges():
    model = _model()
    model.add_edge(Edge("function:f", "writes", "state:b", {"candidate": True, "provenance": "compiler.json", "confidence": 0.9, "ast_node_id": 99}))
    candidates = candidates_from_system_model(model)
    assert any(item.metadata["category"] == "precondition" for item in candidates)
    assert any(item.metadata["category"] == "state_transition_expression" for item in candidates)
    assert any(item.metadata["category"] == "state_dependency_transition" for item in candidates)
    assert all(item.source_ids for item in candidates)


def test_confidence_does_not_resolve_verification_state():
    candidate = Invariant("inv:1", "withdraw preserves accounting", confidence=0.99)
    assert candidate.status is InvariantStatus.UNKNOWN
    unresolved = CandidateVerification("candidate:1", VerificationState.UNRESOLVED, (), (), (), 0.99)
    assert unresolved.state is VerificationState.UNRESOLVED


def test_verification_requires_explicit_polarity():
    evidence = VerificationEvidence("obs:1", VerificationRole.SUPPORTS, 0.9)
    assert evidence.role is VerificationRole.SUPPORTS
    try:
        CandidateVerification("candidate:1", VerificationState.SUPPORTED, ("obs:1",), (), (), 1.0)
    except ValueError as exc:
        assert "supporting evidence" in str(exc)
    else:
        raise AssertionError("supported state must require explicit supporting evidence")


def test_registry_rejects_duplicate_invariant_ids():
    registry = InvariantRegistry()
    registry.add(Invariant("inv:1", "property"))
    try:
        registry.add(Invariant("inv:1", "other property"))
    except ValueError as exc:
        assert "duplicate invariant" in str(exc)
    else:
        raise AssertionError("duplicate invariant IDs must be rejected")
