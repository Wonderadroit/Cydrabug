from cydra.source_provider import (
    ObservationStrength,
    SourceObservation,
    SourceObservationKind,
)


def test_source_observation_preserves_provider_and_strength():
    observation = SourceObservation(
        observation_id="function:apps/manager/src/a.ts:10:send",
        kind=SourceObservationKind.FUNCTION,
        path="apps/manager/src/a.ts",
        name="send",
        attributes={"line": 10},
        provider="typescript",
        tool="typescript-compiler-api",
        tool_version="7.0.0-dev",
        strength=ObservationStrength.COMPILER,
        provenance=("sha256:example",),
        scope_state="IN_SCOPE",
    )

    assert observation.kind is SourceObservationKind.FUNCTION
    assert observation.strength is ObservationStrength.COMPILER
    assert observation.provider == "typescript"
    assert observation.scope_state == "IN_SCOPE"
    assert observation.provenance == ("sha256:example",)


def test_observation_kind_is_language_neutral():
    assert SourceObservationKind.FUNCTION.value == "function"
    assert SourceObservationKind.EXTERNAL_BOUNDARY.value == "external_boundary"
