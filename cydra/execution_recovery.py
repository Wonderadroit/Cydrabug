"""Fresh-process recovery for durable external-execution receipts.

Recovery never re-executes an external adapter. It reconstructs the canonical
request, verifies the durable receipt against that request, and asks the
execution gateway to rehydrate the adapter-neutral result. Evidence ingestion
is deliberately left to the reasoning layer so recovery cannot silently invent
or duplicate observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .execution_request import ExecutionRequest
from .external_execution import ExternalExecutionGateway, ExternalExecutionResult


@dataclass(frozen=True)
class RecoveredExecution:
    request: ExecutionRequest
    result: ExternalExecutionResult
    state: str


class ExecutionRecoveryService:
    """Recover one previously executed request from durable state.

    The callbacks must read durable state; they must not manufacture a request
    or result. Exact request and receipt identity is checked before any adapter
    rehydration occurs.
    """

    def __init__(
        self,
        *,
        gateway: ExternalExecutionGateway,
        load_request: Callable[[str], ExecutionRequest | None],
        load_result: Callable[[str], Mapping[str, object] | None],
        get_state: Callable[[str], str | None],
    ) -> None:
        self.gateway = gateway
        self.load_request = load_request
        self.load_result = load_result
        self.get_state = get_state

    def recover(self, *, execution_id: str, request_digest: str, adapter: str) -> RecoveredExecution:
        if not execution_id.strip():
            raise ValueError("execution_id must not be empty")
        if not request_digest.strip():
            raise ValueError("request_digest must not be empty")
        if not adapter.strip():
            raise ValueError("adapter must not be empty")

        request = self.load_request(execution_id)
        if not isinstance(request, ExecutionRequest):
            raise RuntimeError("durable execution request is missing or not canonical")
        if request.execution_id != execution_id:
            raise ValueError("durable execution request identity does not match recovery request")
        if request.digest != request_digest:
            raise ValueError("durable execution request digest does not match recovery request")
        if request.adapter != adapter:
            raise ValueError("durable execution request adapter does not match recovery adapter")

        state = self.get_state(request.digest)
        if state not in {"RESULT_RECORDED", "COMPLETED", "OUTCOME_UNRECORDED"}:
            raise RuntimeError(
                f"execution recovery requires a recorded or uncertain outcome, found {state or 'ABSENT'}"
            )

        payload = self.load_result(request.digest)
        if not isinstance(payload, Mapping):
            raise RuntimeError("durable execution result receipt is missing or invalid")
        if payload.get("execution_id") != request.execution_id:
            raise ValueError("durable result execution identity does not match request")
        if payload.get("request_digest") != request.digest:
            raise ValueError("durable result request digest does not match request")
        if payload.get("adapter") != request.adapter:
            raise ValueError("durable result adapter does not match request")

        result = self.gateway.rehydrate_result(adapter, request, payload)
        return RecoveredExecution(request=request, result=result, state=state)
