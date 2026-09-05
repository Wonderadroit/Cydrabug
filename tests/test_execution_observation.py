import pytest

from cydra.execution_observation import (
    execution_evidence_from_trusted_variant,
    variant_observation_from_trusted_result,
)
from cydra.execution_request import ExecutionRequest
from cydra.external_execution import ExternalExecutionGateway


class Result:
    def __init__(self, request, *, outcome="INVARIANT_VIOLATED"):
        self.execution_id = request.execution_id
        self.request_digest = request.digest
        self.outcome = outcome
        self._payload = {
            "execution_id": request.execution_id,
            "request_digest": request.digest,
            "adapter": request.adapter,
            "outcome": outcome,
            "variant_id": "boundary",
            "evidence_id": "exec-evidence:1",
            "verification_outcome": outcome,
            "mechanism_fingerprint": "mechanism:1",
            "verification_confidence": 0.8,
        }

    def canonical_payload(self):
        return dict(self._payload)


class Adapter:
    def _bind_gateway_capability(self, capability):
        self.capability = capability

    def execute(self, *, request, authorization, gateway_capability):
        assert gateway_capability is self.capability
        return Result(request)

    def rehydrate_result(self, *, payload, request):
        result = Result(request, outcome=payload["outcome"])
        result._payload = dict(payload)
        return result


class Authorization:
    authorization_id = "auth-1"
    scope_status = "AUTHORIZED_EXECUTION"
    authorized = True


def make_gateway_and_request():
    stored = []
    gateway = ExternalExecutionGateway(
        persist_request=lambda request: None,
        set_execution_state=lambda request, state: None,
        persist_result=lambda request, result: stored.append(result),
    )
    adapter = Adapter()
    gateway.register("experiment", adapter)
    request = ExecutionRequest(
        execution_id="exec-1",
        adapter="experiment",
        target="/authorized/target",
        command=("experiment",),
        project_fingerprint="project-1",
        authorization_id="auth-1",
    )
    return gateway, request


def test_only_gateway_produced_result_can_become_variant_observation():
    gateway, request = make_gateway_and_request()
    result = gateway.execute("experiment", request, authorization=Authorization())

    observation = variant_observation_from_trusted_result(gateway, request, result)

    assert observation.variant_id == "boundary"
    assert observation.evidence_id == "exec-evidence:1"
    assert observation.outcome == "INVARIANT_VIOLATED"
    assert observation.mechanism_fingerprint == "mechanism:1"
    assert observation.confidence == 0.8


def test_fabricated_result_is_rejected_even_when_request_binding_is_correct():
    gateway, request = make_gateway_and_request()
    fabricated = Result(request)

    with pytest.raises(ValueError, match="was not produced or rehydrated"):
        variant_observation_from_trusted_result(gateway, request, fabricated)


def test_result_missing_observation_fields_cannot_enter_verification():
    gateway, request = make_gateway_and_request()
    result = gateway.execute("experiment", request, authorization=Authorization())
    result._payload.pop("verification_outcome")

    with pytest.raises(ValueError, match="complete verification observation"):
        variant_observation_from_trusted_result(gateway, request, result)


def test_manual_outcome_argument_is_not_part_of_observation_boundary():
    gateway, request = make_gateway_and_request()
    result = gateway.execute("experiment", request, authorization=Authorization())

    with pytest.raises(TypeError):
        variant_observation_from_trusted_result(gateway, request, result, outcome="INVARIANT_PRESERVED")


def test_variant_evidence_uses_the_same_trusted_receipt_and_derives_polarity():
    gateway, request = make_gateway_and_request()
    result = gateway.execute("experiment", request, authorization=Authorization())

    evidence = execution_evidence_from_trusted_variant(gateway, request, result)

    assert evidence.evidence_id == "exec-evidence:1"
    assert evidence.execution_id == request.execution_id
    assert evidence.request_digest == request.digest
    assert evidence.polarity == "supports"
    assert evidence.outcome == "INVARIANT_VIOLATED"
    assert evidence.receipt_fingerprint


def test_mutating_a_trusted_result_invalidates_both_observation_and_evidence():
    gateway, request = make_gateway_and_request()
    result = gateway.execute("experiment", request, authorization=Authorization())
    result._payload["mechanism_fingerprint"] = "forged-mechanism"

    with pytest.raises(ValueError, match="mutated after trust was established"):
        variant_observation_from_trusted_result(gateway, request, result)
    with pytest.raises(ValueError, match="mutated after trust was established"):
        execution_evidence_from_trusted_variant(gateway, request, result)
