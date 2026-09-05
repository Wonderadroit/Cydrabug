from cydra.source_ingestion import project_source_observations
from cydra.source_provider import ObservationStrength, SourceObservation, SourceObservationKind


def test_projection_preserves_provider_strength_scope_and_provenance():
    observation = SourceObservation(
        observation_id="function:src/app.ts:12:transfer",
        kind=SourceObservationKind.FUNCTION,
        path="src/app.ts",
        name="transfer",
        attributes={"line": 12},
        provider="typescript",
        tool="typescript-compiler-api",
        tool_version="7.0.0-dev",
        strength=ObservationStrength.COMPILER,
        provenance=("sha256:source", "revision:audited"),
        scope_state="IN_SCOPE",
    )

    system = project_source_observations([observation])
    node = system.nodes[observation.observation_id]

    assert node.kind == "function"
    assert node.attributes["provider"] == "typescript"
    assert node.attributes["strength"] == "compiler"
    assert node.attributes["scope_state"] == "IN_SCOPE"
    assert node.attributes["provenance"] == ["sha256:source", "revision:audited"]
    assert node.attributes["tool"] == "typescript-compiler-api"
