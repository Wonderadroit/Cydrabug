from types import SimpleNamespace

import cydra.run as run_module
from cydra.source_identity import SourceIdentityReceipt


def _candidate(locator):
    return SimpleNamespace(locator=locator)


def _result(revision):
    return SimpleNamespace(
        identity_evidence=SimpleNamespace(advertised_revision=revision),
    )


def _plan(candidates):
    return SimpleNamespace(
        program_id="audit-competition-ens",
        in_scope_candidates=tuple(candidates),
        unresolved_assets=(),
    )


def test_phase_two_groups_assets_by_repository_and_requires_verified_identity(monkeypatch, tmp_path):
    locator = "https://github.com/example/project/tree/main/apps/manager"
    seen = []

    monkeypatch.setattr(run_module, "_acquire_phase_zero", lambda *args, **kwargs: _result("a" * 40))
    monkeypatch.setattr(run_module, "plan_target_acquisition", lambda result: _plan([_candidate(locator)]))

    def fake_acquire(repository, revision, checkout, *, target_paths):
        seen.append((repository, revision, tuple(target_paths)))
        return SourceIdentityReceipt(
            repository_locator=repository,
            repository=repository,
            requested_revision=revision,
            checkout_path=str(checkout),
            observed_revision=revision,
            working_tree_clean=True,
            target_paths=tuple(target_paths),
            missing_target_paths=(),
            status="VERIFIED",
            reason="test verification",
        )

    monkeypatch.setattr(run_module, "acquire_and_verify_source", fake_acquire)

    result = run_module.run_phase_two(
        "https://immunefi.com/audit-competition/audit-competition-ens/resources/",
        workspace=tmp_path,
    )

    assert result.ready_for_next_phase is True
    assert seen == [("https://github.com/example/project.git", "a" * 40, ("apps/manager",))]


def test_phase_two_blocks_when_authoritative_revision_is_missing(monkeypatch):
    monkeypatch.setattr(run_module, "_acquire_phase_zero", lambda *args, **kwargs: _result(None))
    monkeypatch.setattr(
        run_module,
        "plan_target_acquisition",
        lambda result: _plan([_candidate("https://github.com/example/project/tree/main/apps/manager")]),
    )

    try:
        run_module.run_phase_two("https://immunefi.com/audit-competition/audit-competition-ens/resources/")
    except run_module.RunBlocked as exc:
        assert "audited revision is unresolved" in str(exc)
    else:
        raise AssertionError("Phase 2 advanced without an authoritative revision")
