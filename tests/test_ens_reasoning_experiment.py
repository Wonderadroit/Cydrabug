from cydra.ens_reasoning_experiment import run_experiment


def test_experiment_rejects_non_accepted_build_json(tmp_path):
    path = tmp_path / "build.json"
    path.write_text("{}\n", encoding="utf-8")
    try:
        run_experiment(path)
    except ValueError as exc:
        assert "serialized AcceptedFoundryBuild" in str(exc)
    else:
        raise AssertionError("unaccepted build evidence must not enter reasoning")
