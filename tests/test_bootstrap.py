from pathlib import Path

from cydra.bootstrap import build_plan


def test_build_plan_uses_shared_home_for_repo_under_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    repo = home / "cydra-bridge" / "workspace" / "cydrabug"
    repo.mkdir(parents=True)
    monkeypatch.setattr("cydra.bootstrap.Path.home", lambda: home)

    plan = build_plan(repo, container="ubuntu")

    assert plan.shared_home
    assert plan.guest_repository == "/root/cydra-bridge/workspace/cydrabug"
    assert plan.command[:5] == ("proot-distro", "login", "ubuntu", "--shared-home", "--work-dir")
    assert plan.command[-3:] == ("python3", "-m", "cydra.doctor")


def test_build_plan_binds_repo_outside_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    repo = tmp_path / "external" / "cydrabug"
    home.mkdir()
    repo.mkdir(parents=True)
    monkeypatch.setattr("cydra.bootstrap.Path.home", lambda: home)

    plan = build_plan(repo, container="ubuntu", command=("bash", "-lc", "pwd"))

    assert not plan.shared_home
    assert plan.guest_repository == "/workspace/cydrabug"
    assert "--bind" in plan.command
    bind_index = plan.command.index("--bind")
    assert plan.command[bind_index + 1] == f"{Path(repo).resolve()}:/workspace/cydrabug"
    assert plan.command[-3:] == ("bash", "-lc", "pwd")
