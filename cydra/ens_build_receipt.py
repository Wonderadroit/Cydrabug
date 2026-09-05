"""ENS-specific reproducible build receipt.

This module accepts evidence produced by the canonical ENS checkout/build
workflow and verifies that the evidence is bound to the exact target snapshot
and required Node/pnpm toolchain. It deliberately does not execute arbitrary
target commands or infer build success from source metadata alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .ens_build_identity import (
    ENS_NPMRC_SHA,
    ENS_PACKAGE_JSON_SHA,
    ENS_PNPM_LOCK_SHA,
    ENS_PNPM_VERSION,
    ENS_PNPM_WORKSPACE_SHA,
)
from .ens_target import AUDITED_REVISION, DEFAULT_REPOSITORY, DEFAULT_REVISION


ENS_SNAPSHOT_TREE = "8e0d79dac1ab4b4fdb80d6afed8100879ae9f00ba"


@dataclass(frozen=True)
class ENSBuildReceipt:
    repository: str
    audited_revision: str
    snapshot_commit: str
    snapshot_tree: str
    worktree_clean: bool
    node_version: str
    pnpm_version: str
    frozen_install_exit_code: int
    check_exit_code: int
    manager_build_exit_code: int
    package_json_sha: str
    pnpm_lock_sha: str
    pnpm_workspace_sha: str
    npmrc_sha: str

    @property
    def target_identity_verified(self) -> bool:
        return (
            self.repository == DEFAULT_REPOSITORY
            and self.audited_revision == AUDITED_REVISION
            and self.snapshot_commit == DEFAULT_REVISION
            and self.snapshot_tree == ENS_SNAPSHOT_TREE
            and self.worktree_clean
        )

    @property
    def toolchain_verified(self) -> bool:
        return self.node_version.startswith("v22.") and self.pnpm_version == ENS_PNPM_VERSION

    @property
    def dependency_inputs_verified(self) -> bool:
        return (
            self.package_json_sha == ENS_PACKAGE_JSON_SHA
            and self.pnpm_lock_sha == ENS_PNPM_LOCK_SHA
            and self.pnpm_workspace_sha == ENS_PNPM_WORKSPACE_SHA
            and self.npmrc_sha == ENS_NPMRC_SHA
        )

    @property
    def validation_verified(self) -> bool:
        return (
            self.frozen_install_exit_code == 0
            and self.check_exit_code == 0
            and self.manager_build_exit_code == 0
        )

    @property
    def verified(self) -> bool:
        return (
            self.target_identity_verified
            and self.toolchain_verified
            and self.dependency_inputs_verified
            and self.validation_verified
        )

    def failure_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.target_identity_verified:
            reasons.append("target identity/worktree evidence is not verified")
        if not self.toolchain_verified:
            reasons.append("Node/pnpm toolchain evidence is not verified")
        if not self.dependency_inputs_verified:
            reasons.append("dependency/build input hashes are not verified")
        if not self.validation_verified:
            reasons.append("one or more canonical validation commands failed")
        return tuple(reasons)


def build_receipt_from_observations(
    *,
    node_version: str,
    pnpm_version: str,
    frozen_install_exit_code: int,
    check_exit_code: int,
    manager_build_exit_code: int,
    worktree_clean: bool,
    snapshot_commit: str = DEFAULT_REVISION,
    snapshot_tree: str = ENS_SNAPSHOT_TREE,
    file_hashes: Mapping[str, str] | None = None,
) -> ENSBuildReceipt:
    """Bind externally observed build evidence to the canonical ENS snapshot.

    ``file_hashes`` must contain the four immutable build-input blobs. Missing
    entries are represented explicitly as empty values and therefore cannot
    satisfy the verification boundary.
    """
    hashes = file_hashes or {}
    return ENSBuildReceipt(
        repository=DEFAULT_REPOSITORY,
        audited_revision=AUDITED_REVISION,
        snapshot_commit=snapshot_commit,
        snapshot_tree=snapshot_tree,
        worktree_clean=worktree_clean,
        node_version=node_version,
        pnpm_version=pnpm_version,
        frozen_install_exit_code=frozen_install_exit_code,
        check_exit_code=check_exit_code,
        manager_build_exit_code=manager_build_exit_code,
        package_json_sha=hashes.get("package.json", ""),
        pnpm_lock_sha=hashes.get("pnpm-lock.yaml", ""),
        pnpm_workspace_sha=hashes.get("pnpm-workspace.yaml", ""),
        npmrc_sha=hashes.get(".npmrc", ""),
    )
