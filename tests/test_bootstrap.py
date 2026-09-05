from pathlib import Path

from cydra.bootstrap import build_plan


def test_build_plan_preserves_guest_home_and_binds_repo_explicitly(tmp_path, monkeypatch):
    home = tmp_path / "home"
    repo = home / "cydra-bridge" / "workspace" / "cydrabug"
    repo.mkdir(parents=True)
    monkeypatch.setattr("cydra.bootstrap.Path.home", lambda: home)

    plan = build_plan(repo, container="ubuntu")

    assert not plan.shared_home
    assert plan.guest_repository == "/workspace/cydrabug"
    assert plan.command[:5] == ("proot-distro", "login", "ubuntu", "--bind", f"{repo.resolve()}:/workspace/cydrabug")
    assert plan.command[-3] == "bash"
    assert plan.command[-2] == "-lc"
    assert plan.command[-1].endswith("exec python3 -m cydra.doctor")
    assert ". \"$HOME/.nvm/nvm.sh\"" in plan.command[-1]


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
    assert plan.command[-3] == "bash"
    assert plan.command[-2] == "-lc"
    assert plan.command[-1].endswith("exec bash -lc pwd")


def test_build_plan_maps_target_into_guest_workspace(tmp_path):
    repo = tmp_path / "cydrabug"
    target = tmp_path / "ens-audit-snapshot"
    repo.mkdir()
    target.mkdir()

    command = ("python3", "-m", "cydra.doctor", "--target", target.resolve().as_posix())
    plan = build_plan(repo, container="ubuntu", command=command, target=target)

    assert plan.target == target.resolve()
    assert plan.guest_target == "/workspace/target"
    assert plan.binds == (
        (repo.resolve(), "/workspace/cydrabug"),
        (target.resolve(), "/workspace/target"),
    )
    assert plan.command[-1].endswith(
        "exec python3 -m cydra.doctor --target /workspace/target"
    )
    assert f"{target.resolve()}:/workspace/target" in plan.command


def test_build_plan_rejects_missing_target(tmp_path):
    repo = tmp_path / "cydrabug"
    repo.mkdir()
    missing = tmp_path / "ens-audit-snapshot"

    try:
        build_plan(repo, target=missing)
    except ValueError as exc:
        assert "target directory does not exist" in str(exc)
    else:
        raise AssertionError("missing target should be rejected")


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
