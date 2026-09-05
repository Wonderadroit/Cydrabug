import hashlib
import json
import subprocess
from types import SimpleNamespace

import pytest

from cydra.execution_request import ExecutionRequest
from cydra.execution_recovery import ExecutionRecoveryService
from cydra.external_execution import ExternalExecutionGateway
from cydra.foundry_build_info import accept_foundry_build_info, project_accepted_ast_evidence
from cydra.foundry_execution import FoundryBuildAdapter
from cydra.project_build import BuildProfile, BuildResult
from cydra.system_model import SystemModel


REPOSITORY = "immunefi-team/vaults"
REVISION = "49c1de26cda19c9e8a4aa311ba3b0dc864f34a25"


def run(root, *args):
    subprocess.run(("git", *args), cwd=root, check=True, capture_output=True, text=True)


def ast():
    return {"id": 1, "nodeType": "SourceUnit", "nodes": [
        {"id": 2, "nodeType": "ContractDefinition", "name": "Vault", "nodes": [
            {"id": 3, "nodeType": "VariableDeclaration", "name": "balance", "stateVariable": True},
            {"id": 4, "nodeType": "FunctionDefinition", "name": "deposit", "scope": 2,
             "body": {"nodeType": "Block", "statements": [{"id": 5, "nodeType": "Identifier", "referencedDeclaration": 3, "src": "1:7:0"}]}}
        ]}
    ]}


def gateway_result(root, monkeypatch, returncode=0, execution_id="foundry-exec-1", parameters=None):
    responses = [
        SimpleNamespace(returncode=0, stdout="forge 1.0.0", stderr=""),
        SimpleNamespace(returncode=returncode, stdout="", stderr=""),
    ]
    monkeypatch.setattr("cydra.foundry_execution.shutil.which", lambda name: "/usr/bin/forge")
    original_run = subprocess.run
    def fake_run(*args, **kwargs):
        command = args[0]
        if command[0] == "forge" or command[1:] == ("--version",):
            return responses.pop(0)
        return original_run(*args, **kwargs)
    monkeypatch.setattr("cydra.foundry_execution.subprocess.run", fake_run)
    request = ExecutionRequest(execution_id, "foundry", str(root), ("forge", "build", "--build-info"), None, "auth-1", parameters=parameters or {})
    gateway = ExternalExecutionGateway(
        persist_request=lambda request: None,
        set_execution_state=lambda request, state: None,
        persist_result=lambda request, result: None,
    )
    gateway.register("foundry", FoundryBuildAdapter())
    result = gateway.execute(
        "foundry", request,
        authorization=SimpleNamespace(authorization_id="auth-1", scope_status="AUTHORIZED_EXECUTION", authorized=True),
    )
    return gateway, request, result


def fixture_checkout(tmp_path):
    root = tmp_path / "vaults"
    root.mkdir()
    (root / "contracts").mkdir()
    (root / "contracts" / "Vault.sol").write_text("contract Vault { uint balance; function deposit() external { balance++; } }", encoding="utf-8")
    (root / "foundry.toml").write_text("[profile.default]\nsrc = 'contracts'\n", encoding="utf-8")
    (root / ".gitignore").write_text("out/\n", encoding="utf-8")
    run(root, "init")
    run(root, "config", "user.email", "tests@example.invalid")
    run(root, "config", "user.name", "CYDRA Tests")
    run(root, "add", ".")
    run(root, "commit", "-m", "fixture")
    run(root, "branch", "-M", "pinned")
    # The receiver supplies the expected identity; fixture HEAD is substituted below.
    return root, run_output(root, "rev-parse", "HEAD")


def run_output(root, *args):
    return subprocess.run(("git", *args), cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def write_build_info(root, *, document=None, path="out/build-info/build.json"):
    source = (root / "contracts" / "Vault.sol").read_text(encoding="utf-8")
    document = document or {"compiler_version": "0.8.24+commit.e11b9ed9", "input": {"settings": {"optimizer": {"enabled": True}}, "sources": {"contracts/Vault.sol": {"content": source}}}, "output": {"sources": {"contracts/Vault.sol": {"id": 0, "ast": ast()}}}}
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document), encoding="utf-8")
    return target


