from cydra.ens_source_experiment import run_ens_source_observation_experiment
from cydra.source_provider import ObservationStrength, SourceObservation, SourceObservationKind, SourceRelationship


def test_ens_source_observation_experiment_counts_observations_and_relationships(monkeypatch, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "apps/manager").mkdir(parents=True)
    (target / "apps/manager/a.ts").write_text('export const a = 1;')
    (target / "apps/manager/b.ts").write_text('export const b = 2;')
    inventory = tmp_path / "inventory.txt"
    inventory.write_text("apps/manager/a.ts\napps/manager/b.ts\n")

    observations = (
        SourceObservation(
            "file:apps/manager/a.ts:1:apps/manager/a.ts",
            SourceObservationKind.FILE,
            "apps/manager/a.ts",
            "apps/manager/a.ts",
            provider="test",
            strength=ObservationStrength.COMPILER,
        ),
        SourceObservation(
            "file:apps/manager/b.ts:1:apps/manager/b.ts",
            SourceObservationKind.FILE,
            "apps/manager/b.ts",
            "apps/manager/b.ts",
            provider="test",
            strength=ObservationStrength.COMPILER,
        ),
        SourceObservation(
            "import:apps/manager/a.ts:1:./b",
            SourceObservationKind.IMPORT,
            "apps/manager/a.ts",
            "./b",
            attributes={"resolution_status": "RESOLVED"},
            provider="test",
            strength=ObservationStrength.COMPILER,
            relationships=(SourceRelationship("imports", "file:apps/manager/b.ts:1:apps/manager/b.ts"),),
        ),
        SourceObservation(
            "import:apps/manager/a.ts:2:external",
            SourceObservationKind.IMPORT,
            "apps/manager/a.ts",
            "external",
            attributes={"resolution_status": "UNRESOLVED"},
            provider="test",
            strength=ObservationStrength.COMPILER,
        ),
    )

    class FakeProvider:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, paths, sources):
            return observations

    monkeypatch.setattr("cydra.ens_source_experiment.TypeScriptCompilerProvider", FakeProvider)

    result = run_ens_source_observation_experiment(target, inventory)

    assert result.inventory_files == 2
    assert result.supplied_source_files == 2
    assert result.observation_count == 4
    assert result.node_count == 4
    assert result.edge_count == 1
    assert result.resolved_imports == 1
    assert result.unresolved_imports == 1
    assert result.internal_relationships == 1
