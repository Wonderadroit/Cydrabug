from cydra.ens_build_identity import declared_build_identity
from cydra.ens_source_identity import (
    ENS_SOURCE_ORIGIN_REPOSITORY,
    ENS_SOURCE_SNAPSHOT_COMMIT,
)
from cydra.ens_target import AUDITED_REVISION, DEFAULT_REPOSITORY


def test_declared_build_identity_preserves_snapshot_and_toolchain_evidence():
    evidence = declared_build_identity()
    assert evidence.repository == DEFAULT_REPOSITORY
    assert evidence.audited_revision == AUDITED_REVISION
    assert evidence.snapshot_commit == ENS_SOURCE_SNAPSHOT_COMMIT
    assert evidence.origin_repository == ENS_SOURCE_ORIGIN_REPOSITORY
    assert evidence.node_requirement == "22"
    assert evidence.pnpm_version == "10.27.0"
    assert evidence.package_json_sha
    assert evidence.pnpm_lock_sha
    assert evidence.pnpm_workspace_sha
    assert evidence.npmrc_sha


def test_build_identity_remains_unresolved_without_execution():
    evidence = declared_build_identity()
    assert evidence.source_lineage_declared
    assert not evidence.build_verified
    assert evidence.status == "BUILD_IDENTITY_UNRESOLVED"