def accept(root, revision, monkeypatch, **kwargs):
    gateway, request, result = gateway_result(root, monkeypatch)
    return accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision, expected_request=request, execution_result=result, execution_gateway=gateway, **kwargs)


def test_foundry_adapter_accepts_exact_build_info_command():
    request = ExecutionRequest("foundry-exec-1", "foundry", "fixture", ("forge", "build", "--build-info"), None, "auth-1")
    FoundryBuildAdapter()._validate_request(request)


@pytest.mark.parametrize("command", [
    ("forge", "build", "--build-info", "--force"),
    ("forge", "--build-info", "build"),
    ("forge", "build"),
])
def test_foundry_adapter_rejects_non_exact_build_info_commands(command):
    request = ExecutionRequest("foundry-exec-1", "foundry", "fixture", command, None, "auth-1")
    with pytest.raises(ValueError, match="exact"):
        FoundryBuildAdapter()._validate_request(request)


def test_valid_build_info_is_accepted_and_projects_ast(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    artifact = write_build_info(root)
    accepted = accept(root, revision, monkeypatch)
    assert accepted.receipt.solc_version == "0.8.24+commit.e11b9ed9"
    assert accepted.receipt.forge_version == "forge 1.0.0"
    assert json.loads(accepted.receipt.to_json())["fingerprint"] == accepted.receipt.fingerprint
    assert accepted.receipt.build_info_sha256 == (("out/build-info/build.json", hashlib.sha256(artifact.read_bytes()).hexdigest()),)
    model = SystemModel()
    project_accepted_ast_evidence(model, accepted)
    assert model.edges and model.edges[0].attributes["provenance"] == "solc-json-ast:contracts/Vault.sol"


def test_wrong_head_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path); write_build_info(root)
    with pytest.raises(ValueError, match="HEAD"):
        accept(root, "0" * 40, monkeypatch)


def test_dirty_checkout_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path); write_build_info(root)
    (root / "foundry.toml").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="clean"):
        accept(root, revision, monkeypatch)


def test_missing_or_ambiguous_build_info_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    artifact = write_build_info(root)
    gateway, request, result = gateway_result(root, monkeypatch)
    artifact.unlink()
    with pytest.raises(ValueError, match="missing"):
        accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision, expected_request=request, execution_result=result, execution_gateway=gateway)
    write_build_info(root); write_build_info(root, path="out/build-info/second.json")
    with pytest.raises(ValueError, match="ambiguous"):
        accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision, expected_request=request, execution_result=result, execution_gateway=gateway)


def test_missing_ast_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    document = {"compiler_version": "0.8.24", "input": {"settings": {}, "sources": {"contracts/Vault.sol": {"content": (root / "contracts/Vault.sol").read_text()}}}, "output": {"sources": {"contracts/Vault.sol": {}}}}
    write_build_info(root, document=document)
    with pytest.raises(ValueError, match="AST"):
        accept(root, revision, monkeypatch)


def test_missing_or_conflicting_compiler_metadata_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    source = (root / "contracts/Vault.sol").read_text()
    base = {"input": {"settings": {}, "sources": {"contracts/Vault.sol": {"content": source}}}, "output": {"sources": {"contracts/Vault.sol": {"ast": ast()}}}}
    write_build_info(root, document=base)
    with pytest.raises(ValueError, match="compiler version"):
        accept(root, revision, monkeypatch)
    base["compiler_version"] = "0.8.24"; base["solcVersion"] = "0.8.25"
    write_build_info(root, document=base)
    with pytest.raises(ValueError, match="unambiguous"):
        accept(root, revision, monkeypatch)


