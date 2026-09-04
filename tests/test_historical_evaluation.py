import pytest

from cydra.historical_evaluation import EvaluationPhase, HistoricalEvaluation


def evaluation():
    return HistoricalEvaluation(
        "eval-immunefi-arbitration-2024",
        "Immunefi Arbitration",
        "immunefi-team/vaults",
        "49c1de26cda19c9e8a4aa311ba3b0dc864f34a25",
    )


def test_evaluation_is_blind_before_freeze():
    item = evaluation()
    assert item.blind
    assert not item.oracle_allowed


def test_oracle_cannot_be_revealed_before_freeze():
    with pytest.raises(RuntimeError, match="before CYDRA output is frozen"):
        evaluation().advance(EvaluationPhase.ORACLE_REVEALED)


def test_comparison_requires_oracle_reveal():
    frozen = evaluation().advance(EvaluationPhase.FROZEN)
    with pytest.raises(RuntimeError, match="requires oracle reveal"):
        frozen.advance(EvaluationPhase.COMPARED)


def test_frozen_then_oracle_then_compare():
    item = evaluation().advance(EvaluationPhase.FROZEN)
    item = item.advance(EvaluationPhase.ORACLE_REVEALED)
    assert not item.blind
    assert item.oracle_allowed
    item = item.advance(EvaluationPhase.COMPARED)
    assert item.phase is EvaluationPhase.COMPARED
