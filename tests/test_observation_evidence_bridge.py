import pytest

from cydra.execution_evidence import ExecutionEvidence
from cydra.hypothesis import Hypothesis, HypothesisState
from cydra.invariants import VerificationRole
from cydra.observation_evidence_bridge import (
    ObservationVerificationBinding,
    apply_observation_evidence,
    verification_from_execution_evidence,
)


def evidence(outcome="INVARIANT_PRESERVED", confidence=1.0):
    return ExecutionEvidence(
        evidence_id="evidence:exec-1",
        observation_name="check-state",
        execution_id="exec-1",
        request_digest="execution-request:fixture",
        adapter="fake",
        outcome=outcome,
        receipt_fingerprint="execution-receipt:fingerprint",
        payload={"execution_id": "exec-1"},
        confidence=confidence,
    )


def binding(**roles):
    return ObservationVerificationBinding(
        observation_name="check-state",
        hypothesis_ids=("h:holds", "h:violated"),
        outcome_roles=roles or {
            "INVARIANT_PRESERVED": (VerificationRole.SUPPORTS, VerificationRole.CONTRADICTS),
            "INVARIANT_VIOLATED": (VerificationRole.CONTRADICTS, VerificationRole.SUPPORTS),
            "INCONCLUSIVE": (VerificationRole.NEUTRAL, VerificationRole.NEUTRAL),
        },
    )


def hypotheses():
    return (
        Hypothesis("h:holds", "the invariant holds"),
        Hypothesis("h:violated", "the invariant is violated"),
    )


def test_explicit_outcome_mapping_updates_exact_competing_pair():
    updated, updates = apply_observation_evidence(
        hypotheses=hypotheses(), evidence=evidence(), binding=binding()
    )
    assert updated[0].state == HypothesisState.SUPPORTED
    assert updated[0].belief > 0.5
    assert updated[1].state == HypothesisState.CONTRADICTED
    assert updated[1].belief < 0.5
    assert updates[0].evidence_ids == ("evidence:exec-1",)


def test_inconclusive_mapping_preserves_beliefs_and_unresolved_state():
    updated, _ = apply_observation_evidence(
        hypotheses=hypotheses(), evidence=evidence("INCONCLUSIVE"), binding=binding()
    )
    assert all(item.belief == 0.5 for item in updated)
    assert all(item.state == HypothesisState.UNRESOLVED for item in updated)


def test_unknown_outcome_is_fail_closed():
    with pytest.raises(ValueError, match="unmapped observation outcome"):
        verification_from_execution_evidence(
            evidence=evidence("UNDECLARED"), binding=binding()
        )


def test_observation_identity_must_match_binding():
    bad = ExecutionEvidence(
        evidence_id="e1", observation_name="other", execution_id="exec-1",
        request_digest="execution-request:fixture", adapter="fake", outcome="INVARIANT_PRESERVED",
        receipt_fingerprint="execution-receipt:fingerprint", payload={"execution_id": "exec-1"},
    )
    with pytest.raises(ValueError, match="observation"):
        verification_from_execution_evidence(evidence=bad, binding=binding())


def test_non_neutral_receipt_evidence_cannot_skip_semantic_mapping():
    non_neutral = ExecutionEvidence(
        evidence_id="e1", observation_name="check-state", execution_id="exec-1",
        request_digest="execution-request:fixture", adapter="fake", outcome="INVARIANT_PRESERVED",
        receipt_fingerprint="execution-receipt:fingerprint", payload={"execution_id": "exec-1"},
        polarity="supports",
    )
    with pytest.raises(ValueError, match="neutral polarity"):
        verification_from_execution_evidence(evidence=non_neutral, binding=binding())


def test_missing_hypothesis_fails_closed():
    with pytest.raises(ValueError, match="hypotheses"):
        apply_observation_evidence(
            hypotheses=(hypotheses()[0],), evidence=evidence(), binding=binding()
        )
