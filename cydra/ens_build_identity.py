"""ENS snapshot build-identity evidence.

This module records immutable metadata observed in the public contest snapshot.
It deliberately stops short of claiming that the snapshot is cryptographically
identical to the published audited Git object or that a clean build has run.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ens_source_identity import (
    ENS_SOURCE_ORIGIN_REPOSITORY,
    ENS_SOURCE_SNAPSHOT_COMMIT,
)
from .ens_target import AUDITED_REVISION, DEFAULT_REPOSITORY

ENS_NODE_REQUIREMENT = "22"
ENS_PNPM_VERSION = "10.27.0"
ENS_PACKAGE_JSON_SHA = "6ffda56eccda0d11b6cf44dd826e40e1549ad482"
ENS_PNPM_LOCK_SHA = "e5b5f78fbdc98d1582506737133c618a53d6ec20"
ENS_PNPM_WORKSPACE_SHA = "7db28db28ea4691c27112ce7aed1bc13d073da6b"
ENS_NPMRC_SHA = "0a2aa731fe65ecaddd36fb6900d09664fb3964c1"


@dataclass(frozen=True)
class ENSBuildIdentityEvidence:
    repository: str
    audited_revision: str
    snapshot_commit: str
    origin_repository: str
    node_requirement: str
    pnpm_version: str
    package_json_sha: str
    pnpm_lock_sha: str
    pnpm_workspace_sha: str
    npmrc_sha: str
    status: str

    @property
    def source_lineage_declared(self) -> bool:
        return (
            self.repository == DEFAULT_REPOSITORY
            and self.origin_repository == ENS_SOURCE_ORIGIN_REPOSITORY
            and self.snapshot_commit == ENS_SOURCE_SNAPSHOT_COMMIT
            and self.audited_revision == AUDITED_REVISION
        )

    @property
    def build_verified(self) -> bool:
        return False


def declared_build_identity() -> ENSBuildIdentityEvidence:
    """Return snapshot metadata without promoting it to a verified build."""
    return ENSBuildIdentityEvidence(
        repository=DEFAULT_REPOSITORY,
        audited_revision=AUDITED_REVISION,
        snapshot_commit=ENS_SOURCE_SNAPSHOT_COMMIT,
        origin_repository=ENS_SOURCE_ORIGIN_REPOSITORY,
        node_requirement=ENS_NODE_REQUIREMENT,
        pnpm_version=ENS_PNPM_VERSION,
        package_json_sha=ENS_PACKAGE_JSON_SHA,
        pnpm_lock_sha=ENS_PNPM_LOCK_SHA,
        pnpm_workspace_sha=ENS_PNPM_WORKSPACE_SHA,
        npmrc_sha=ENS_NPMRC_SHA,
        status="BUILD_IDENTITY_UNRESOLVED",
    )
