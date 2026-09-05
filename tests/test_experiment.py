import pytest

from cydra.experiment import ExperimentVariant
from cydra.ens_target import AUDITED_REVISION, DEFAULT_REPOSITORY

REVISION = AUDITED_REVISION


def make_variant(**overrides):
    values = {
        "target_repository": DEFAULT_REPOSITORY,
        "target_revision": REVISION,
        "experiment_name": "verify-invariant:test",
        "variant_id": "boundary",
        "parameters": {"amount": 1, "actor": "alice"},
        "hypothesis_ids": ("hypothesis:invariant-holds:test", "hypothesis:invariant-violated:test"),
        "target_ids": ("function:ENS:example",),
    }
    values.update(overrides)
    return ExperimentVariant(**values)


def test_experiment_digest_binds_variant_and_parameters():
    first = make_variant()
    second = make_variant(variant_id="adversarial")
    third = make_variant(parameters={"amount": 2, "actor": "alice"})
    assert first.digest != second.digest
    assert first.digest != third.digest
    assert first.request_parameters()["experiment_digest"] == first.digest


def test_experiment_parameters_are_canonicalized():
    first = make_variant(parameters={"actor": "alice", "amount": 1})
    second = make_variant(parameters={"amount": 1, "actor": "alice"})
    assert first.digest == second.digest


def test_experiment_rejects_wrong_live_target_revision():
    with pytest.raises(ValueError, match="pinned live target revision"):
        make_variant(target_revision="deadbeef")


def test_experiment_rejects_other_repository():
    with pytest.raises(ValueError, match="outside the current CYDRA live target"):
        make_variant(target_repository="other/project")


def test_experiment_requires_hypothesis_binding():
    with pytest.raises(ValueError, match="at least one"):
        make_variant(hypothesis_ids=())
