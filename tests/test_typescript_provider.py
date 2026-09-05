import json
from types import SimpleNamespace

import pytest

from cydra.source_provider import ObservationStrength, SourceObservationKind
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


def test_typescript_provider_fails_closed_when_compiler_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "cydra.typescript_provider.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=42, stdout="", stderr="typescript compiler API unavailable"),
    )
    provider = TypeScriptCompilerProvider(tmp_path)

    with pytest.raises(SourceProviderUnavailable, match="native API"):
        tuple(provider.observe(["src/app.ts"], {"src/app.ts": "export const x = 1;"}))
