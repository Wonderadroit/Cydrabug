"""Authoritative environment requirements for the live ENS contest target."""
from __future__ import annotations

from .ens_build_identity import ENS_NODE_REQUIREMENT, ENS_PNPM_VERSION, ENS_TSGO_VERSION
from .target_environment import TargetRequirement


ENS_NODE_SOURCE = "ENS contest build requirement"
ENS_PNPM_SOURCE = "ENS contest build requirement"
ENS_TSGO_SOURCE = "ENS manager typecheck toolchain requirement"


def authoritative_requirements() -> tuple[TargetRequirement, ...]:
    """Return contest/build requirements that outrank repository CI declarations."""
    return (
        TargetRequirement(
            name="node",
            kind="runtime",
            version=ENS_NODE_REQUIREMENT,
            source=ENS_NODE_SOURCE,
            required=True,
            authority="PLATFORM",
            purpose="canonical-build",
        ),
        TargetRequirement(
            name="pnpm",
            kind="package-manager",
            version=ENS_PNPM_VERSION,
            source=ENS_PNPM_SOURCE,
            required=True,
            authority="PLATFORM",
            purpose="canonical-build",
        ),
        TargetRequirement(
            name="tsgo",
            kind="compiler",
            version=ENS_TSGO_VERSION,
            source=ENS_TSGO_SOURCE,
            required=True,
            authority="PROJECT",
            purpose="canonical-build",
        ),
    )
