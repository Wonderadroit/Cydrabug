"""Convert gateway-trusted execution receipts into verification observations.

Verification must consume observations whose execution identity, provenance, and
classification are bound to the external-execution gateway. Manual outcome
objects and untrusted result instances are deliberately rejected.
"""
from __future__ import annotations

from collections.abc import Mapping

from .external_execution import ExternalExecutionGateway, ExternalExecutionResult
from .execution_request import ExecutionRequest
from .verification import VariantObservation

_ALLOWED_OUTCOMES = frozenset({"INVARIANT_VIOLATED", "INVARIANT_PRESERVED", "INCONCLUSIVE"})


def variant_observation_from_trusted_result(
    gateway: ExternalExecutionGateway,
    request: ExecutionRequest,
    result: ExternalExecutionResult,
) -> VariantObservation:
    """Build a VariantObservation only from a gateway-trusted, self-bound result.

    The result must carry its variant identity, verification outcome, mechanism
    fingerprint, and evidence identity in its canonical durable payload. These
    fields are therefore part of the authenticated execution receipt rather
    than caller-supplied arguments to verification.
    """
    if not isinstance(gateway, ExternalExecutionGateway):
        raise TypeError("gateway must be an ExternalExecutionGateway")
    if not isinstance(request, ExecutionRequest):
        raise TypeError("request must be a canonical ExecutionRequest")
    gateway.require_trusted_result(result)
    if not isinstance(result, ExternalExecutionResult):
        raise TypeError("result does not implement the CYDRA execution result contract")
    if result.execution_id != request.execution_id or result.request_digest != request.digest:
        raise ValueError("trusted result is not bound to the supplied execution request")

    payload = result.canonical_payload()
    if not isinstance(payload, Mapping):
        raise TypeError("trusted result canonical payload must be a mapping")
    required = {"execution_id", "request_digest", "variant_id", "verification_outcome", "mechanism_fingerprint", "evidence_id"}
    if not required.issubset(payload):
        raise ValueError("trusted result does not contain a complete verification observation")
    if payload["execution_id"] != request.execution_id or payload["request_digest"] != request.digest:
        raise ValueError("trusted result observation identity does not match execution request")

    variant_id = payload["variant_id"]
    evidence_id = payload["evidence_id"]
    outcome = payload["verification_outcome"]
    mechanism = payload["mechanism_fingerprint"]
    for name, value in (("variant_id", variant_id), ("evidence_id", evidence_id), ("mechanism_fingerprint", mechanism)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"trusted result {name} must be a non-empty string")
    if not isinstance(outcome, str) or outcome not in _ALLOWED_OUTCOMES:
        raise ValueError("trusted result verification outcome is invalid")

    confidence = payload.get("verification_confidence", 1.0)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("trusted result verification confidence must be numeric")
    return VariantObservation(variant_id, evidence_id, outcome, mechanism, float(confidence))
