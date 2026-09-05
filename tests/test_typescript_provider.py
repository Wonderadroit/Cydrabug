import pytest

from cydra.source_provider import ObservationStrength, SourceObservationKind
from cydra.typescript_provider import TypeScriptCompilerProvider


def test_typescript_provider_uses_compiler_structure(tmp_path):
    source = tmp_path / "app.ts"
    source.write_text(
        "import { x } from './dep';\n"
        "export function transfer(to: string) { return x(to); }\n"
        "export interface Config { owner: string }\n",
        encoding="utf-8",
    )

    try:
        observations = tuple(TypeScriptCompilerProvider().observe([str(source)], {}))
    except RuntimeError as exc:
        pytest.skip(str(exc))

    kinds = {observation.kind for observation in observations}
    assert SourceObservationKind.FILE in kinds
    assert SourceObservationKind.IMPORT in kinds
    assert SourceObservationKind.FUNCTION in kinds
    assert SourceObservationKind.TYPE in kinds
    assert all(observation.strength is ObservationStrength.COMPILER for observation in observations)
    assert all(observation.provider == "typescript-compiler" for observation in observations)


def test_typescript_provider_does_not_infer_authorization(tmp_path):
    source = tmp_path / "auth.ts"
    source.write_text(
        "export function requireAuth() { return true; }\n",
        encoding="utf-8",
    )

    try:
        observations = tuple(TypeScriptCompilerProvider().observe([str(source)], {}))
    except RuntimeError as exc:
        pytest.skip(str(exc))

    assert all(observation.kind is not SourceObservationKind.AUTHORIZATION for observation in observations)
