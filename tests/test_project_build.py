import json
from pathlib import Path

from cydra.project_build import ProjectBuilder, ToolchainSpec, detect_project, build_identity
from cydra.solidity_model import load_foundry_build_info


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


def test_foundry_build_info_is_discovered_under_out(tmp_path: Path):
    build_info = tmp_path / "out" / "build-info"
    build_info.mkdir(parents=True)
    source = "contract Vault {}"
    ast = {"nodeType": "SourceUnit", "id": 1, "nodes": []}
    payload = {
        "solcVersion": "0.8.18",
        "solcLongVersion": "0.8.18+commit.87f61d96",
        "input": {"sources": {"src/Vault.sol": {"content": source}}},
        "output": {"sources": {"src/Vault.sol": {"ast": ast}}},
    }
    (build_info / "fixture.json").write_text(json.dumps(payload), encoding="utf-8")
    records = load_foundry_build_info(tmp_path)
    assert len(records) == 1
    assert records[0].build_info_file == "out/build-info/fixture.json"
    assert records[0].source_file == "src/Vault.sol"
    assert records[0].solc_version == "0.8.18"
