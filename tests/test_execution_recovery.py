from dataclasses import dataclass

import pytest

from cydra.execution_recovery import ExecutionRecoveryService
from cydra.execution_request import ExecutionRequest
from cydra.external_execution import ExternalExecutionGateway


@dataclass(frozen=True)
class Result:
    execution_id: str
    request_digest: str | None
    outcome: str

    def canonical_payload(self):
        return {
            "execution_id": self.execution_id,
            "request_digest": self.request_digest,
            "outcome": self.outcome,
        }


class Adapter:
    def _bind_gateway_capability(self, capability):
        self.capability = capability

    def execute(self, *, request, authorization, gateway_capability):
        return Result(request.execution_id, request.digest, "NO_COUNTEREXAMPLE")

    def rehydrate_result(self, *, payload, request):
        return Result(payload["execution_id"], payload["request_digest"], payload["outcome"])


def request():
    return ExecutionRequest(
        "exec-recover-1",
        "fake",
        "fixture",
        ("fake", "check"),
        "project:1",
        "auth-1",
    )


def test_recovery_rehydrates_exact_durable_receipt_without_execution():
    req = request()
    states = {req.digest: "COMPLETED"}
    receipts = {
        req.digest: {
            "execution_id": req.execution_id,
            "request_digest": req.digest,
            "outcome": "NO_COUNTEREXAMPLE",
        }
    }
    adapter = Adapter()
    gateway = ExternalExecutionGateway(
        get_execution_state=lambda r: states.get(r.digest),
    )
    gateway.register("fake", adapter)

    service = ExecutionRecoveryService(
        gateway=gateway,
        load_request=lambda execution_id: req if execution_id == req.execution_id else None,
        load_result=lambda digest: receipts.get(digest),
        get_state=lambda digest: states.get(digest),
    )

    recovered = service.recover(
        execution_id=req.execution_id,
        request_digest=req.digest,
        adapter="fake",
    )

    assert recovered.request.digest == req.digest
    assert recovered.result.execution_id == req.execution_id
    assert recovered.result.request_digest == req.digest
    assert recovered.state == "COMPLETED"


def test_recovery_rejects_receipt_bound_to_different_request():
    req = request()
    states = {req.digest: "COMPLETED"}
    receipts = {
        req.digest: {
            "execution_id": req.execution_id,
            "request_digest": "execution-request:wrong",
            "outcome": "NO_COUNTEREXAMPLE",
        }
    }
    gateway = ExternalExecutionGateway(
        get_execution_state=lambda r: states.get(r.digest),
    )
    gateway.register("fake", Adapter())
    service = ExecutionRecoveryService(
        gateway=gateway,
        load_request=lambda execution_id: req,
        load_result=lambda digest: receipts.get(digest),
        get_state=lambda digest: states.get(digest),
    )

    with pytest.raises(ValueError, match="digest"):
        service.recover(
            execution_id=req.execution_id,
            request_digest=req.digest,
            adapter="fake",
        )


def test_recovery_never_runs_adapter():
    req = request()
    states = {req.digest: "OUTCOME_UNRECORDED"}
    receipts = {
        req.digest: {
            "execution_id": req.execution_id,
            "request_digest": req.digest,
            "outcome": "NO_COUNTEREXAMPLE",
        }
    }
    adapter = Adapter()
    adapter.execute_called = False

    gateway = ExternalExecutionGateway(
        get_execution_state=lambda r: states.get(r.digest),
    )
    gateway.register("fake", adapter)
    service = ExecutionRecoveryService(
        gateway=gateway,
        load_request=lambda execution_id: req,
        load_result=lambda digest: receipts.get(digest),
        get_state=lambda digest: states.get(digest),
    )

    service.recover(execution_id=req.execution_id, request_digest=req.digest, adapter="fake")
    assert adapter.execute_called is False
