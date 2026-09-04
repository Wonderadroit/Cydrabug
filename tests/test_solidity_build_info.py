import json

from cydra.solidity_model import load_foundry_build_info


def test_load_foundry_build_info_requires_compiler_and_source_identity(tmp_path):
    (tmp_path / "build-info").mkdir()
    data = {
        "solcVersion": "0.8.24",
        "solcLongVersion": "0.8.24+commit.e11b9ed9",
        "input": {"sources": {"src/Vault.sol": {"content": "contract Vault {}"}}},
        "output": {"sources": {"src/Vault.sol": {"ast": {"nodeType": "SourceUnit", "id": 1}}}},
    }
    (tmp_path / "build-info" / "a.json").write_text(json.dumps(data), encoding="utf-8")
    records = load_foundry_build_info(tmp_path)
    assert len(records) == 1
    assert records[0].source_file == "src/Vault.sol"
    assert records[0].solc_version == "0.8.24"
    assert records[0].solc_long_version == "0.8.24+commit.e11b9ed9"
    assert records[0].source_fingerprint


def test_load_foundry_build_info_rejects_missing_compiler_identity(tmp_path):
    (tmp_path / "build-info").mkdir()
    data = {
        "input": {"sources": {"src/Vault.sol": {"content": "contract Vault {}"}}},
        "output": {"sources": {"src/Vault.sol": {"ast": {"nodeType": "SourceUnit", "id": 1}}}},
    }
    (tmp_path / "build-info" / "a.json").write_text(json.dumps(data), encoding="utf-8")
    assert load_foundry_build_info(tmp_path) == ()
