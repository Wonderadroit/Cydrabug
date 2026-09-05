"""ENS audited-source identity and lineage evidence.

The competition publishes an upstream audited commit SHA that is not the same
Git object as the public contest fork's root commit.

The fork declares that it was created from the audited upstream revision.
That declaration is provenance evidence, not cryptographic proof.

This module therefore keeps two separate concepts:

1. declared lineage;
2. independently verified Git identity.

Only the second can produce VERIFIED source identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

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


@dataclass(frozen=True)
class ENSSourceIdentityCheck:
    repository_path: str
    advertised_revision: str
    observed_revision: str | None
    advertised_object_available: bool
    status: str
    reason: str

    @property
    def verified(self) -> bool:
        return self.status == "VERIFIED"


def verify_source_identity(
    repository_path: str | Path,
    *,
    advertised_revision: str = AUDITED_REVISION,
) -> ENSSourceIdentityCheck:
    """Independently evaluate an acquired Git checkout against the advertised SHA.

    A declared fork message is never treated as proof.

    VERIFIED requires the checkout HEAD to be exactly the advertised Git
    commit and for that Git object to be independently available in the
    checkout.

    Missing advertised Git evidence remains UNRESOLVED rather than being
    classified as a mismatch.
    """
    path = Path(repository_path).resolve()

    def git(*args: str) -> tuple[int, str]:
        completed = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.returncode, completed.stdout.strip()

    code, observed = git("rev-parse", "HEAD")

    if code != 0:
        return ENSSourceIdentityCheck(
            repository_path=str(path),
            advertised_revision=advertised_revision,
            observed_revision=None,
            advertised_object_available=False,
            status="UNRESOLVED",
            reason="repository HEAD could not be resolved",
        )

    code, _ = git(
        "cat-file",
        "-e",
        f"{advertised_revision}^{{commit}}",
    )

    if code != 0:
        return ENSSourceIdentityCheck(
            repository_path=str(path),
            advertised_revision=advertised_revision,
            observed_revision=observed,
            advertised_object_available=False,
            status="UNRESOLVED",
            reason=(
                "advertised Git commit object is not independently available"
            ),
        )

    if observed == advertised_revision:
        return ENSSourceIdentityCheck(
            repository_path=str(path),
            advertised_revision=advertised_revision,
            observed_revision=observed,
            advertised_object_available=True,
            status="VERIFIED",
            reason=(
                "repository HEAD exactly matches the advertised "
                "audited revision"
            ),
        )

    return ENSSourceIdentityCheck(
        repository_path=str(path),
        advertised_revision=advertised_revision,
        observed_revision=observed,
        advertised_object_available=True,
        status="MISMATCH",
        reason=(
            "repository HEAD differs from the advertised "
            "audited revision"
        ),
    )


def declared_source_lineage() -> ENSSourceLineage:
    """Return declared lineage without promoting it to verified identity."""
    return ENSSourceLineage(
        repository=DEFAULT_REPOSITORY,
        audited_revision=AUDITED_REVISION,
        snapshot_commit=ENS_SOURCE_SNAPSHOT_COMMIT,
        origin_repository=ENS_SOURCE_ORIGIN_REPOSITORY,
        declaration=ENS_SOURCE_SNAPSHOT_MESSAGE,
        status="DECLARED_SNAPSHOT_LINEAGE",
    )
