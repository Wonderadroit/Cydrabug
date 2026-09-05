from cydra.program_intake import (
    AcquiredResource,
    AcquisitionState,
    AuthorityClass,
    ResourceKind,
    parse_immunefi_program,
)


def test_immunefi_program_parser_binds_known_issue_to_acquired_source():
    base = "https://immunefi.com/audit-competition/audit-competition-ens/"
    pages = (
        AcquiredResource(base + "information/", "ENS information", "fixture"),
        AcquiredResource(base + "scope/", "ENS scope", "fixture"),
        AcquiredResource(base + "resources/", "Known issues: previously identified issues are not eligible; PoC required", "fixture"),
    )
    contract = parse_immunefi_program(locator=base + "information/", pages=pages)
    assert contract.platform == "immunefi"
    assert contract.known_issues
    issue = contract.known_issues[0]
    assert issue.status.value == "INELIGIBLE_KNOWN"
    assert issue.source_resource_id == contract.primary_resource_id
    assert any(resource.kind is ResourceKind.PROGRAM and resource.state is AcquisitionState.ACQUIRED for resource in contract.resources)
