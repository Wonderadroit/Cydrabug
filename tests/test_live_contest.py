from cydra.live_contest import AcquisitionIdentityEvidence, acquire_live_contest
from cydra.program_intake import AcquiredResource, ResourceKind, ScopeStatus
from cydra.source_lineage import LineageStatus, SourceCandidate


REVISION = "63772fd872af472ced58b009499355f3430c2a86"
FORK_REVISION = "cda79acaad59711b943fc68207ebb3f1d0ff8596"


class FakeFetcher:
    def __init__(self, repository_links=None):
        self.calls = []
        self.repository_links = repository_links or (
            "https://github.com/example/context-pr",
            "https://github.com/example/target",
        )

    def fetch(self, locator):
        self.calls.append(locator)
        links = " ".join(
            f'<a href="{repository}">repo</a>'
            for repository in self.repository_links
        )
        content = f'<html>{links} audited revision {REVISION}</html>'
        return AcquiredResource(locator, content, "fixture")


def acquire(fetcher, tmp_path):
    return acquire_live_contest(
        "https://immunefi.com/audit-competition/audit-competition-ens/information/",
        fetcher=fetcher,
        receipt_path=tmp_path / "live-contest.json",
    )


def test_live_contest_acquisition_composes_immunefi_intake_and_graph(tmp_path):
    result = acquire(FakeFetcher(), tmp_path)

    assert result.contract.platform == "immunefi"
    assert len(result.acquired) == 3
    assert result.contract.fingerprint
    assert result.graph
    assert result.discovered
    assert any(item.kind is ResourceKind.REPOSITORY for item in result.discovered)
    assert result.source_resolution is not None
    assert result.source_resolution.status is LineageStatus.UNRESOLVED
    assert (tmp_path / "live-contest.json").is_file()


def test_acquisition_preserves_unresolved_identity_evidence(tmp_path):
    result = acquire(FakeFetcher(), tmp_path)

    assert isinstance(result.identity_evidence, AcquisitionIdentityEvidence)
    assert result.identity_evidence.status == "UNRESOLVED"
    assert result.identity_evidence.independent_verification is False
    assert result.identity_evidence.repository_locator is None
    assert result.identity_evidence.acquired_revision is None
    assert result.identity_evidence.advertised_revision == REVISION
    assert "insufficient evidence" in result.identity_evidence.reason

    receipt = (tmp_path / "live-contest.json").read_text()
    assert '"identity_evidence"' in receipt
    assert '"repository_locator": null' in receipt
    assert '"status": "UNRESOLVED"' in receipt
    assert '"source_resolution"' in receipt


def test_discovered_project_resource_does_not_become_authorized(tmp_path):
    result = acquire(FakeFetcher(), tmp_path)

    repo_resources = [r for r in result.graph if r.kind is ResourceKind.REPOSITORY]
    assert repo_resources
    assert all(r.scope is ScopeStatus.UNKNOWN for r in repo_resources)
    assert result.ready_for_active_testing is False


def test_repository_discovery_order_cannot_change_source_identity(tmp_path):
    first = acquire(
        FakeFetcher(
            repository_links=(
                "https://github.com/example/context-pr",
                "https://github.com/example/target",
            )
        ),
        tmp_path,
    )
    second = acquire(
        FakeFetcher(
            repository_links=(
                "https://github.com/example/target",
                "https://github.com/example/context-pr",
            )
        ),
        tmp_path,
    )

    assert first.identity_evidence.repository_locator is None
    assert second.identity_evidence.repository_locator is None
    assert first.identity_evidence.reason == second.identity_evidence.reason
    assert first.source_resolution.status is LineageStatus.UNRESOLVED
    assert second.source_resolution.status is LineageStatus.UNRESOLVED


def test_provenance_supported_source_never_unlocks_active_testing(tmp_path):
    result = acquire(FakeFetcher(), tmp_path)
    resolved = result.resolve_source_candidates(
        [
            SourceCandidate(
                locator="https://github.com/immunefi-team/audit-comp-ens",
                observed_revision=FORK_REVISION,
                advertised_revision_available=False,
                declared_lineage=True,
            )
        ]
    )

    assert resolved.source_resolution.status is LineageStatus.PROVENANCE_SUPPORTED
    assert resolved.source_resolution.ready_for_analysis is False
    assert resolved.identity_evidence.independent_verification is False
    assert resolved.ready_for_active_testing is False


def test_exact_verified_source_becomes_eligible_for_identity_gate(tmp_path):
    result = acquire(FakeFetcher(), tmp_path)
    resolved = result.resolve_source_candidates(
        [
            SourceCandidate(
                locator="https://example.invalid/audited.git",
                observed_revision=REVISION,
                advertised_revision_available=True,
                observed_head_matches=True,
            )
        ]
    )

    assert resolved.source_resolution.status is LineageStatus.VERIFIED
    assert resolved.source_resolution.ready_for_analysis is True
    assert resolved.identity_evidence.repository_locator == "https://example.invalid/audited.git"
    assert resolved.identity_evidence.independent_verification is True
