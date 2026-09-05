from cydra.live_contest import acquire_live_contest
from cydra.program_intake import AcquiredResource, ResourceKind, ScopeStatus


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def fetch(self, locator):
        self.calls.append(locator)
        content = f'<html><a href="https://github.com/example/ens-app">repo</a></html>'
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
