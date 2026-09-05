import pytest

from cydra.invariants import VerificationState
from cydra.verification import VariantObservation, verify_candidate_from_variants


def obs(variant, evidence, outcome, mechanism="m1", confidence=0.9):
    return VariantObservation(variant, evidence, outcome, mechanism, confidence)


def test_two_distinct_variants_with_same_violation_mechanism_support_candidate():
    verification, evidence = verify_candidate_from_variants(
        "candidate:x",
        [obs("normal", "e1", "INVARIANT_VIOLATED"), obs("boundary", "e2", "INVARIANT_VIOLATED")],
    )
    assert verification.state is VerificationState.SUPPORTED
    assert verification.supporting_ids == ("e1", "e2")
    assert len(evidence) == 2


def test_repeated_same_variant_does_not_count_as_variant_validation():
    verification, _ = verify_candidate_from_variants(
        "candidate:x",
        [obs("normal", "e1", "INVARIANT_VIOLATED"), obs("normal", "e2", "INVARIANT_VIOLATED")],
    )
    assert verification.state is VerificationState.UNRESOLVED


def test_contradictory_variants_remain_unresolved():
    verification, evidence = verify_candidate_from_variants(
        "candidate:x",
        [obs("normal", "e1", "INVARIANT_VIOLATED"), obs("boundary", "e2", "INVARIANT_PRESERVED")],
    )
    assert verification.state is VerificationState.UNRESOLVED
    assert not verification.supporting_ids
    assert not verification.contradicting_ids
    assert [item.role.value for item in evidence] == ["supports", "contradicts"]


def test_preserved_distinct_variants_contradict_violation_candidate():
    verification, _ = verify_candidate_from_variants(
        "candidate:x",
        [obs("normal", "e1", "INVARIANT_PRESERVED"), obs("boundary", "e2", "INVARIANT_PRESERVED")],
    )
    assert verification.state is VerificationState.CONTRADICTED
    assert verification.contradicting_ids == ("e1", "e2")


def test_different_mechanisms_do_not_claim_one_causal_verification():
    verification, _ = verify_candidate_from_variants(
        "candidate:x",
        [obs("normal", "e1", "INVARIANT_VIOLATED", "m1"), obs("boundary", "e2", "INVARIANT_VIOLATED", "m2")],
    )
    assert verification.state is VerificationState.UNRESOLVED


def test_evidence_ids_must_be_unique():
    with pytest.raises(ValueError, match="unique evidence IDs"):
        verify_candidate_from_variants(
            "candidate:x",
            [obs("normal", "e1", "INVARIANT_VIOLATED"), obs("boundary", "e1", "INVARIANT_VIOLATED")],
        )
