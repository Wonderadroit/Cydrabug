from cydra.ens_build_identity import (
    ENS_NPMRC_SHA,
    ENS_PACKAGE_JSON_SHA,
    ENS_PNPM_LOCK_SHA,
    ENS_PNPM_VERSION,
    ENS_PNPM_WORKSPACE_SHA,
)
from cydra.ens_build_receipt import build_receipt_from_observations


HASHES = {
    "package.json": ENS_PACKAGE_JSON_SHA,
    "pnpm-lock.yaml": ENS_PNPM_LOCK_SHA,
    "pnpm-workspace.yaml": ENS_PNPM_WORKSPACE_SHA,
    ".npmrc": ENS_NPMRC_SHA,
}


def test_verified_receipt_requires_exact_snapshot_and_successful_validation():
    receipt = build_receipt_from_observations(
        node_version="v22.23.2",
        pnpm_version=ENS_PNPM_VERSION,
        frozen_install_exit_code=0,
        check_exit_code=0,
        manager_build_exit_code=0,
        worktree_clean=True,
        file_hashes=HASHES,
    )

    assert receipt.target_identity_verified
    assert receipt.toolchain_verified
    assert receipt.dependency_inputs_verified
    assert receipt.validation_verified
    assert receipt.verified
    assert receipt.failure_reasons() == ()


def test_receipt_rejects_wrong_toolchain_even_when_commands_succeed():
    receipt = build_receipt_from_observations(
        node_version="v18.19.1",
        pnpm_version=ENS_PNPM_VERSION,
        frozen_install_exit_code=0,
        check_exit_code=0,
        manager_build_exit_code=0,
        worktree_clean=True,
        file_hashes=HASHES,
    )

    assert not receipt.verified
    assert "Node/pnpm toolchain evidence is not verified" in receipt.failure_reasons()


def test_receipt_rejects_dirty_or_wrong_snapshot():
    receipt = build_receipt_from_observations(
        node_version="v22.23.2",
        pnpm_version=ENS_PNPM_VERSION,
        frozen_install_exit_code=0,
        check_exit_code=0,
        manager_build_exit_code=0,
        worktree_clean=False,
        snapshot_commit="not-the-snapshot",
        file_hashes=HASHES,
    )

    assert not receipt.verified
    assert "target identity/worktree evidence is not verified" in receipt.failure_reasons()


def test_receipt_rejects_missing_build_input_hashes():
    receipt = build_receipt_from_observations(
        node_version="v22.23.2",
        pnpm_version=ENS_PNPM_VERSION,
        frozen_install_exit_code=0,
        check_exit_code=0,
        manager_build_exit_code=0,
        worktree_clean=True,
    )

    assert not receipt.verified
    assert "dependency/build input hashes are not verified" in receipt.failure_reasons()


def test_receipt_rejects_failed_canonical_command():
    receipt = build_receipt_from_observations(
        node_version="v22.23.2",
        pnpm_version=ENS_PNPM_VERSION,
        frozen_install_exit_code=0,
        check_exit_code=1,
        manager_build_exit_code=0,
        worktree_clean=True,
        file_hashes=HASHES,
    )

    assert not receipt.verified
    assert "one or more canonical validation commands failed" in receipt.failure_reasons()
