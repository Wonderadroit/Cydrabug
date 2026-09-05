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


def test_source_identity_is_unresolved_when_advertised_object_is_absent(tmp_path):
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "-C", str(repo), "init"], check=True)
    (repo / "README").write_text("snapshot")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True)
    subprocess.run(
        [
            "git", "-C", str(repo),
            "-c", "user.name=CYDRA",
            "-c", "user.email=cydra@example.invalid",
            "commit", "-m", "snapshot",
        ],
        check=True,
    )

    from cydra.ens_source_identity import verify_source_identity

    result = verify_source_identity(
        repo,
        advertised_revision="1111111111111111111111111111111111111111",
    )

    assert result.status == "UNRESOLVED"
    assert result.verified is False
    assert result.advertised_object_available is False


def test_source_identity_verifies_exact_git_object(tmp_path):
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "-C", str(repo), "init"], check=True)
    (repo / "README").write_text("audited")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True)
    subprocess.run(
        [
            "git", "-C", str(repo),
            "-c", "user.name=CYDRA",
            "-c", "user.email=cydra@example.invalid",
            "commit", "-m", "audited",
        ],
        check=True,
    )

    revision = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    from cydra.ens_source_identity import verify_source_identity

    result = verify_source_identity(repo, advertised_revision=revision)

    assert result.status == "VERIFIED"
    assert result.verified is True
    assert result.advertised_object_available is True
    assert result.observed_revision == revision
