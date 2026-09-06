from cydra.live_contest import AcquiredResource, acquire_live_contest
from cydra.run import RunBlocked, canonicalize_immunefi_locator
import cydra.run as run_module


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


def test_phase_zero_stops_after_intake(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_module,
        "acquire_live_contest",
        lambda locator, receipt_path: acquire_live_contest(
            locator,
            fetcher=FakeFetcher(),
            receipt_path=receipt_path,
        ),
    )
    result = run_module.run(
        "https://immunefi.com/audit-competition/audit-comp-ens/resources/",
        receipt_path=tmp_path / "live-contest.json",
    )
    assert result.contract.platform == "immunefi"
    assert result.identity_evidence is not None
    assert result.identity_evidence.independent_verification is False
    assert (tmp_path / "live-contest.json").is_file()


def test_run_blocks_incomplete_intake(monkeypatch, tmp_path):
    class IncompleteContract:
        ready_for_active_testing = False

    class Incomplete:
        contract = IncompleteContract()

    monkeypatch.setattr(run_module, "acquire_live_contest", lambda *args, **kwargs: Incomplete())
    try:
        run_module.run(
            "https://immunefi.com/audit-competition/audit-comp-ens/resources/",
            receipt_path=tmp_path / "live-contest.json",
        )
    except RunBlocked as exc:
        assert "intake is incomplete" in str(exc)
    else:
        raise AssertionError("incomplete intake advanced")
