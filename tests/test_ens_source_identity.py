from cydra.ens_source_identity import (
    ENS_SOURCE_ORIGIN_REPOSITORY,
    ENS_SOURCE_SNAPSHOT_COMMIT,
    declared_source_lineage,
)
from cydra.ens_target import AUDITED_REVISION, DEFAULT_REPOSITORY


def test_declared_snapshot_lineage_preserves_audited_revision_identity():
    lineage = declared_source_lineage()
    assert lineage.repository == DEFAULT_REPOSITORY
    assert lineage.audited_revision == AUDITED_REVISION
    assert lineage.snapshot_commit == ENS_SOURCE_SNAPSHOT_COMMIT
    assert lineage.origin_repository == ENS_SOURCE_ORIGIN_REPOSITORY
    assert lineage.declaration.endswith(AUDITED_REVISION)


def test_declared_snapshot_is_not_exact_git_identity_or_build_ready():
    lineage = declared_source_lineage()
    assert not lineage.is_exact_git_identity
    assert not lineage.build_ready
    assert lineage.status == "DECLARED_SNAPSHOT_LINEAGE"
