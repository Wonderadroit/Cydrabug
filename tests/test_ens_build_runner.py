from pathlib import Path

from cydra.ens_build_identity import (
    ENS_NPMRC_SHA,
    ENS_PACKAGE_JSON_SHA,
    ENS_PNPM_LOCK_SHA,
    ENS_PNPM_WORKSPACE_SHA,
    ENS_PNPM_VERSION,
)
from cydra.ens_build_runner import CANONICAL_COMMANDS, run_ens_build


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


def _make_checkout(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    for name in HASHES:
        (tmp_path / name).write_text(name, encoding="utf-8")
    return tmp_path


def test_runner_produces_verified_receipt_from_matching_observations(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path)
    _fake_tools(
        monkeypatch,
        "cda79acaad59711b943fc68207ebb3f1d0ff8596",
        "8e0d79dac1ab4b4fdb80d6afed8100879ae9f00ba",
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
        "8e0d79dac1ab4b4fdb80d6afed8100879ae9f00ba",
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
        "8e0d79dac1ab4b4fdb80d6afed8100879ae9f00ba",
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
