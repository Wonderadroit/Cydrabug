from cydra.source_ingestion import ingest_source_provider, project_source_observations
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


def test_ingest_source_provider_connects_provider_to_canonical_model():
    class Provider:
        name = "test-provider"

        def observe(self, paths, sources):
            return [
                SourceObservation(
                    observation_id="file:src/app.ts:1:src/app.ts",
                    kind=SourceObservationKind.FILE,
                    path="src/app.ts",
                    name="src/app.ts",
                    provider=self.name,
                    strength=ObservationStrength.STRUCTURAL,
                    scope_state="IN_SCOPE",
                )
            ]

    system = ingest_source_provider(Provider(), ["src/app.ts"], {"src/app.ts": "export const x = 1;"})
    assert "file:src/app.ts:1:src/app.ts" in system.nodes
    assert system.nodes["file:src/app.ts:1:src/app.ts"].attributes["provider"] == "test-provider"


def test_projection_preserves_noncanonical_source_facts_as_observations():
    observations = [
        SourceObservation(
            observation_id="type:src/app.ts:3:User",
            kind=SourceObservationKind.TYPE,
            path="src/app.ts",
            name="User",
            strength=ObservationStrength.COMPILER,
        ),
        SourceObservation(
            observation_id="export:src/app.ts:4:User",
            kind=SourceObservationKind.EXPORT,
            path="src/app.ts",
            name="User",
            strength=ObservationStrength.COMPILER,
        ),
        SourceObservation(
            observation_id="call:src/app.ts:5:transfer",
            kind=SourceObservationKind.CALL,
            path="src/app.ts",
            name="transfer",
            strength=ObservationStrength.COMPILER,
        ),
    ]

    system = project_source_observations(observations)

    assert system.nodes["type:src/app.ts:3:User"].kind == "observation"
    assert system.nodes["type:src/app.ts:3:User"].attributes["source_observation_kind"] == "type"
    assert system.nodes["export:src/app.ts:4:User"].kind == "observation"
    assert system.nodes["export:src/app.ts:4:User"].attributes["source_observation_kind"] == "export"
    assert system.nodes["call:src/app.ts:5:transfer"].kind == "observation"
    assert system.nodes["call:src/app.ts:5:transfer"].attributes["source_observation_kind"] == "call"
