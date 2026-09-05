import json

from cydra.target_environment import discover_requirements, verify_requirements


def test_discover_requirements_reads_target_declarations(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({
            "packageManager": "pnpm@10.27.0",
            "engines": {"node": ">=22"},
            "scripts": {"e2e": "docker compose up"},
        }),
        encoding="utf-8",
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    requirements = discover_requirements(tmp_path)
    assert any(r.name == "pnpm" and r.version == "10.27.0" for r in requirements)
    assert any(r.name == "node" and r.version == ">=22" for r in requirements)
    assert any(r.name == "docker" for r in requirements)
    assert any(r.name == "pnpm-lock.yaml" for r in requirements)


def test_verify_requirements_reports_missing_capability_without_installing(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(
        json.dumps({"packageManager": "pnpm@99.99.99"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("cydra.target_environment.shutil.which", lambda executable: None)
    report = verify_requirements(tmp_path)
    assert not report.ready
    assert "pnpm" in report.missing_required
    assert (tmp_path / "package.json").read_text(encoding="utf-8")


def test_version_constraints_are_not_treated_as_unconditional(monkeypatch, tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"engines": {"node": ">=22"}}), encoding="utf-8"
    )
    monkeypatch.setattr("cydra.target_environment.shutil.which", lambda executable: executable)
    monkeypatch.setattr(
        "cydra.target_environment.subprocess.run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": "v20.11.0\n", "stderr": ""})(),
    )
    report = verify_requirements(tmp_path)
    assert not report.ready
    assert "node" in report.missing_required
