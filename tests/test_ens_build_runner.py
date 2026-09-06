from pathlib import Path

from cydra.ens_build_identity import (
    ENS_NPMRC_SHA,
    ENS_PACKAGE_JSON_SHA,
    ENS_PNPM_LOCK_SHA,
    ENS_PNPM_WORKSPACE_SHA,
    ENS_PNPM_VERSION,
)
from cydra.ens_build_runner import CANONICAL_COMMANDS, preflight_ens_environment, run_ens_build


HASHES = {
    "package.json": ENS_PACKAGE_JSON_SHA,
    "pnpm-lock.yaml": ENS_PNPM_LOCK_SHA,
    "pnpm-workspace.yaml": ENS_PNPM_WORKSPACE_SHA,
    ".npmrc": ENS_NPMRC_SHA,
}


def _fake_tools(monkeypatch, head, tree, clean=True, hashes=None):
    def fake_which(name):
        return f"/usr/bin/{name}"

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(argv, **kwargs):
        command = list(argv)
        if command[:2] == ["git", "rev-parse"]:
            ref = command[-1]
            if ref == "HEAD^{tree}":
                Result.stdout = tree
            elif ref.startswith("HEAD:"):
                Result.stdout = (hashes or {}).get(ref[5:], "")
            else:
                Result.stdout = head
        elif command[:3] == ["git", "status", "--porcelain"]:
            Result.stdout = "" if clean else " M package.json"
        elif command == ["node", "--version"]:
            Result.stdout = "v22.23.2"
        elif command == ["pnpm", "--version"]:
            Result.stdout = ENS_PNPM_VERSION
        else:
            Result.stdout = ""
        return Result()

    monkeypatch.setattr("cydra.ens_build_runner.shutil.which", fake_which)
    monkeypatch.setattr("cydra.ens_build_runner.subprocess.run", fake_run)
    monkeypatch.setattr("cydra.target_environment.shutil.which", fake_which)
    monkeypatch.setattr(
        "cydra.target_environment._version",
        lambda executable: "v22.23.2" if executable == "node" else ENS_PNPM_VERSION,
    )


def _make_checkout(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    for name in HASHES:
        (tmp_path / name).write_text(name, encoding="utf-8")
    return tmp_path


def test_preflight_reports_authoritative_ens_tools_without_running_build(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path)
    _fake_tools(
        monkeypatch,
        "cda79acaad59711b943fc68207ebb3f1d0ff8596",
        "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba",
        hashes=HASHES,
    )

    report = preflight_ens_environment(target)

    assert report.ready
    assert [(c.requirement.name, c.available) for c in report.capabilities] == [
        ("node", True),
        ("pnpm", True),
    ]


def test_runner_does_not_execute_contest_commands_when_required_tool_missing(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path)
    calls = []

    monkeypatch.setattr("cydra.target_environment.shutil.which", lambda name: None)
    monkeypatch.setattr("cydra.target_environment._version", lambda executable: None)
    monkeypatch.setattr("cydra.ens_build_runner.shutil.which", lambda name: calls.append(name) or f"/usr/bin/{name}")

    def unexpected_run(*args, **kwargs):
        calls.append("EXECUTED")
        raise AssertionError("canonical contest command executed despite failed preflight")

    monkeypatch.setattr("cydra.ens_build_runner.subprocess.run", unexpected_run)

    run = run_ens_build(target)

    assert not run.verified
    assert run.commands == ()
    assert not run.environment.ready
    assert run.environment.missing_required == ("node", "pnpm")
    assert "EXECUTED" not in calls


def test_runner_produces_verified_receipt_from_matching_observations(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path)
    _fake_tools(
        monkeypatch,
        "cda79acaad59711b943fc68207ebb3f1d0ff8596",
        "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba",
        hashes=HASHES,
    )

    run = run_ens_build(target)

    assert run.verified
    assert run.receipt.verified
    assert [item.command for item in run.commands] == list(CANONICAL_COMMANDS)


def test_runner_executes_only_canonical_commands_and_persists_receipt(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path)
    _fake_tools(
        monkeypatch,
        "cda79acaad59711b943fc68207ebb3f1d0ff8596",
        "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba",
        hashes=HASHES,
    )

    run = run_ens_build(target, receipt_path=tmp_path / "evidence" / "ens-build.json")

    assert [item.command for item in run.commands] == list(CANONICAL_COMMANDS)
    assert all(item.returncode == 0 for item in run.commands)
    assert run.verified
    assert run.receipt.snapshot_commit == "cda79acaad59711b943fc68207ebb3f1d0ff8596"
    assert (tmp_path / "evidence" / "ens-build.json").is_file()


def test_runner_stops_at_first_failed_canonical_command(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path)
    _fake_tools(
        monkeypatch,
        "cda79acaad59711b943fc68207ebb3f1d0ff8596",
        "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba",
        hashes=HASHES,
    )

    calls = []
    original = __import__("cydra.ens_build_runner", fromlist=["_run"])._run

    def fake_run(root, command, timeout):
        calls.append(tuple(command))
        observation = original(root, command, timeout)
        if tuple(command) == ("pnpm", "check"):
            from cydra.ens_build_runner import CommandObservation

            return CommandObservation(tuple(command), 1, "FAILED")
        return observation

    monkeypatch.setattr("cydra.ens_build_runner._run", fake_run)
    run = run_ens_build(target)

    assert calls == list(CANONICAL_COMMANDS[:2])
    assert not run.verified
    assert run.commands[-1].command == ("pnpm", "check")
    assert run.commands[-1].returncode == 1
