from cydra.live_contest import AcquisitionIdentityEvidence, acquire_live_contest
from cydra.program_intake import AcquiredResource, ResourceKind, ScopeStatus


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
        content = (
            f'<html>{links} '
            "audited revision 63772fd872af472ced58b009499355f3430c2a86</html>"
        )
        return AcquiredResource(locator, content, "fixture")


def test_live_contest_acquisition_composes_immunefi_intake_and_graph(tmp_path):
    fetcher = FakeFetcher()
    result = acquire_live_contest(
        "https://immunefi.com/audit-competition/audit-competition-ens/information/",
        fetcher=fetcher,
        receipt_path=tmp_path / "live-contest.json",
    )

    assert result.contract.platform == "immunefi"
    assert len(result.acquired) == 3
    assert result.contract.fingerprint
    assert result.graph
    assert result.discovered
    assert any(item.kind is ResourceKind.REPOSITORY for item in result.discovered)
    assert (tmp_path / "live-contest.json").is_file()


def test_acquisition_preserves_unresolved_identity_evidence(tmp_path):
    fetcher = FakeFetcher()
    result = acquire_live_contest(
        "https://immunefi.com/audit-competition/audit-competition-ens/information/",
        fetcher=fetcher,
        receipt_path=tmp_path / "live-contest.json",
    )

    assert isinstance(result.identity_evidence, AcquisitionIdentityEvidence)
    assert result.identity_evidence.status == "UNRESOLVED"
    assert result.identity_evidence.independent_verification is False
    assert result.identity_evidence.repository_locator is None
    assert result.identity_evidence.acquired_revision is None
    assert result.identity_evidence.advertised_revision == "63772fd872af472ced58b009499355f3430c2a86"
    assert "target/resource classification" in result.identity_evidence.reason

    receipt = (tmp_path / "live-contest.json").read_text()
    assert '"identity_evidence"' in receipt
    assert '"repository_locator": null' in receipt
    assert '"status": "UNRESOLVED"' in receipt


def test_discovered_project_resource_does_not_become_authorized(tmp_path):
    fetcher = FakeFetcher()
    result = acquire_live_contest(
        "https://immunefi.com/audit-competition/audit-competition-ens/scope/",
        fetcher=fetcher,
        receipt_path=tmp_path / "live-contest.json",
    )

    repo_resources = [r for r in result.graph if r.kind is ResourceKind.REPOSITORY]
    assert repo_resources
    assert all(r.scope is ScopeStatus.UNKNOWN for r in repo_resources)
    assert result.ready_for_active_testing is False


def test_repository_discovery_order_cannot_change_source_identity(tmp_path):
    first_context = FakeFetcher(
        repository_links=(
            "https://github.com/example/context-pr",
            "https://github.com/example/target",
        )
    )
    second_context = FakeFetcher(
        repository_links=(
            "https://github.com/example/target",
            "https://github.com/example/context-pr",
        )
    )

    first = acquire_live_contest(
        "https://immunefi.com/audit-competition/audit-competition-ens/information/",
        fetcher=first_context,
        receipt_path=tmp_path / "first.json",
    )
    second = acquire_live_contest(
        "https://immunefi.com/audit-competition/audit-competition-ens/information/",
        fetcher=second_context,
        receipt_path=tmp_path / "second.json",
    )

    assert first.identity_evidence.repository_locator is None
    assert second.identity_evidence.repository_locator is None
    assert first.identity_evidence.reason == second.identity_evidence.reason

    first_repositories = [
        r.locator for r in first.graph if r.kind is ResourceKind.REPOSITORY
    ]
    second_repositories = [
        r.locator for r in second.graph if r.kind is ResourceKind.REPOSITORY
    ]
    assert first_repositories != second_repositories
    assert first.identity_evidence.repository_locator != first_repositories[0]
    assert second.identity_evidence.repository_locator != second_repositories[0]
