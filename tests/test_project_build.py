from pathlib import Path

from cydra.project_build import ProjectBuilder, ToolchainSpec, detect_project, build_identity


def test_foundry_declared_solc_is_preserved(tmp_path: Path):
    (tmp_path / "foundry.toml").write_text('solc_version = "0.8.24"\n', encoding="utf-8")
    profile = detect_project(tmp_path)
    assert profile.system == "foundry"
    assert profile.toolchain == ToolchainSpec("solc", "0.8.24", "foundry.toml:solc_version", "forge")
    assert profile.ast_format == "solc-json-ast"


def test_missing_compiler_version_remains_unknown(tmp_path: Path):
    (tmp_path / "foundry.toml").write_text('[profile.default]\noptimizer = true\n', encoding="utf-8")
    profile = detect_project(tmp_path)
    assert profile.toolchain.version is None
    assert "compiler-unspecified" in profile.toolchain.source


def test_build_identity_fingerprints_declared_configuration(tmp_path: Path):
    (tmp_path / "foundry.toml").write_text('solc_version = "0.8.24"\n', encoding="utf-8")
    (tmp_path / "foundry.lock").write_text("locked", encoding="utf-8")
    identity = build_identity(tmp_path, "abc123", "example/repo")
    assert identity.repository == "example/repo"
    assert identity.revision == "abc123"
    assert identity.declared_toolchain.version == "0.8.24"
    assert identity.config_fingerprint
    assert identity.dependency_lock_files == ("foundry.lock",)


def test_unavailable_build_tool_never_claims_reproducibility(tmp_path: Path):
    (tmp_path / "foundry.toml").write_text('solc_version = "0.8.24"\n', encoding="utf-8")
    builder = ProjectBuilder(tmp_path)
    result = builder.build(command=("definitely-not-a-cydra-tool",))
    assert result.status == "TOOLCHAIN_UNAVAILABLE"
    assert result.reproducibility == "NOT_ESTABLISHED"
    assert result.artifacts == {}
