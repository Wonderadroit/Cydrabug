from dataclasses import replace
import hashlib
import json
import pytest

from cydra.execution_evidence import evidence_from_receipt
from cydra.execution_request import ExecutionRequest


def request():
    return ExecutionRequest("exec-1", "fake", "fixture", ("fake", "check"), "project:1", "auth-1")


def receipt(req):
    body = {
        "execution_id": req.execution_id,
        "request_digest": req.digest,
        "adapter": req.adapter,
        "outcome": "INVARIANT_PRESERVED",
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    body["fingerprint"] = f"execution-receipt:{hashlib.sha256(encoded).hexdigest()}"
    return body


def test_exact_receipt_becomes_evidence():
    req = request()
    evidence = evidence_from_receipt(
        observation_name="check",
        request=req,
        receipt_payload=receipt(req),
        evidence_id="evidence:exec-1",
    )
    assert evidence.execution_id == req.execution_id
    assert evidence.request_digest == req.digest
    assert evidence.outcome == "INVARIANT_PRESERVED"
    assert evidence.confidence == 1.0


def test_wrong_request_digest_is_rejected():
    req = request()
    bad = receipt(req)
    bad["request_digest"] = "execution-request:wrong"
    with pytest.raises(ValueError, match="digest"):
        evidence_from_receipt(observation_name="check", request=req, receipt_payload=bad, evidence_id="e1")


def test_tampered_receipt_fingerprint_is_rejected():
    req = request()
    bad = receipt(req)
    bad["outcome"] = "INVARIANT_VIOLATED"
    with pytest.raises(ValueError, match="fingerprint"):
        evidence_from_receipt(observation_name="check", request=req, receipt_payload=bad, evidence_id="e1")


def test_receipt_cannot_cross_adapters():
    req = request()
    bad = receipt(req)
    bad["adapter"] = "other"
    with pytest.raises(ValueError, match="adapter"):
        evidence_from_receipt(observation_name="check", request=req, receipt_payload=bad, evidence_id="e1")


def test_evidence_polarity_is_explicit():
    req = request()
    evidence = evidence_from_receipt(
        observation_name="check", request=req, receipt_payload=receipt(req),
        evidence_id="e1", polarity="contradicts", confidence=0.8,
    )
    assert evidence.polarity == "contradicts"
    assert evidence.confidence == 0.8
