from cydra.ens_target import AUDITED_REVISION, bind_repository, assert_fail_closed, scoped_assets


def test_ens_binding_does_not_promote_frozen_snapshot_to_audited_revision():
    binding = bind_repository()
    assert binding.status == "REVISION_MISMATCH"
    assert not binding.ready


def test_ens_exact_revision_is_the_only_ready_revision():
    binding = bind_repository(available_revision=AUDITED_REVISION)
    assert binding.ready
    assert binding.status == "READY"


def test_unresolved_revision_fails_closed():
    binding = bind_repository(available_revision=None)
    try:
        assert_fail_closed(binding)
    except RuntimeError as exc:
        assert "not audit-ready" in str(exc)
    else:
        raise AssertionError("unresolved source revision must not pass the audit gate")


def test_scoped_assets_match_live_ens_snapshot():
    assert scoped_assets() == (
        "apps/manager",
        "apps/portal",
        "workers/api-worker",
        "packages/transaction-manager",
        "packages/smart-account",
    )
