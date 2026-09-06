from pathlib import Path

from cydra.ens_build_identity import ENS_NPMRC_SHA, ENS_PACKAGE_JSON_SHA, ENS_PNPM_LOCK_SHA, ENS_PNPM_VERSION, ENS_PNPM_WORKSPACE_SHA, ENS_TSGO_VERSION
from cydra.ens_build_runner import CANONICAL_COMMANDS, preflight_ens_environment, run_ens_build

HASHES = {"package.json": ENS_PACKAGE_JSON_SHA, "pnpm-lock.yaml": ENS_PNPM_LOCK_SHA, "pnpm-workspace.yaml": ENS_PNPM_WORKSPACE_SHA, ".npmrc": ENS_NPMRC_SHA}


def _fake_tools(monkeypatch, head, tree, clean=True, hashes=None):
    def fake_which(name): return f"/usr/bin/{name}"
    class Result:
        returncode = 0; stdout = ""; stderr = ""
    def fake_run(argv, **kwargs):
        command = list(argv)
        if command[:2] == ["git", "rev-parse"]:
            ref = command[-1]; Result.stdout = tree if ref == "HEAD^{tree}" else ((hashes or {}).get(ref[5:], "") if ref.startswith("HEAD:") else head)
        elif command[:3] == ["git", "status", "--porcelain"]: Result.stdout = "" if clean else " M package.json"
        elif command == ["node", "--version"]: Result.stdout = "v22.23.2"
        elif command == ["pnpm", "--version"]: Result.stdout = ENS_PNPM_VERSION
        elif command == ["tsgo", "--version"]: Result.stdout = ENS_TSGO_VERSION
        else: Result.stdout = ""
        return Result()
    monkeypatch.setattr("cydra.ens_build_runner.shutil.which", fake_which)
    monkeypatch.setattr("cydra.ens_build_runner.subprocess.run", fake_run)
    monkeypatch.setattr("cydra.target_environment.observe_version", lambda root, name: {"node": "v22.23.2", "pnpm": ENS_PNPM_VERSION, "tsgo": ENS_TSGO_VERSION}[name])
    monkeypatch.setattr("cydra.target_environment.subprocess.run", fake_run)
    monkeypatch.setattr("cydra.ens_build_runner.observe_version", lambda root, name: {"node": "v22.23.2", "pnpm": ENS_PNPM_VERSION, "tsgo": ENS_TSGO_VERSION}[name])


def _make_checkout(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    for name in HASHES: (tmp_path / name).write_text(name, encoding="utf-8")
    return tmp_path


def test_preflight_checks_only_bootstrap_tools(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path); _fake_tools(monkeypatch, "cda79acaad59711b943fc68207ebb3f1d0ff8596", "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba", hashes=HASHES)
    report = preflight_ens_environment(target)
    assert report.ready
    assert [(c.requirement.name, c.available) for c in report.capabilities] == [("node", True), ("pnpm", True)]


def test_runner_blocks_before_materialization_when_bootstrap_tool_missing(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path); calls = []
    monkeypatch.setattr("cydra.target_environment.observe_version", lambda root, name: None)
    monkeypatch.setattr("cydra.ens_build_runner.shutil.which", lambda name: calls.append(name) or f"/usr/bin/{name}")
    def unexpected_run(*args, **kwargs): calls.append("EXECUTED"); raise AssertionError("materialization executed despite failed bootstrap")
    monkeypatch.setattr("cydra.ens_build_runner.subprocess.run", unexpected_run); monkeypatch.setattr("cydra.target_environment.subprocess.run", unexpected_run)
    run = run_ens_build(target)
    assert not run.verified and run.commands[0].command == ("pnpm", "install", "--frozen-lockfile") and run.commands[0].returncode == 127
    assert run.preparation.materialization_status == "BOOTSTRAP_BLOCKED" and not run.environment.ready and "EXECUTED" not in calls


def test_runner_materializes_before_verifying_target_local_tool(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path); installed = {"value": False}
    monkeypatch.setattr("cydra.ens_build_runner.shutil.which", lambda name: f"/usr/bin/{name}")
    class Result:
        returncode = 0; stdout = ""; stderr = ""
    def runner_run(argv, **kwargs):
        command = list(argv)
        if command == ["pnpm", "install", "--frozen-lockfile"]: installed["value"] = True
        if command == ["node", "--version"]: Result.stdout = "v22.23.2"
        elif command == ["pnpm", "--version"]: Result.stdout = ENS_PNPM_VERSION
        elif command == ["tsgo", "--version"]: Result.stdout = ENS_TSGO_VERSION
        elif command[:2] == ["git", "rev-parse"]: Result.stdout = "cda79acaad59711b943fc68207ebb3f1d0ff8596" if command[-1] != "HEAD^{tree}" else "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba"
        elif command[:3] == ["git", "status", "--porcelain"]: Result.stdout = ""
        elif command[-1].startswith("HEAD:"): Result.stdout = HASHES[command[-1][5:]]
        else: Result.stdout = ""
        return Result()
    monkeypatch.setattr("cydra.ens_build_runner.subprocess.run", runner_run); monkeypatch.setattr("cydra.target_environment.subprocess.run", runner_run)
    def observe(root, name):
        if name == "tsgo" and not installed["value"]: return None
        return {"node": "v22.23.2", "pnpm": ENS_PNPM_VERSION, "tsgo": ENS_TSGO_VERSION}[name]
    monkeypatch.setattr("cydra.target_environment.observe_version", observe); monkeypatch.setattr("cydra.ens_build_runner.observe_version", observe)
    run = run_ens_build(target)
    assert run.preparation.materialization_returncode == 0 and run.environment.ready
    assert run.commands[0].command == ("pnpm", "install", "--frozen-lockfile") and run.commands[1].command == CANONICAL_COMMANDS[1]


def test_runner_executes_only_canonical_commands_and_persists_receipt(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path); _fake_tools(monkeypatch, "cda79acaad59711b943fc68207ebb3f1d0ff8596", "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba", hashes=HASHES)
    run = run_ens_build(target, receipt_path=tmp_path / "evidence" / "ens-build.json")
    assert [item.command for item in run.commands] == list(CANONICAL_COMMANDS) and all(item.returncode == 0 for item in run.commands)
    assert run.verified and run.receipt.snapshot_commit == "cda79acaad59711b943fc68207ebb3f1d0ff8596" and (tmp_path / "evidence" / "ens-build.json").is_file()
    assert run.receipt.tsgo_version == ENS_TSGO_VERSION


def test_runner_stops_at_first_failed_canonical_command(monkeypatch, tmp_path):
    target = _make_checkout(tmp_path); _fake_tools(monkeypatch, "cda79acaad59711b943fc68207ebb3f1d0ff8596", "8e0d79dac1ab4b4fdb80d6afed810087ae9f00ba", hashes=HASHES)
    calls = []
    def fake_run(root, command, timeout):
        calls.append(tuple(command))
        from cydra.ens_build_runner import CommandObservation
        return CommandObservation(tuple(command), 1, "FAILED") if tuple(command) == ("pnpm", "check") else CommandObservation(tuple(command), 0, "SUCCEEDED")
    monkeypatch.setattr("cydra.ens_build_runner._run", fake_run)
    run = run_ens_build(target)
    assert calls == list(CANONICAL_COMMANDS[1:2]) and not run.verified and run.commands[-1].returncode == 1
