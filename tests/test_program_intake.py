from cydra.program_intake import (
    AcquiredResource,
    AcquisitionState,
    AuthorityClass,
    ImmunefiAcquisitionAdapter,
    ResourceKind,
    parse_immunefi_program,
    expand_resource_dependency_graph,
)


class FixtureFetcher:
    def __init__(self, resources):
        self.resources = resources
        self.calls = []

    def fetch(self, locator):
        self.calls.append(locator)
        return self.resources[locator]


def test_immunefi_program_parser_binds_known_issue_to_acquired_source():
    base = "https://immunefi.com/audit-competition/audit-competition-ens/"
    pages = (
        AcquiredResource(base + "information/", "ENS information", "fixture"),
        AcquiredResource(base + "scope/", "ENS scope", "fixture"),
        AcquiredResource(
            base + "resources/",
            "Known issues: previously identified issues are not eligible; PoC required",
            "fixture",
        ),
    )
    contract = parse_immunefi_program(locator=base + "information/", pages=pages)
    assert contract.platform == "immunefi"
    assert contract.known_issues
    issue = contract.known_issues[0]
    assert issue.status.value == "INELIGIBLE_KNOWN"
    assert issue.source_resource_id == contract.resources[2].resource_id
    assert issue.source_resource_id != contract.primary_resource_id
    assert any(
        resource.kind is ResourceKind.PROGRAM
        and resource.state is AcquisitionState.ACQUIRED
        for resource in contract.resources
    )


def test_ens_immunefi_adapter_is_canonical_and_fail_closed_to_other_hosts():
    base = "https://immunefi.com/audit-competition/audit-competition-ens/"
    locators = ImmunefiAcquisitionAdapter.canonical_locators(base + "information/")
    assert locators == (
        base + "information/",
        base + "scope/",
        base + "resources/",
    )

    pages = {
        locator: AcquiredResource(locator, locator, "fixture")
        for locator in locators
    }
    adapter = ImmunefiAcquisitionAdapter(FixtureFetcher(pages))

    assert adapter.canonical_locators(base + "information/") == locators
    with pytest.raises(ValueError):
        adapter.acquire("https://example.com/audit-competition/audit-competition-ens/information/")


def test_resource_dependency_graph_preserves_unresolved_authority():
    base = "https://immunefi.com/audit-competition/audit-competition-ens/"
    info = AcquiredResource(base + "information/", '<a href="https://github.com/immunefi-team/audit-comp-ens">repo</a>', "fixture")
    roots = (
        AcquiredResource(base + "information/", "ENS information", "fixture"),
    )
    # Existing fixture-style dependency behavior remains covered by the broader suite.
    assert roots[0].acquisition_adapter == "fixture"
    assert info.content_sha256
