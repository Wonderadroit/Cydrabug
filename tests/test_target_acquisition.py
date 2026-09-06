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


def test_authoritative_asset_identity_is_preserved_separately_from_paths():
    scope = _resource(ResourceKind.SCOPE, "https://immunefi.com/audit-competition/example/scope/")
    evidence = extract_scope_evidence(
        scope,
        """
        <table>
          <tr><th>Target</th><th>Name</th><th>Added on</th></tr>
          <tr><td></td><td>Manager app Files</td><td>6 August 2026</td></tr>
          <tr><td></td><td>Explorer app Files</td><td>6 August 2026</td></tr>
          <tr><td></td><td>Workers</td><td>13 August 2026</td></tr>
          <tr><td></td><td>Transaction-manager</td><td>13 August 2026</td></tr>
          <tr><td></td><td>Smart-account</td><td>13 August 2026</td></tr>
        </table>
        Applies to: apps/manager (Manager app), apps/portal (Explorer app),
        packages/smart-account, packages/transaction-manager, workers/api-worker
        """,
    )
    assert {asset.asset_name for asset in evidence.assets} == {
        "Manager app Files",
        "Explorer app Files",
        "Workers",
        "Transaction-manager",
        "Smart-account",
    }
    assert "workers/api-worker" in evidence.path_hints


def test_asset_extraction_does_not_cross_into_impacts_or_known_issue_tables():
    scope = _resource(ResourceKind.SCOPE, "https://immunefi.com/audit-competition/example/scope/")
    evidence = extract_scope_evidence(
        scope,
        """
        <h2>Assets in Scope</h2>
        <table>
          <tr><th>Target</th><th>Name</th><th>Added on</th></tr>
          <tr><td></td><td>Manager app Files</td><td>6 August 2026</td></tr>
          <tr><td></td><td>Explorer app Files</td><td>6 August 2026</td></tr>
          <tr><td></td><td>Workers</td><td>13 August 2026</td></tr>
          <tr><td></td><td>Transaction-manager</td><td>13 August 2026</td></tr>
          <tr><td></td><td>Smart-account</td><td>13 August 2026</td></tr>
        </table>
        <h2>Impacts in Scope</h2>
        <table>
          <tr><th>Severity</th><th>Title</th></tr>
          <tr><td>Critical</td><td>Direct theft of user funds</td></tr>
          <tr><td>High</td><td>Arbitrary file uploads</td></tr>
        </table>
        <h2>Public Disclosure of Known Issues</h2>
        <table>
          <tr><th>Ref</th><th>Severity</th><th>Area</th><th>Issue</th></tr>
          <tr><td>R2-01</td><td>Medium</td><td>Manager + Explorer</td><td>Secrets remediation incomplete</td></tr>
        </table>
        Applies to: apps/manager, apps/portal, packages/smart-account,
        packages/transaction-manager, workers/api-worker
        """,
    )
    assert {asset.asset_name for asset in evidence.assets} == {
        "Manager app Files",
        "Explorer app Files",
        "Workers",
        "Transaction-manager",
        "Smart-account",
    }
    assert "Critical" not in {asset.asset_name for asset in evidence.assets}
    assert "Direct theft of user funds" not in {asset.asset_name for asset in evidence.assets}
    assert "R2-01" not in {asset.asset_name for asset in evidence.assets}


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


def test_all_authoritative_assets_must_be_resolved_before_source_identity():
    scope_locator = "https://immunefi.com/audit-competition/example/scope/"
    first_target_locator = "https://github.com/example/project/tree/rev/apps/manager"
    second_target_locator = "https://github.com/example/fork/tree/rev/apps/manager"
    dependency_locator = "https://github.com/example/ensjs/pull/230"
    scope = _resource(ResourceKind.SCOPE, scope_locator)
    first_target = _resource(ResourceKind.REPOSITORY, first_target_locator)
    second_target = _resource(ResourceKind.REPOSITORY, second_target_locator)
    dependency = _resource(ResourceKind.REPOSITORY, dependency_locator)
    acquired_scope = AcquiredResource(
        scope_locator,
        """
        <table>
          <tr><th>Target</th><th>Name</th><th>Added on</th></tr>
          <tr><td></td><td>Manager app Files</td><td>6 August 2026</td></tr>
          <tr><td></td><td>Workers</td><td>13 August 2026</td></tr>
        </table>
        In scope: apps/manager workers/api-worker
        """,
        "fixture",
    )
    contract = ProgramContract(
        "example",
        "immunefi",
        "Example",
        scope.resource_id,
        (scope, first_target, second_target, dependency),
    )
    result = LiveContestAcquisition(
        "https://immunefi.com/audit-competition/example/information/",
        contract,
        (acquired_scope,),
        (),
        (scope, first_target, second_target, dependency),
    )

    plan = plan_target_acquisition(result)
    assert plan.ready_for_source_identity is False
    assert any(asset.asset_name == "Workers" for asset in plan.unresolved_assets)


def test_missing_asset_path_can_be_inferred_from_unique_observed_repository_lineage():
    scope_locator = "https://immunefi.com/audit-competition/example/scope/"
    manager_locator = "https://github.com/example/project/tree/audit-ready/apps/manager"
    scope = _resource(ResourceKind.SCOPE, scope_locator)
    manager = _resource(ResourceKind.REPOSITORY, manager_locator)
    acquired_scope = AcquiredResource(
        scope_locator,
        """
        <table>
          <tr><th>Target</th><th>Name</th><th>Added on</th></tr>
          <tr><td></td><td>Manager app Files</td><td>6 August 2026</td></tr>
          <tr><td></td><td>Workers</td><td>13 August 2026</td></tr>
        </table>
        In scope: apps/manager workers/api-worker
        """,
        "fixture",
    )
    contract = ProgramContract("example", "immunefi", "Example", scope.resource_id, (scope, manager))
    result = LiveContestAcquisition(
        "https://immunefi.com/audit-competition/example/information/",
        contract,
        (acquired_scope,),
        (),
        (scope, manager),
    )

    plan = plan_target_acquisition(result)
    inferred = [c for c in plan.candidates if c.acquisition_role == "TARGET_INFERRED_PATH"]
    assert len(inferred) == 1
    assert inferred[0].locator == "https://github.com/example/project/tree/audit-ready/workers/api-worker"
    assert inferred[0].asset_names == ("Workers",)
    assert plan.unresolved_assets == ()
    assert plan.ready_for_source_identity is True


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
