"""CYDRA host-runtime capability detection.

This is an executable boundary, not documentation. It answers whether the host can
run CYDRA's base runtime and records observed capabilities without installing or
executing arbitrary target software.
"""
from __future__ import annotations

from dataclasses import dataclass
import platform
import shutil
import subprocess
from typing import Sequence


@dataclass(frozen=True)
class Capability:
    name: str
    required: bool
    available: bool
    observed: str | None
    reason: str


@dataclass(frozen=True)
class RuntimeReport:
    profile: str
    platform: str
    architecture: str
    capabilities: tuple[Capability, ...]

    @property
    def ready(self) -> bool:
        return all(c.available for c in self.capabilities if c.required)

    @property
    def missing_required(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.capabilities if c.required and not c.available)


def _run(argv: Sequence[str], timeout: int = 10) -> tuple[bool, str | None]:
    executable = shutil.which(argv[0])
    if executable is None:
        return False, None
    try:
        result = subprocess.run(
            [executable, *argv[1:]],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, None
    text = (result.stdout or result.stderr).strip()
    return result.returncode == 0, (text.splitlines()[0][:500] if text else None)


def detect_runtime(*, require_proot: bool = True) -> RuntimeReport:
    """Inspect the supported Linux runtime without changing the host."""
    system = platform.system().lower()
    architecture = platform.machine().lower()
    proot_ok, proot_version = _run(("proot", "--version"))
    ubuntu = False
    try:
        release = open("/etc/os-release", encoding="utf-8").read().lower()
        ubuntu = "id=ubuntu" in release or "id=ubuntu\n" in release
    except OSError:
        pass

    capabilities = (
        Capability("linux", True, system == "linux", system, "CYDRA production runtime is Linux-first"),
        Capability("ubuntu", True, ubuntu, "ubuntu" if ubuntu else None, "first supported CYDRA production profile is Ubuntu"),
        Capability("proot", require_proot, proot_ok, proot_version, "first supported mobile runtime uses PRoot"),
        Capability("python", True, _run(("python", "--version"))[0], _run(("python", "--version"))[1], "CYDRA core runtime"),
        Capability("git", True, _run(("git", "--version"))[0], _run(("git", "--version"))[1], "source acquisition and provenance"),
    )
    profile = "proot-ubuntu" if system == "linux" and ubuntu and proot_ok else "unsupported"
    return RuntimeReport(profile, system, architecture, capabilities)


def format_report(report: RuntimeReport) -> str:
    lines = [
        "CYDRA RUNTIME",
        f"profile: {report.profile}",
        f"platform: {report.platform}",
        f"architecture: {report.architecture}",
        f"status: {'READY' if report.ready else 'BLOCKED'}",
    ]
    for capability in report.capabilities:
        mark = "PASS" if capability.available else "FAIL"
        requirement = "required" if capability.required else "optional"
        observed = f" [{capability.observed}]" if capability.observed else ""
        lines.append(f"{mark} {capability.name} ({requirement}){observed} — {capability.reason}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report(detect_runtime()))