def test_source_mapping_and_artifact_content_mismatch_are_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    write_build_info(root)
    artifact = root / "out/build-info/build.json"
    payload = json.loads(artifact.read_text())
    payload["output"]["sources"] = {"contracts/Other.sol": {"ast": ast()}}
    artifact.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="mapping"):
        accept(root, revision, monkeypatch)
    payload["output"]["sources"] = {"contracts/Vault.sol": {"ast": ast()}}
    payload["input"]["sources"]["contracts/Vault.sol"]["content"] = "tampered"
    artifact.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="content"):
        accept(root, revision, monkeypatch)


def test_artifact_hash_mismatch_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    artifact = write_build_info(root)
    gateway, request, result = gateway_result(root, monkeypatch)
    artifact.write_text(artifact.read_text() + " ")
    with pytest.raises(ValueError, match="hash"):
        accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision, expected_request=request, execution_result=result, execution_gateway=gateway)


@pytest.mark.parametrize("path", ["out/build-info/reports/build.json", "out/build-info/findings/build.json", "out/build-info/leaderboard/build.json", "out/build-info/remediation/build.json"])
def test_prohibited_build_artifact_paths_are_rejected(tmp_path, path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    write_build_info(root, path=path)
    with pytest.raises(ValueError, match="prohibited"):
        accept(root, revision, monkeypatch)


def test_fabricated_build_result_is_rejected(tmp_path):
    root, revision = fixture_checkout(tmp_path)
    write_build_info(root)
    fabricated = BuildResult("SUCCEEDED", ("forge", "build", "--build-info"), 0, "", "",
                             BuildProfile("foundry", ("forge", "build", "--build-info"), ("out", "build-info")), {}, ())
    with pytest.raises(TypeError, match="gateway-owned"):
        accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision,
                                  expected_request=ExecutionRequest("fake", "foundry", str(root), ("forge", "build", "--build-info"), None, "auth-1"),
                                  execution_result=fabricated, execution_gateway=ExternalExecutionGateway())


def test_failed_foundry_build_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    write_build_info(root)
    gateway, request, result = gateway_result(root, monkeypatch, returncode=1)
    with pytest.raises(ValueError, match="successful"):
        accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision,
                                  expected_request=request, execution_result=result, execution_gateway=gateway)


def test_trusted_result_for_different_target_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    (tmp_path / "other").mkdir()
    other, _ = fixture_checkout(tmp_path / "other")
    write_build_info(root)
    write_build_info(other)
    gateway, request, result = gateway_result(other, monkeypatch)
    with pytest.raises(ValueError, match="request does not match"):
        accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision,
                                  expected_request=request, execution_result=result, execution_gateway=gateway)


def test_trusted_result_for_different_request_is_rejected(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    write_build_info(root)
    gateway, request, result = gateway_result(root, monkeypatch, execution_id="other-request")
    expected = ExecutionRequest("expected-request", "foundry", str(root), ("forge", "build", "--build-info"), None, "auth-1")
    with pytest.raises(ValueError, match="expected execution request"):
        accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision,
                                  expected_request=expected, execution_result=result, execution_gateway=gateway)


def test_rehydrated_foundry_result_is_authenticated_without_execution(tmp_path, monkeypatch):
    root, revision = fixture_checkout(tmp_path)
    write_build_info(root)
    gateway, request, result = gateway_result(root, monkeypatch)
    states = {request.digest: "COMPLETED"}
    recovered_gateway = ExternalExecutionGateway(get_execution_state=lambda request: states.get(request.digest))
    recovered_gateway.register("foundry", FoundryBuildAdapter())
    recovered = ExecutionRecoveryService(
        gateway=recovered_gateway,
        load_request=lambda execution_id: request,
        load_result=lambda digest: result.canonical_payload(),
        get_state=lambda digest: states.get(digest),
    ).recover(execution_id=request.execution_id, request_digest=request.digest, adapter="foundry")
    accepted = accept_foundry_build_info(checkout=root, repository=REPOSITORY, expected_revision=revision,
                                         expected_request=request, execution_result=recovered.result, execution_gateway=recovered_gateway)
    assert accepted.receipt.forge_version == result.forge_version
