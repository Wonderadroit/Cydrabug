import subprocess

from cydra.source_identity import (
    acquire_and_verify_source,
    repository_locator,
    target_path,
)


def _repo(path):
    path.mkdir()
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True)
    (path / "apps").mkdir()
    (path / "apps" / "manager").mkdir()
    (path / "apps" / "manager" / "README").write_text("target")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=CYDRA", "-c", "user.email=cydra@example.invalid", "commit", "-m", "target"],
        check=True,
        capture_output=True,
    )
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def test_github_tree_locator_preserves_repository_and_target_path():
    locator = "https://github.com/example/project/tree/main/apps/manager"
    assert repository_locator(locator) == "https://github.com/example/project.git"
    assert target_path(locator) == "apps/manager"


def test_source_identity_verifies_exact_revision_and_target(tmp_path):
    origin = tmp_path / "origin"
    revision = _repo(origin)
    clone = tmp_path / "clone"

    # file:// keeps the test local while exercising the same Git acquisition path
    locator = origin.as_uri()
    result = acquire_and_verify_source(
        locator,
        revision,
        clone,
        target_paths=("apps/manager",),
    )

    assert result.status == "VERIFIED"
    assert result.verified is True
    assert result.observed_revision == revision
    assert result.working_tree_clean is True
    assert result.missing_target_paths == ()


def test_source_identity_is_unresolved_when_revision_is_absent(tmp_path):
    origin = tmp_path / "origin"
    _repo(origin)
    clone = tmp_path / "clone"

    result = acquire_and_verify_source(
        origin.as_uri(),
        "1111111111111111111111111111111111111111",
        clone,
    )

    assert result.status == "UNRESOLVED"
    assert result.verified is False


def test_source_identity_blocks_dirty_checkout(tmp_path):
    origin = tmp_path / "origin"
    revision = _repo(origin)
    clone = tmp_path / "clone"

    first = acquire_and_verify_source(origin.as_uri(), revision, clone)
    assert first.status == "VERIFIED"

    (clone / "dirty").write_text("local mutation")
    second = acquire_and_verify_source(origin.as_uri(), revision, clone)

    assert second.status == "UNRESOLVED"
    assert second.working_tree_clean is False
    assert "not clean" in second.reason
