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
    fetcher = FixtureFetcher(pages)
    adapter = ImmunefiAcquisitionAdapter(fetcher)
    acquired = adapter.acquire_program_pages(base + "information/")
    assert tuple(page.locator for page in acquired) == locators
    assert fetcher.calls == list(locators)

    try:
        adapter.acquire("https://example.com/audit-competition/audit-competition-ens/information/")
    except ValueError as exc:
        assert "non-Immunefi" in str(exc)
    else:
        raise AssertionError("non-Immunefi acquisition must be rejected")


def test_resource_dependency_graph_preserves_authority_and_unresolved_status():
    base = "https://immunefi.com/audit-competition/audit-competition-ens/"
    root = AcquiredResource(
        base + "information/",
        '<a href="https://github.com/immunefi-team/audit-comp-ens">source</a>',
        "fixture",
    )
    root_resource = parse_immunefi_program(
        locator=base + "information/",
        pages=(
            root,
            AcquiredResource(base + "scope/", "scope", "fixture"),
            AcquiredResource(base + "resources/", "resources", "fixture"),
        ),
    ).resources[0]
    source = AcquiredResource(
        "https://github.com/immunefi-team/audit-comp-ens",
        "repository placeholder",
        "fixture",
    )
    fetcher = FixtureFetcher({source.locator: source})
    resources = expand_resource_dependency_graph(
        roots=(root_resource,),
        acquired={root_resource.resource_id: root},
        fetcher=fetcher,
        max_depth=1,
    )
    repository = next(r for r in resources if r.kind is ResourceKind.REPOSITORY)
    assert repository.authority is AuthorityClass.PROJECT
    assert repository.state is AcquisitionState.ACQUIRED
    assert repository.parent_resource_id == root_resource.resource_id
    assert repository.scope.value == "UNKNOWN"
