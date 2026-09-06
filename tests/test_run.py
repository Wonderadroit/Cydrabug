from cydra.live_contest import AcquiredResource
from cydra.run import RunBlocked, canonicalize_immunefi_locator, run


class FakeFetcher:
    def fetch(self, locator):
        return AcquiredResource(
            locator,
            '<html><a href="https://github.com/immunefi-team/audit-comp-ens">repo</a>'
            ' audited revision cda79acaad59711b943fc68207ebb3f1d0ff8596</html>',
            "fixture",
        )


def test_canonicalize_accepts_immunefi_program_pages():
    assert canonicalize_immunefi_locator(
        "https://immunefi.com/audit-competition/audit-competition-ens/resources/"
    ) == "https://immunefi.com/audit-competition/audit-competition-ens/information/"
    assert canonicalize_immunefi_locator(
        "https://immunefi.com/audit-competition/audit-competition-ens/"
    ) == "https://immunefi.com/audit-competition/audit-competition-ens/information/"


def test_canonicalize_rejects_non_immunefi_locator():
    try:
        canonicalize_immunefi_locator("https://github.com/example/target")
    except ValueError as exc:
        assert "Immunefi" in str(exc)
    else:
        raise AssertionError("non-Immunefi locator was accepted")


def test_phase_zero_stops_before_target_acquisition(tmp_path):
    result = run(
        "https://immunefi.com/audit-competition/audit-comp-ens/resources/",
        receipt_path=tmp_path / "live-contest.json",
    )
    assert result.contract.platform == "immunefi"
    assert result.identity_evidence is not None
    assert result.identity_evidence.independent_verification is False


def test_run_requires_real_immunefi_intake(monkeypatch, tmp_path):
    # The production run intentionally uses the real passive fetcher. This
    # test verifies the phase gate without introducing a target shortcut.
    from cydra import run as run_module

    monkeypatch.setattr(run_module, "acquire_live_contest", lambda *args, **kwargs: type(
        "Incomplete",
        (),
        {
            "contract": type("Contract", (), {"ready_for_active_testing": False})(),
        },
    )())
    try:
        run_module.run(
            "https://immunefi.com/audit-competition/audit-comp-ens/resources/",
            receipt_path=tmp_path / "live-contest.json",
        )
    except RunBlocked as exc:
        assert "intake is incomplete" in str(exc)
    else:
        raise AssertionError("incomplete intake advanced")
