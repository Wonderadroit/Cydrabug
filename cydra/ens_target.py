"""ENS live-contest target binding.

This module binds the current Immunefi contest snapshot to the repository resource
that CYDRA is allowed to analyze. It deliberately distinguishes the competition's
published audited revision from whatever public repository currently exposes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

AUDITED_REVISION = "63772fd872af472ced58b009499355f3430c2a86"
DEFAULT_REPOSITORY = "immunefi-team/audit-comp-ens"
DEFAULT_REVISION = "cda79acaad59711b943fc68207ebb3f1d0ff8596"

@dataclass(frozen=True)
class ENSRepositoryBinding:
    repository: str
    audited_revision: str
    available_revision: str | None
    revision_match: bool
    status: str
    reason: str

    @property
    def ready(self) -> bool:
        return self.revision_match and self.available_revision is not None


def bind_repository(*, repository: str = DEFAULT_REPOSITORY,
                     available_revision: str | None = DEFAULT_REVISION,
                     audited_revision: str = AUDITED_REVISION) -> ENSRepositoryBinding:
    """Return a fail-closed binding between Immunefi's audited SHA and a source SHA.

    The public competition snapshot currently identifies an audited SHA that must not
    silently be substituted with a later snapshot. Callers must therefore explicitly
    resolve the exact audited commit before treating the repository as audit-ready.
    """
    if not repository.strip():
        raise ValueError("repository must not be empty")
    if not audited_revision.strip():
        raise ValueError("audited_revision must not be empty")
    if available_revision is None:
        return ENSRepositoryBinding(repository, audited_revision, None, False,
                                    "UNRESOLVED", "exact audited revision has not been resolved")
    matched = available_revision == audited_revision
    return ENSRepositoryBinding(
        repository, audited_revision, available_revision, matched,
        "READY" if matched else "REVISION_MISMATCH",
        "exact audited revision resolved" if matched else
        "available source revision differs from Immunefi audited revision",
    )


def scoped_assets() -> tuple[str, ...]:
    return (
        "apps/manager",
        "apps/portal",
        "workers/api-worker",
        "packages/transaction-manager",
        "packages/smart-account",
    )


def out_of_scope_domains() -> tuple[str, ...]:
    return (
        "ENS smart contracts",
        "subgraph/indexer",
        "NFT metadata service",
    )


def assert_fail_closed(binding: ENSRepositoryBinding) -> None:
    if not binding.ready:
        raise RuntimeError(
            f"ENS source is not audit-ready: {binding.status}: {binding.reason}"
        )
