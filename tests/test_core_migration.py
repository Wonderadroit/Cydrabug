from cydra.program_intake import (
    AcquiredResource,
    AuthorityClass,
    ResourceKind,
    ScopeStatus,
    build_program_contract,
    canonical_resource_id,
    contract_to_system_model,
    resource_from_acquisition,
)
from cydra.scope import ScopePolicy, ScopeRule, ScopeState


def test_migrated_program_contract_is_fail_closed():
    locator = "https://immunefi.com/audit-competition/audit-competition-ens/scope/"
    resource = AcquiredResource(locator, "ENS scope snapshot", "fixture")
    program = build_program_contract(
        program_id="audit-competition-ens",
        display_name="ENS",
        primary_locator=locator,
        resources=(
            resource_from_acquisition(
                kind=ResourceKind.PROGRAM,
                acquired=resource,
                adapter="fixture",
                authority=AuthorityClass.AUTHORITATIVE,
            ),
        ),
    )
    assert program.ready_for_active_testing
    assert len(program.fingerprint) == 64
    model = contract_to_system_model(program)
    assert not model.validate()


def test_unknown_scope_is_not_authorized():
    policy = ScopePolicy([ScopeRule("apps/manager/**", ScopeState.IN_SCOPE, "ENS competition scope")])
    assert policy.decide("packages/unknown/file.ts").state is ScopeState.UNKNOWN
    assert policy.decide("packages/unknown/file.ts").allowed_for_active_testing is False


def test_explicit_out_of_scope_context_remains_context_only():
    primary_locator = "https://immunefi.com/audit-competition/audit-competition-ens/scope/"
    primary = resource_from_acquisition(
        kind=ResourceKind.PROGRAM,
        acquired=AcquiredResource(primary_locator, "x", "fixture"),
        adapter="fixture",
        authority=AuthorityClass.AUTHORITATIVE,
    )
    dep = resource_from_acquisition(
        kind=ResourceKind.REPOSITORY,
        acquired=AcquiredResource("https://github.com/example/dep", "x", "fixture"),
        adapter="fixture",
        authority=AuthorityClass.PROJECT,
        parent_resource_id=primary.resource_id,
        scope=ScopeStatus.OUT_OF_SCOPE,
        required=False,
    )
    contract = build_program_contract(
        program_id="ens",
        display_name="ENS",
        primary_locator=primary_locator,
        resources=(primary, dep),
    )
    assert contract.ready_for_active_testing
    assert contract.resources[1].scope is ScopeStatus.OUT_OF_SCOPE
    assert contract.resources[1].required is False
