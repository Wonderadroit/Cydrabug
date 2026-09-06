from cydra.live_contest import AcquiredResource
from cydra.run import run_phase_one
import cydra.run as run_module


class PhaseOneFetcher:
    def fetch(self, locator):
        content = (
            "<html>"
            "Assets in scope: apps/manager, packages/smart-account "
            '<a href="https://github.com/example/project/tree/audit-ready/apps/manager">manager</a>'
            '<a href="https://github.com/example/ensjs/pull/230">dependency</a>'
            " audited revision 63772fd872af472ced58b009499355f3430c2a86"
            "</html>"
        )
        return AcquiredResource(locator, content, "fixture")


def test_phase_one_classifies_from_scope_not_discovery_order(monkeypatch, tmp_path):
    from cydra.live_contest import acquire_live_contest

    monkeypatch.setattr(
        run_module,
        "acquire_live_contest",
        lambda locator, receipt_path: acquire_live_contest(
            locator,
            fetcher=PhaseOneFetcher(),
            receipt_path=receipt_path,
        ),
    )

    plan = run_phase_one(
        "https://immunefi.com/audit-competition/example/resources/",
        receipt_path=tmp_path / "phase0.json",
    )

    assert len(plan.in_scope_candidates) == 1
    assert plan.in_scope_candidates[0].matched_hints == ("apps/manager",)
    assert len(plan.unresolved_resources) == 1
    assert plan.ready_for_source_identity is True
