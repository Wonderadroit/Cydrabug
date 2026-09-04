import pytest

from cydra.hypothesis import Hypothesis, HypothesisState, update_hypothesis
from cydra.invariants import CandidateVerification, VerificationEvidence, VerificationRole, VerificationState
from cydra.planner import Hypothesis as PlannerHypothesis


def evidence(evidence_id="e1", role=VerificationRole.SUPPORTS, confidence=0.8):
    return VerificationEvidence(evidence_id, role, confidence, "bound test evidence")


def verification(state=VerificationState.SUPPORTED, evidence_ids=("e1",), supporting_ids=("e1",), contradicting_ids=()):
    return CandidateVerification("candidate:1", state, evidence_ids, supporting_ids, contradicting_ids, 0.8)


def test_planner_and_persistent_hypothesis_are_one_model():
    assert PlannerHypothesis is Hypothesis
    item = Hypothesis("hypothesis:x", "x")
    assert item.probability == item.belief
    assert item.predictions is item.planning_predictions


def test_supporting_bound_evidence_increases_belief():
    item = Hypothesis("hypothesis:x", "x", 0.5)
    updated, event = update_hypothesis(item, verification(), [evidence()])
    assert updated.belief > item.belief
    assert updated.state == HypothesisState.SUPPORTED
    assert event.evidence_ids == ("e1",)
    assert updated.applied_evidence_ids == ("e1",)


def test_contradicting_bound_evidence_decreases_belief():
    item = Hypothesis("hypothesis:x", "x", 0.8)
    v = verification(VerificationState.CONTRADICTED, ("e2",), (), ("e2",))
    updated, _ = update_hypothesis(item, v, [evidence("e2", VerificationRole.CONTRADICTS)])
    assert updated.belief < item.belief
    assert updated.state == HypothesisState.CONTRADICTED


def test_unresolved_verification_leaves_belief_unchanged():
    item = Hypothesis("hypothesis:x", "x", 0.7)
    v = verification(VerificationState.UNRESOLVED, (), (), ())
    updated, _ = update_hypothesis(item, v, [])
    assert updated.belief == item.belief
    assert updated.state == HypothesisState.UNRESOLVED


def test_unbound_evidence_cannot_influence_update():
    item = Hypothesis("hypothesis:x", "x", 0.5)
    with pytest.raises(ValueError, match="was not supplied"):
        update_hypothesis(item, verification(), [evidence("different")])


def test_neutral_evidence_does_not_change_belief():
    item = Hypothesis("hypothesis:x", "x", 0.5)
    v = verification(VerificationState.UNRESOLVED, ("e1",), (), ())
    updated, _ = update_hypothesis(item, v, [evidence("e1", VerificationRole.NEUTRAL)])
    assert updated.belief == item.belief
    assert updated.state == HypothesisState.UNRESOLVED


def test_duplicate_verification_evidence_is_rejected_within_one_update():
    item = Hypothesis("hypothesis:x", "x", 0.5)
    duplicate = verification(evidence_ids=("e1", "e1"), supporting_ids=("e1", "e1"))
    with pytest.raises(ValueError, match="duplicate evidence IDs"):
        update_hypothesis(item, duplicate, [evidence()])


def test_already_applied_evidence_cannot_change_belief_twice():
    item = Hypothesis("hypothesis:x", "x", 0.5)
    updated, _ = update_hypothesis(item, verification(), [evidence()])
    with pytest.raises(ValueError, match="already been applied"):
        update_hypothesis(updated, verification(), [evidence()])


def test_discovery_confidence_is_not_used_as_initial_belief():
    a = Hypothesis("hypothesis:a", "a", 0.5)
    b = Hypothesis("hypothesis:b", "b", 0.5)
    assert a.belief == b.belief
