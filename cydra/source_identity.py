"""General source acquisition and exact Git identity verification."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse

from .source_lineage import SourceCandidate


@dataclass(frozen=True)
class SourceIdentityReceipt:
    repository_locator: str
    repository: str
    requested_revision: str
    checkout_path: str
    observed_revision: str | None
    advertised_revision_available: bool
    working_tree_clean: bool
    target_paths: tuple[str, ...]
    missing_target_paths: tuple[str, ...]
    status: str
    reason: str

    @property
    def verified(self) -> bool:
        return self.status == "VERIFIED"

    def to_candidate(self) -> SourceCandidate:
        """Convert acquisition facts into generic lineage evidence."""
        return SourceCandidate(
            locator=self.repository_locator,
            observed_revision=self.observed_revision,
            advertised_revision_available=self.advertised_revision_available,
            observed_head_matches=(
                self.status == "VERIFIED"
                and self.observed_revision is not None
                and self.observed_revision.lower() == self.requested_revision.lower()
            ),
            contradictory_identity=self.status == "MISMATCH",
        )


def repository_locator(locator: str) -> str:
    """Normalize a supported repository/tree/blob locator to its repository URL."""
    parsed = urlparse(locator.strip())
    if parsed.scheme == "file" and parsed.path:
        return locator.split("?", 1)[0].split("#", 1)[0]
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("repository locator must be an HTTPS URL or local file URL")

    host = parsed.hostname.lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host == "github.com":
        if len(parts) < 2:
            raise ValueError("GitHub locator does not identify a repository")
        repository = parts[1].removesuffix(".git")
        return f"https://github.com/{parts[0]}/{repository}.git"

    if parsed.path.endswith(".git"):
        return locator.split("?", 1)[0].split("#", 1)[0]

    raise ValueError(f"unsupported repository locator host: {parsed.hostname}")


def target_path(locator: str) -> str | None:
    """Extract a repository-relative path from a GitHub tree/blob locator."""
    parsed = urlparse(locator.strip())
    if parsed.hostname and parsed.hostname.lower() == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 4 and parts[2] in {"tree", "blob"}:
            return "/".join(parts[4:]) or None
    return None


def _run_git(path: Path, *args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _git_available() -> bool:
    return shutil.which("git") is not None


def _receipt(*, repository_locator_value: str, repo_url: str, revision: str,
             destination: Path, observed_revision: str | None,
             advertised_revision_available: bool, target_paths: tuple[str, ...],
             missing_target_paths: tuple[str, ...], status: str, reason: str,
             working_tree_clean: bool = False) -> SourceIdentityReceipt:
    return SourceIdentityReceipt(
        repository_locator=repository_locator_value,
        repository=repo_url,
        requested_revision=revision,
        checkout_path=str(destination),
        observed_revision=observed_revision,
        advertised_revision_available=advertised_revision_available,
        working_tree_clean=working_tree_clean,
        target_paths=target_paths,
        missing_target_paths=missing_target_paths,
        status=status,
        reason=reason,
    )


def acquire_and_verify_source(repository_locator_value: str, revision: str,
                              checkout_path: str | Path, *,
                              target_paths: tuple[str, ...] = ()) -> SourceIdentityReceipt:
    """Acquire a repository locally and verify its exact requested Git revision.

    A missing advertised commit is UNRESOLVED, not a mismatch. This distinction
    matters for fork/snapshot lineages where a commit declaration may exist but
    the advertised object is not present in the target repository.
    """
    repo_url = repository_locator(repository_locator_value)
    if not revision or len(revision) != 40:
        raise ValueError("revision must be a full 40-character Git commit SHA")
    if not _git_available():
        return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                        revision=revision, destination=Path(checkout_path).resolve(),
                        observed_revision=None, advertised_revision_available=False,
                        target_paths=target_paths, missing_target_paths=target_paths,
                        status="UNRESOLVED", reason="git executable is unavailable")

    destination = Path(checkout_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if not destination.exists():
        clone = subprocess.run(["git", "clone", "--no-checkout", repo_url, str(destination)],
                               capture_output=True, text=True, check=False)
        if clone.returncode != 0:
            return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                            revision=revision, destination=destination, observed_revision=None,
                            advertised_revision_available=False, target_paths=target_paths,
                            missing_target_paths=target_paths, status="UNRESOLVED",
                            reason=(clone.stderr.strip() or "repository could not be acquired")[:1000])

    code, remote, _ = _run_git(destination, "remote", "get-url", "origin")
    if code != 0 or remote != repo_url:
        return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                        revision=revision, destination=destination, observed_revision=None,
                        advertised_revision_available=False, target_paths=target_paths,
                        missing_target_paths=target_paths, status="UNRESOLVED",
                        reason="existing checkout has a different origin repository")

    fetch = subprocess.run(["git", "-C", str(destination), "fetch", "origin", revision, "--depth=1"],
                           capture_output=True, text=True, check=False)
    if fetch.returncode != 0:
        return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                        revision=revision, destination=destination, observed_revision=None,
                        advertised_revision_available=False, target_paths=target_paths,
                        missing_target_paths=target_paths, status="UNRESOLVED",
                        reason=(fetch.stderr.strip() or "advertised Git revision could not be acquired")[:1000])

    code, _, _ = _run_git(destination, "cat-file", "-e", f"{revision}^{{commit}}")
    if code != 0:
        return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                        revision=revision, destination=destination, observed_revision=None,
                        advertised_revision_available=False, target_paths=target_paths,
                        missing_target_paths=target_paths, status="UNRESOLVED",
                        reason="advertised Git commit object is not independently available")

    # The exact object exists locally. Preserve that fact even if later checks fail.
    object_available = True

    checkout = subprocess.run(["git", "-C", str(destination), "checkout", "--detach", revision],
                              capture_output=True, text=True, check=False)
    if checkout.returncode != 0:
        return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                        revision=revision, destination=destination, observed_revision=None,
                        advertised_revision_available=object_available, target_paths=target_paths,
                        missing_target_paths=target_paths, status="UNRESOLVED",
                        reason=(checkout.stderr.strip() or "exact revision could not be checked out")[:1000])

    code, observed, _ = _run_git(destination, "rev-parse", "HEAD")
    if code != 0:
        return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                        revision=revision, destination=destination, observed_revision=None,
                        advertised_revision_available=object_available, target_paths=target_paths,
                        missing_target_paths=target_paths, status="UNRESOLVED",
                        reason="checked-out HEAD could not be resolved")

    code, status_text, _ = _run_git(destination, "status", "--porcelain=v1")
    clean = code == 0 and not status_text
    missing = tuple(path for path in target_paths if not (destination / path).exists())

    if observed != revision:
        status, reason = "MISMATCH", "checkout HEAD differs from requested revision"
    elif not clean:
        status, reason = "UNRESOLVED", "checkout is not clean"
    elif missing:
        status, reason = "UNRESOLVED", "one or more authoritative target paths are absent from the revision"
    else:
        status, reason = "VERIFIED", "repository, exact revision, clean checkout, and target paths verified"

    return _receipt(repository_locator_value=repository_locator_value, repo_url=repo_url,
                    revision=revision, destination=destination, observed_revision=observed,
                    advertised_revision_available=object_available, target_paths=target_paths,
                    missing_target_paths=missing, status=status, reason=reason,
                    working_tree_clean=clean)


__all__ = ["SourceIdentityReceipt", "repository_locator", "target_path", "acquire_and_verify_source"]
