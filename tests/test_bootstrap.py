from pathlib import Path

from cydra.bootstrap import build_plan


def test_build_plan_uses_actual_shared_home_path_for_repo_under_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    repo = home / "cydra-bridge" / "workspace" / "cydrabug"
    repo.mkdir(parents=True)
    monkeypatch.setattr("cydra.bootstrap.Path.home", lambda: home)

    plan = build_plan(repo, container="ubuntu")

    assert plan.shared_home
    assert plan.guest_repository == repo.resolve().as_posix()
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


def test_container_exists_uses_machine_readable_container_list(monkeypatch):
    calls = []

    monkeypatch.setattr("cydra.bootstrap._require_executable", lambda name: "/usr/bin/proot-distro")

    class Result:
        returncode = 0
        stdout = "debian\nubuntu\n"

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return Result()

    monkeypatch.setattr("cydra.bootstrap.subprocess.run", fake_run)

    from cydra.bootstrap import _container_exists

    assert _container_exists("ubuntu")
    assert calls == [["proot-distro", "list", "--quiet"]]


def test_container_exists_accepts_active_marker(monkeypatch):
    monkeypatch.setattr("cydra.bootstrap._require_executable", lambda name: "/usr/bin/proot-distro")

    class Result:
        returncode = 0
        stdout = "* ubuntu\ndebian\n"

    monkeypatch.setattr("cydra.bootstrap.subprocess.run", lambda *args, **kwargs: Result())

    from cydra.bootstrap import _container_exists

    assert _container_exists("ubuntu")


def test_container_exists_rejects_unlisted_container(monkeypatch):
    monkeypatch.setattr("cydra.bootstrap._require_executable", lambda name: "/usr/bin/proot-distro")

    class Result:
        returncode = 0
        stdout = "debian\n"

    monkeypatch.setattr("cydra.bootstrap.subprocess.run", lambda *args, **kwargs: Result())

    from cydra.bootstrap import _container_exists

    assert not _container_exists("ubuntu")
