"""Convert gateway-trusted execution receipts into verification observations.

Verification must consume observations whose execution identity, provenance, and
classification are bound to the external-execution gateway. Manual outcome
objects and untrusted result instances are deliberately rejected.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from .execution_evidence import ExecutionEvidence, _fingerprint
from .external_execution import ExternalExecutionGateway, ExternalExecutionResult
from .execution_request import ExecutionRequest
from .hypothesis import BeliefUpdate, Hypothesis, HypothesisState, update_hypothesis
from .verification import VariantObservation, verify_candidate_from_variants

_ALLOWED_OUTCOMES = frozenset({"INVARIANT_VIOLATED", "INVARIANT_PRESERVED", "INCONCLUSIVE"})


def _observation_payload(result: ExternalExecutionResult, request: ExecutionRequest) -> Mapping[str, object]:
    payload = result.canonical_payload()
    if not isinstance(payload, Mapping):
        raise TypeError("trusted result canonical payload must be a mapping")
    required = {"execution_id", "request_digest", "variant_id", "verification_outcome", "mechanism_fingerprint", "evidence_id"}
    if not required.issubset(payload):
        raise ValueError("trusted result does not contain a complete verification observation")
    if payload["execution_id"] != request.execution_id or payload["request_digest"] != request.digest:
        raise ValueError("trusted result observation identity does not match execution request")
    return payload


def variant_observation_from_trusted_result(
    gateway: ExternalExecutionGateway,
    request: ExecutionRequest,
    result: ExternalExecutionResult,
) -> VariantObservation:
    """Build a VariantObservation only from a gateway-trusted, self-bound result."""
    if not isinstance(gateway, ExternalExecutionGateway):
        raise TypeError("gateway must be an ExternalExecutionGateway")
    if not isinstance(request, ExecutionRequest):
        raise TypeError("request must be a canonical ExecutionRequest")
    gateway.require_trusted_result(result)
    if not isinstance(result, ExternalExecutionResult):
        raise TypeError("result does not implement the CYDRA execution result contract")
    if result.execution_id != request.execution_id or result.request_digest != request.digest:
        raise ValueError("trusted result is not bound to the supplied execution request")

    payload = _observation_payload(result, request)
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


def execution_evidence_from_trusted_variant(
    gateway: ExternalExecutionGateway,
    request: ExecutionRequest,
    result: ExternalExecutionResult,
) -> ExecutionEvidence:
    """Create canonical evidence from the same trusted receipt as a variant observation."""
    gateway.require_trusted_result(result)
    observation = variant_observation_from_trusted_result(gateway, request, result)
    payload = dict(result.canonical_payload())
    receipt_fingerprint = _fingerprint(payload)
    polarity = {
        "INVARIANT_VIOLATED": "supports",
        "INVARIANT_PRESERVED": "contradicts",
        "INCONCLUSIVE": "neutral",
    }[observation.outcome]
    return ExecutionEvidence(
        evidence_id=observation.evidence_id,
        observation_name="variant_verification",
        execution_id=request.execution_id,
        request_digest=request.digest,
        adapter=request.adapter,
        outcome=observation.outcome,
        receipt_fingerprint=receipt_fingerprint,
        payload=payload,
        polarity=polarity,
        confidence=observation.confidence,
    )


def verify_violation_hypothesis_from_trusted_results(
    gateway: ExternalExecutionGateway,
    candidate_id: str,
    hypothesis: Hypothesis,
    executions: Iterable[tuple[ExecutionRequest, ExternalExecutionResult]],
) -> tuple[Hypothesis, BeliefUpdate]:
    """Verify and update an invariant-violation hypothesis from trusted executions.

    The execution receipts are the sole source of verification classification.
    This function only composes the existing variant verifier and hypothesis
    updater; it does not execute anything, alter prior belief, or infer truth
    from discovery confidence.
    """
    if not candidate_id.strip():
        raise ValueError("candidate_id must not be empty")
    expected_id = f"hypothesis:invariant-violated:{candidate_id}"
    if hypothesis.hypothesis_id != expected_id:
        raise ValueError("hypothesis is not the canonical invariant-violation hypothesis for this candidate")
    if hypothesis.state in {HypothesisState.SUPPORTED, HypothesisState.CONTRADICTED}:
        raise ValueError("terminal hypothesis state cannot be updated with new verification evidence")

    observations = tuple(
        variant_observation_from_trusted_result(gateway, request, result)
        for request, result in executions
    )
    verification, evidence = verify_candidate_from_variants(candidate_id, observations)
    return update_hypothesis(hypothesis, verification, evidence)
