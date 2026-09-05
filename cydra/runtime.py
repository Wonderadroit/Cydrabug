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


def _os_release() -> str:
    try:
        return open("/etc/os-release", encoding="utf-8").read().lower()
    except OSError:
        return ""


def _is_ubuntu(release: str) -> bool:
    return any(line.strip() in {"id=ubuntu", 'id="ubuntu"'} for line in release.splitlines())


def detect_runtime(*, require_proot: bool = True) -> RuntimeReport:
    """Inspect the supported Linux runtime without changing the host.

    Android's kernel can be reported by ``platform.system()`` even while Python is
    executing inside a PRoot Ubuntu userspace. CYDRA therefore treats the userspace
    identity as the relevant runtime boundary and records the kernel-reported host
    separately.
    """
    kernel_system = platform.system().lower()
    architecture = platform.machine().lower()
    release = _os_release()
    ubuntu = _is_ubuntu(release)
    proot_ok, proot_version = _run(("proot", "--version"))
    userspace_linux = ubuntu or (kernel_system == "linux" and bool(release))
    python_ok, python_version = _run(("python", "--version"))
    git_ok, git_version = _run(("git", "--version"))

    capabilities = (
        Capability("linux", True, userspace_linux, "linux" if userspace_linux else kernel_system, "CYDRA production runtime is Linux-first"),
        Capability("ubuntu", True, ubuntu, "ubuntu" if ubuntu else None, "first supported CYDRA production profile is Ubuntu"),
        Capability("proot", require_proot, proot_ok, proot_version, "first supported mobile runtime uses PRoot"),
        Capability("python", True, python_ok, python_version, "CYDRA core runtime"),
        Capability("git", True, git_ok, git_version, "source acquisition and provenance"),
    )
    profile = "proot-ubuntu" if userspace_linux and ubuntu and proot_ok else "unsupported"
    return RuntimeReport(profile, kernel_system, architecture, capabilities)


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
