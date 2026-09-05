"""ENS audited-source lineage evidence.

The competition publishes an upstream audited commit SHA that is not the same Git
object as the public contest fork's root commit. The fork explicitly declares that
it was created from the audited upstream revision. This module records that fact as
provenance evidence without treating the fork commit as cryptographically identical
to the upstream Git object or as build-verified source identity.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ens_target import AUDITED_REVISION, DEFAULT_REPOSITORY

ENS_SOURCE_ORIGIN_REPOSITORY = "ensdomains/apps-monorepo"
ENS_SOURCE_SNAPSHOT_COMMIT = "cda79acaad59711b943fc68207ebb3f1d0ff8596"
ENS_SOURCE_SNAPSHOT_MESSAGE = (
    "fork ensdomains/apps-monorepo at "
    "63772fd872af472ced58b009499355f3430c2a86"
)


@dataclass(frozen=True)
class ENSSourceLineage:
    repository: str
    audited_revision: str
    snapshot_commit: str
    origin_repository: str
    declaration: str
    status: str

    @property
    def is_exact_git_identity(self) -> bool:
        return self.snapshot_commit == self.audited_revision

    @property
    def build_ready(self) -> bool:
        return False


def declared_source_lineage() -> ENSSourceLineage:
    """Return project-declared lineage evidence without promoting it to audit-ready."""
    return ENSSourceLineage(
        repository=DEFAULT_REPOSITORY,
        audited_revision=AUDITED_REVISION,
        snapshot_commit=ENS_SOURCE_SNAPSHOT_COMMIT,
        origin_repository=ENS_SOURCE_ORIGIN_REPOSITORY,
        declaration=ENS_SOURCE_SNAPSHOT_MESSAGE,
        status="DECLARED_SNAPSHOT_LINEAGE",
    )
