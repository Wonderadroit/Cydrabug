import pytest

from cydra.hypothesis import Hypothesis
from cydra.invariants import InvariantCandidate, VerificationState
from cydra.invariant_hypothesis_bridge import hypotheses_from_verified_invariants, persist_invariant_hypotheses, competing_hypotheses_from_candidates, InvariantHypothesis, planner_hypotheses_from_verified_invariants
from cydra.planner import Hypothesis as PlannerHypothesis
from cydra.system_model import Node, SystemModel


def candidate(cid="invariant:i1", statement="balance remains solvent"):
    return InvariantCandidate(cid, statement, ("ast:withdraw",), .9, 1)


def supported_model():
    model = SystemModel()
    model.add_node(Node("invariant:i1", "invariant", "balance remains solvent", {"verification_state": VerificationState.SUPPORTED.value, "verification_confidence": .9, "supporting_evidence_ids": ["e1"]}))
    model.add_node(Node("evidence:e1", "evidence", "e1"))
    model.connect("invariant:i1", "verified_by", "evidence:e1", provenance="explicit_verification")
    return model


def test_only_explicitly_supported_invariants_bridge():
    model = supported_model()
    model.add_node(Node("invariant:i2", "invariant", "unverified", {"verified": True, "confidence": .99}))
    result = hypotheses_from_verified_invariants(model, [candidate(), candidate("invariant:i2", "unverified")])
    assert [x.invariant_id for x in result] == ["invariant:i1"]


def test_missing_verification_edge_blocks_bridge():
    model = SystemModel()
    model.add_node(Node("invariant:i1", "invariant", "balance remains solvent", {"verification_state": VerificationState.SUPPORTED.value, "supporting_evidence_ids": ["e1"]}))
    model.add_node(Node("evidence:e1", "evidence", "e1"))
    assert hypotheses_from_verified_invariants(model, [candidate()]) == []


def test_persistence_requires_supported_invariant():
    model = SystemModel()
    model.add_node(Node("invariant:i1", "invariant", "balance remains solvent", {"verification_state": VerificationState.UNRESOLVED.value, "supporting_evidence_ids": ["e1"]}))
    model.add_node(Node("evidence:e1", "evidence", "e1"))
    with pytest.raises(ValueError, match="explicitly supported"):
        persist_invariant_hypotheses(model, [InvariantHypothesis("hypothesis:h", "invariant:i1", "Violation of invariant: balance remains solvent", .9)])


def test_candidate_creates_symmetric_competing_hypotheses():
    hypotheses, observations = competing_hypotheses_from_candidates([candidate()])
    assert [h.probability for h in hypotheses] == [.5, .5]
    assert all(isinstance(h, Hypothesis) for h in hypotheses)
    assert all(isinstance(h, PlannerHypothesis) for h in hypotheses)
    assert len(observations) == 1
    assert observations[0].discriminates_hypothesis_ids == tuple(h.hypothesis_id for h in hypotheses)
    assert observations[0].target_ids == ()


def test_discovery_confidence_does_not_bias_competing_priors():
    high = InvariantCandidate("candidate:x", "property", ("compiler:1",), .999, 1)
    hypotheses, _ = competing_hypotheses_from_candidates([high])
    assert all(h.probability == .5 for h in hypotheses)


def test_planner_bridge_preserves_explicit_canonical_hypothesis_identity():
    model = supported_model()
    canonical = Hypothesis("hypothesis:invariant:i1", "Violation of invariant: balance remains solvent")
    result = planner_hypotheses_from_verified_invariants(
        model, [candidate()], {canonical.hypothesis_id: canonical}
    )
    assert len(result) == 1
    item, hypothesis = result[0]
    assert item.hypothesis_id == canonical.hypothesis_id
    assert hypothesis is canonical
