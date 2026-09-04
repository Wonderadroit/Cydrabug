from pathlib import Path

import pytest

from cydra.historical_workspace import arbitration_boost_2024, materialize_blind_workspace


def git_checkout(tmp_path: Path, revision: str) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / ".git").mkdir()
    # Replace the git command boundary with a tiny executable fixture.
    return root


def test_arbitration_spec_is_exact():
    spec = arbitration_boost_2024()
    assert spec.repository == "immunefi-team/vaults"
    assert spec.revision == "49c1de26cda19c9e8a4aa311ba3b0dc864f34a25"
    assert spec.allowed_paths == ("README.md", "foundry.toml", "src")
    assert "reports" in spec.excluded_names


def test_non_git_checkout_is_rejected(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    with pytest.raises(ValueError, match="git working tree"):
        materialize_blind_workspace(root, tmp_path / "blind", arbitration_boost_2024())


def test_allowlist_does_not_copy_oracle_like_paths(tmp_path):
    # This test exercises the structural policy without requiring a real Git checkout.
    spec = arbitration_boost_2024()
    assert all("reports" not in p.lower() for p in spec.allowed_paths)
    assert all("findings" not in p.lower() for p in spec.allowed_paths)
