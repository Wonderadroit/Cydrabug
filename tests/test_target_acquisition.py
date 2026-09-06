from cydra.live_contest import LiveContestAcquisition
from cydra.program_intake import (
    AcquiredResource,
    AcquisitionState,
    AuthorityClass,
    ProgramContract,
    ProgramResource,
    ResourceKind,
)
from cydra.target_acquisition import (
    classify_repository,
    extract_scope_evidence,
    plan_target_acquisition,
)


def _resource(kind, locator, parent=None):
    return ProgramResource(
        resource_id=f"resource:{kind.value.lower()}:{abs(hash(locator))}",
        kind=kind,
        locator=locator,
        authority=AuthorityClass.AUTHORITATIVE if kind is ResourceKind.SCOPE else AuthorityClass.PROJECT,
        acquisition_adapter="fixture",
        state=AcquisitionState.ACQUIRED,
        parent_resource_id=parent,
        required=False,
    )


def test_scope_path_hints_are_authoritative_and_conservative():
    scope = _resource(ResourceKind.SCOPE, "https://immunefi.com/audit-competition/example/scope/")
    evidence = extract_scope_evidence(
        scope,
        "Assets: apps/manager, apps/portal, packages/transaction-manager, packages/smart-account, workers/api-worker",
    )
    assert "apps/manager" in evidence.path_hints
    assert "packages/transaction-manager" in evidence.path_hints
    assert "workers/api-worker" in evidence.path_hints


def test_repository_is_target_only_when_authoritative_scope_path_matches():
    scope = _resource(ResourceKind.SCOPE, "https://immunefi.com/audit-competition/example/scope/")
    evidence = extract_scope_evidence(scope, "In scope: apps/manager")

    target = _resource(
        ResourceKind.REPOSITORY,
        "https://github.com/example/project/tree/audit-ready/apps/manager",
    )
    dependency = _resource(
        ResourceKind.REPOSITORY,
        "https://github.com/example/dependency/pull/230",
    )
    unrelated = _resource(
        ResourceKind.REPOSITORY,
        "https://github.com/example/project/tree/audit-ready/apps/other",
    )

    target_candidate = classify_repository(target, evidence)
    dependency_candidate = classify_repository(dependency, evidence)
    unrelated_candidate = classify_repository(unrelated, evidence)

    assert target_candidate.scope.value == "IN_SCOPE"
    assert target_candidate.acquisition_role == "TARGET"
    assert dependency_candidate.scope.value == "UNKNOWN"
    assert unrelated_candidate.scope.value == "UNKNOWN"


def test_discovery_order_cannot_change_target_classification():
    scope_locator = "https://immunefi.com/audit-competition/example/scope/"
    target_locator = "https://github.com/example/project/tree/rev/apps/manager"
    dependency_locator = "https://github.com/example/ensjs/pull/230"
    scope = _resource(ResourceKind.SCOPE, scope_locator)
    target = _resource(ResourceKind.REPOSITORY, target_locator)
    dependency = _resource(ResourceKind.REPOSITORY, dependency_locator)
    acquired_scope = AcquiredResource(scope_locator, "In scope: apps/manager", "fixture")
    contract = ProgramContract("example", "immunefi", "Example", scope.resource_id, (scope, target, dependency))

    first = LiveContestAcquisition(
        "https://immunefi.com/audit-competition/example/information/",
        contract,
        (acquired_scope,),
        (),
        (scope, target, dependency),
    )
    second = LiveContestAcquisition(
        "https://immunefi.com/audit-competition/example/information/",
        contract,
        (acquired_scope,),
        (),
        (scope, dependency, target),
    )

    first_plan = plan_target_acquisition(first)
    second_plan = plan_target_acquisition(second)
    first_states = {c.locator: c.scope.value for c in first_plan.candidates}
    second_states = {c.locator: c.scope.value for c in second_plan.candidates}
    assert first_states == second_states
    assert first_states[target_locator] == "IN_SCOPE"
    assert first_states[dependency_locator] == "UNKNOWN"
