from dataclasses import dataclass
import pytest
from cydra.execution_request import ExecutionRequest
from cydra.external_execution import ExternalExecutionAdapter, ExternalExecutionGateway

@dataclass(frozen=True)
class Auth:
    authorization_id: str = "auth-1"
    scope_status: str = "AUTHORIZED_EXECUTION"
    authorized: bool = True

@dataclass(frozen=True)
class Result:
    execution_id: str
    request_digest: str | None
    outcome: str
    def canonical_payload(self):
        return {"execution_id": self.execution_id, "request_digest": self.request_digest, "outcome": self.outcome}

class Adapter:
    def __init__(self, result_mode="ok"):
        self.capability=None; self.result_mode=result_mode; self.calls=0
    def _bind_gateway_capability(self, capability): self.capability=capability
    def execute(self, *, request, authorization, gateway_capability):
        assert gateway_capability is self.capability
        self.calls += 1
        if self.result_mode == "wrong-digest": return Result(request.execution_id, "execution-request:wrong", "NO_COUNTEREXAMPLE")
        return Result(request.execution_id, request.digest, "NO_COUNTEREXAMPLE")
    def rehydrate_result(self, *, payload, request): return Result(payload["execution_id"], payload["request_digest"], payload["outcome"])

def request():
    return ExecutionRequest("exec-1", "fake", "fixture", ("fake", "check"), "project:1", "auth-1")

def gateway(events, states):
    return ExternalExecutionGateway(
        lambda r: events.append("persist-request"),
        lambda r,s: (states.__setitem__(r.digest,s), events.append(s)),
        lambda r: states.get(r.digest),
        lambda r,x: events.append("persist-result"),
    )

def test_gateway_enforces_order_and_exact_result_binding():
    events=[]; states={}; g=gateway(events,states); a=Adapter(); g.register("fake",a)
    result=g.execute("fake",request(),authorization=Auth())
    assert result.request_digest == request().digest
    assert events == ["persist-request","PERSISTED","RUNNING","persist-result","RESULT_RECORDED","COMPLETED"]
    assert states[request().digest] == "COMPLETED"

def test_invalid_result_becomes_outcome_unrecorded_not_failed():
    events=[]; states={}; g=gateway(events,states); a=Adapter("wrong-digest"); g.register("fake",a)
    with pytest.raises(ValueError,match="request digest"):
        g.execute("fake",request(),authorization=Auth())
    assert states[request().digest] == "OUTCOME_UNRECORDED"
    assert a.calls == 1

def test_persisted_terminal_state_blocks_replay():
    req=request(); events=[]; states={req.digest:"COMPLETED"}; g=gateway(events,states); a=Adapter(); g.register("fake",a)
    with pytest.raises(RuntimeError,match="COMPLETED"):
        g.execute("fake",req,authorization=Auth())
    assert a.calls == 0

def test_gateway_requires_exact_authorization_before_persistence():
    events=[]; states={}; g=gateway(events,states); g.register("fake",Adapter())
    with pytest.raises(PermissionError,match="authorization identity"):
        g.execute("fake",request(),authorization=Auth("wrong"))
    assert events == []

def test_gateway_rejects_adapter_rebinding():
    a=Adapter(); first=ExternalExecutionGateway(); second=ExternalExecutionGateway(); first.register("fake",a)
    with pytest.raises(RuntimeError,match="different gateway"):
        second.register("fake",a)

def test_reconciled_result_is_registered_as_trusted():
    req = request()
    states = {req.digest: "OUTCOME_UNRECORDED"}
    durable = Result(req.execution_id, req.digest, "NO_COUNTEREXAMPLE")
    g = ExternalExecutionGateway(
        set_execution_state=lambda r, s: states.__setitem__(r.digest, s),
        get_execution_state=lambda r: states.get(r.digest),
        persist_result=lambda r, x: None,
        get_result=lambda r: durable,
    )
    g.reconcile_result(req, durable)
    assert g.require_trusted_result(durable) is durable

def test_reconciliation_rejects_fabricated_result_without_matching_durable_record():
    req = request()
    states = {req.digest: "OUTCOME_UNRECORDED"}
    durable = Result(req.execution_id, req.digest, "RECORDED")
    fabricated = Result(req.execution_id, req.digest, "FABRICATED")
    g = ExternalExecutionGateway(
        set_execution_state=lambda r, s: states.__setitem__(r.digest, s),
        get_execution_state=lambda r: states.get(r.digest),
        persist_result=lambda r, x: None,
        get_result=lambda r: durable,
    )
    with pytest.raises(ValueError, match="existing durable result"):
        g.reconcile_result(req, fabricated)
