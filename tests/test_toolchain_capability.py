import os

from cydra.target_environment import TargetRequirement, verify_requirements
from cydra.toolchain_capability import resolve_executable


def test_required_tool_can_be_observed_from_target_local_node_bin(tmp_path):
    local_bin = tmp_path / "node_modules" / ".bin"
    local_bin.mkdir(parents=True)
    executable = local_bin / "tsgo"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' '7.0.0-dev.20260421.2'\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | os.X_OK)

    report = verify_requirements(
        tmp_path,
        (TargetRequirement("tsgo", "compiler", "7.0.0-dev.20260421.2", "test", True, "PROJECT", "canonical-build"),),
    )

    capability = report.capabilities[0]
    assert report.ready
    assert capability.available
    assert capability.observed == "7.0.0-dev.20260421.2"


def test_workspace_package_local_tool_is_observed(tmp_path):
    package = tmp_path / "apps" / "manager"
    local_bin = package / "node_modules" / ".bin"
    local_bin.mkdir(parents=True)
    (package / "package.json").write_text("{}", encoding="utf-8")
    executable = local_bin / "tsgo"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' '7.0.0-dev.20260421.2'\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | os.X_OK)

    resolved = resolve_executable(tmp_path, "tsgo")

    assert resolved == str(executable)

    report = verify_requirements(
        tmp_path,
        (TargetRequirement("tsgo", "compiler", "7.0.0-dev.20260421.2", "test", True, "PROJECT", "canonical-build"),),
    )
    assert report.ready
    assert report.capabilities[0].observed == "7.0.0-dev.20260421.2"


def test_missing_target_local_tool_remains_blocked(tmp_path):
    report = verify_requirements(
        tmp_path,
        (TargetRequirement("tsgo", "compiler", "7.0.0-dev.20260421.2", "test", True, "PROJECT", "canonical-build"),),
    )

    assert not report.ready
    assert report.missing_required == ("tsgo",)
