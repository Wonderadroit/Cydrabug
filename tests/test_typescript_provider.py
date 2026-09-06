import json
from types import SimpleNamespace

import pytest

from cydra.source_ingestion import project_source_observations
from cydra.source_provider import ObservationStrength, SourceObservation, SourceObservationKind
from cydra.typescript_provider import SourceProviderUnavailable, TypeScriptCompilerProvider


def test_typescript_provider_normalizes_compiler_structure(monkeypatch, tmp_path):
    payload = {
        "compiler": "typescript-compiler-api",
        "compiler_version": "6.0.0",
        "observations": [
            {"path": "src/app.ts", "kind": "function", "name": "transfer", "line": 7, "attributes": {"parameters": 2}}
        ],
    }
    monkeypatch.setattr(
        "cydra.typescript_provider.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""),
    )
    provider = TypeScriptCompilerProvider(tmp_path, scope_resolver=lambda _: "IN_SCOPE")
    observation = tuple(provider.observe(["src/app.ts"], {"src/app.ts": "export function transfer(a,b) {}"}))[0]

    assert observation.kind is SourceObservationKind.FUNCTION
    assert observation.strength is ObservationStrength.COMPILER
    assert observation.tool == "typescript-compiler-api"
    assert observation.tool_version == "6.0.0"
    assert observation.scope_state == "IN_SCOPE"
    assert observation.attributes["line"] == 7
    assert observation.provenance[0].startswith("sha256:")


def test_typescript_provider_accepts_javascript_family_sources(monkeypatch, tmp_path):
    payload = {
        "compiler": "typescript-compiler-api",
        "compiler_version": "6.0.3",
        "observations": [
            {"path": "src/app.js", "kind": "file", "name": "src/app.js", "line": 1, "attributes": {}},
            {"path": "src/app.js", "kind": "function", "name": "transfer", "line": 1, "attributes": {}},
        ],
    }

    captured = {}

    def run(*args, **kwargs):
        captured["input"] = json.loads(kwargs["input"])
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("cydra.typescript_provider.subprocess.run", run)

    provider = TypeScriptCompilerProvider(tmp_path)
    observations = tuple(provider.observe(
        ["src/app.js"], {"src/app.js": "function transfer() {}"}
    ))

    assert captured["input"]["files"] == [
        {"path": "src/app.js", "source": "function transfer() {}"}
    ]
    assert any(o.kind is SourceObservationKind.FUNCTION for o in observations)


def test_typescript_provider_binds_resolved_import_to_supplied_file(monkeypatch, tmp_path):
    payload = {
        "compiler": "typescript-compiler-api",
        "compiler_version": "6.0.0",
        "observations": [
            {"path": "src/a.ts", "kind": "file", "name": "src/a.ts", "line": 1, "attributes": {}},
            {"path": "src/b.ts", "kind": "file", "name": "src/b.ts", "line": 1, "attributes": {}},
            {"path": "src/a.ts", "kind": "import", "name": "./b", "line": 2,
             "attributes": {"resolved_path": str((tmp_path / "src/b.ts").resolve()), "resolution_status": "RESOLVED"}},
        ],
    }
    monkeypatch.setattr(
        "cydra.typescript_provider.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""),
    )
    provider = TypeScriptCompilerProvider(tmp_path)
    observations = tuple(provider.observe(
        ["src/a.ts", "src/b.ts"], {"src/a.ts": 'import "./b";', "src/b.ts": "export const b = 1;"}
    ))
    import_observation = next(o for o in observations if o.kind is SourceObservationKind.IMPORT)

    assert len(import_observation.relationships) == 1
    assert import_observation.relationships[0].relation == "imports"
    assert import_observation.relationships[0].target_observation_id == "file:src/b.ts:1:src/b.ts"


def test_typescript_provider_fails_closed_when_compiler_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "cydra.typescript_provider.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=42, stdout="", stderr="typescript compiler API unavailable"),
    )
    provider = TypeScriptCompilerProvider(tmp_path)

    with pytest.raises(SourceProviderUnavailable, match="native API"):
        tuple(provider.observe(["src/app.ts"], {"src/app.ts": "export const x = 1;"}))


def test_call_observation_is_preserved_without_inventing_call_edge():
    observation = SourceObservation(
        observation_id="call:src/a.ts:3:send",
        kind=SourceObservationKind.CALL,
        path="src/a.ts",
        name="send",
        attributes={"expression": "send"},
        provider="typescript-compiler",
        tool="typescript-compiler-api",
        tool_version="6.0.3",
        strength=ObservationStrength.COMPILER,
        provenance=("sha256:test",),
    )

    system = project_source_observations((observation,))
    node = system.nodes[observation.observation_id]
    assert node.kind == "observation"
    assert node.attributes["source_observation_kind"] == "call"
    assert node.attributes["strength"] == "compiler"
    assert system.edges == []
