"""Convert a durable external execution receipt into evidence without weakening lineage.

This boundary deliberately does not update hypotheses or declare a security result.
It only proves that an exact, previously recorded execution result can become an
observation-bound evidence record.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Optional

from .execution_request import ExecutionRequest


@dataclass(frozen=True)
class ExecutionEvidence:
    evidence_id: str
    observation_name: str
    execution_id: str
    request_digest: str
    adapter: str
    outcome: str
    receipt_fingerprint: str
    payload: Mapping[str, object]
    polarity: str = "neutral"
    confidence: float = 1.0

    def __post_init__(self) -> None:
        for name in ("evidence_id", "observation_name", "execution_id", "request_digest", "adapter", "outcome", "receipt_fingerprint"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.polarity not in {"supports", "contradicts", "neutral"}:
            raise ValueError("unsupported evidence polarity")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not isinstance(self.payload, Mapping):
            raise TypeError("evidence payload must be a mapping")


def _fingerprint(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    return f"execution-receipt:{sha256(encoded).hexdigest()}"


def evidence_from_receipt(*, observation_name: str, request: ExecutionRequest,
                          receipt_payload: Mapping[str, object], evidence_id: str,
                          polarity: str = "neutral", confidence: float = 1.0) -> ExecutionEvidence:
    """Create evidence only when the receipt is exactly bound to the request."""
    if not isinstance(request, ExecutionRequest):
        raise TypeError("request must be a canonical ExecutionRequest")
    if not isinstance(receipt_payload, Mapping):
        raise TypeError("receipt payload must be a mapping")
    if receipt_payload.get("execution_id") != request.execution_id:
        raise ValueError("receipt execution identity does not match execution request")
    if receipt_payload.get("request_digest") != request.digest:
        raise ValueError("receipt request digest does not match execution request")
    if receipt_payload.get("adapter") != request.adapter:
        raise ValueError("receipt adapter does not match execution request")
    outcome = receipt_payload.get("outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        raise ValueError("receipt outcome must be a non-empty string")
    expected = receipt_payload.get("fingerprint")
    canonical_without_fingerprint = dict(receipt_payload)
    canonical_without_fingerprint.pop("fingerprint", None)
    actual = _fingerprint(canonical_without_fingerprint)
    if expected != actual:
        raise ValueError("receipt fingerprint does not match canonical receipt payload")
    return ExecutionEvidence(
        evidence_id=evidence_id,
        observation_name=observation_name,
        execution_id=request.execution_id,
        request_digest=request.digest,
        adapter=request.adapter,
        outcome=outcome,
        receipt_fingerprint=expected,
        payload=dict(receipt_payload),
        polarity=polarity,
        confidence=confidence,
    )
