from pathlib import Path
import subprocess

import pytest

from cydra.historical_evaluation import EvaluationPhase, HistoricalEvaluation
from cydra.historical_workspace import arbitration_boost_2024, materialize_blind_workspace


def make_git_checkout(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "cydra@test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "CYDRA Test"], cwd=root, check=True)
    (root / "README.md").write_text("blind", encoding="utf-8")
    (root / "foundry.toml").write_text('solc_version = "0.8.23"\n', encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "Vault.sol").write_text("contract Vault {}", encoding="utf-8")
    (root / "reports").mkdir()
    (root / "reports" / "oracle.md").write_text("historical answer", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    return root, actual


def fixture_spec(revision: str):
    base = arbitration_boost_2024()
    return type(base)(base.evaluation_id, base.repository, revision, base.allowed_paths, base.excluded_names)


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


def test_revision_mismatch_fails_closed(tmp_path):
    root, _ = make_git_checkout(tmp_path)
    with pytest.raises(RuntimeError, match="revision mismatch"):
        materialize_blind_workspace(root, tmp_path / "blind", arbitration_boost_2024())


def test_dirty_tracked_checkout_is_rejected(tmp_path):
    root, revision = make_git_checkout(tmp_path)
    spec = fixture_spec(revision)
    (root / "src" / "Vault.sol").write_text("tampered", encoding="utf-8")
    with pytest.raises(RuntimeError, match="must be clean"):
        materialize_blind_workspace(root, tmp_path / "blind", spec)


def test_untracked_file_is_rejected_even_outside_allowlist(tmp_path):
    root, revision = make_git_checkout(tmp_path)
    spec = fixture_spec(revision)
    (root / "oracle-answer.txt").write_text("forbidden", encoding="utf-8")
    with pytest.raises(RuntimeError, match="must be clean"):
        materialize_blind_workspace(root, tmp_path / "blind", spec)


def test_phase_order_is_explicit_and_oracle_is_sealed():
    e = HistoricalEvaluation("e", "contest", "repo", "rev")
    e = e.advance(EvaluationPhase.UNDERSTANDING)
    e = e.advance(EvaluationPhase.REASONING)
    e = e.advance(EvaluationPhase.INVESTIGATION)
    e = e.advance(EvaluationPhase.VERIFICATION)
    e = e.advance(EvaluationPhase.FROZEN)
    with pytest.raises(RuntimeError, match="must advance one phase"):
        e.advance(EvaluationPhase.INTAKE)
    with pytest.raises(RuntimeError, match="requires oracle reveal"):
        e.advance(EvaluationPhase.COMPARED)
    assert e.blind is True
    assert e.oracle_allowed is False
