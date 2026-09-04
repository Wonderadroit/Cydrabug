"""Independent validator for durable external-execution lifecycle history."""
from __future__ import annotations
from collections import defaultdict
from typing import Mapping

_ALLOWED = {None:{"PERSISTED"}, "PERSISTED":{"RUNNING"}, "RUNNING":{"RESULT_RECORDED","FAILED","OUTCOME_UNRECORDED"}, "RESULT_RECORDED":{"COMPLETED","OUTCOME_UNRECORDED"}, "OUTCOME_UNRECORDED":{"COMPLETED","FAILED"}, "COMPLETED":set(), "FAILED":set()}
_TERMINAL = {"COMPLETED", "FAILED"}

def validate_execution_lifecycle(model, history) -> list[str]:
    errors=[]; by_request=defaultdict(list)
    for index,event in enumerate(history):
        if not isinstance(event, Mapping): continue
        if event.get("type") in {"EXECUTION_REQUEST_PERSISTED","EXECUTION_STATE_CHANGED","EXECUTION_RESULT_RECORDED","EXTERNAL_EXECUTION_COMPLETED"}:
            rid=event.get("execution_request")
            if not isinstance(rid,str): errors.append(f"execution lifecycle event {index} is missing execution_request")
            else: by_request[rid].append(event)
    canonical={nid for nid,node in model.nodes.items() if getattr(node,"kind",None)=="execution_request"}
    for rid in sorted(canonical-set(by_request)): errors.append(f"execution request has no persisted lifecycle history: {rid}")
    for rid,events in by_request.items():
        request=model.nodes.get(rid)
        if request is None or request.kind != "execution_request": errors.append(f"execution lifecycle references missing execution request: {rid}"); continue
        state=None; execution_id=request.attributes.get("execution_id"); digest=request.attributes.get("digest"); saw_result=False; saw_terminal=False
        for event in events:
            typ=event.get("type")
            if event.get("execution_id") != execution_id: errors.append(f"execution lifecycle execution identity mismatch: {rid}")
            if typ in {"EXECUTION_STATE_CHANGED","EXECUTION_RESULT_RECORDED"} and event.get("request_digest") not in {None,digest}: errors.append(f"execution lifecycle request digest mismatch: {rid}")
            if typ=="EXECUTION_REQUEST_PERSISTED":
                if event.get("digest") not in {None,digest}: errors.append(f"execution request persistence digest mismatch: {rid}")
                if state not in {None,"PERSISTED"}: errors.append(f"execution request persisted after lifecycle advanced: {rid}")
                state="PERSISTED"
            elif typ=="EXECUTION_RESULT_RECORDED":
                if state != "RUNNING": errors.append(f"execution result recorded outside RUNNING state: {rid}")
                if saw_result: errors.append(f"duplicate execution result receipt event: {rid}")
                result=model.nodes.get(event.get("execution_result")) if isinstance(event.get("execution_result"),str) else None
                if result is None or result.kind != "execution_result": errors.append(f"execution result event references missing receipt: {rid}")
                elif result.attributes.get("execution_id") != execution_id or result.attributes.get("request_digest") != digest: errors.append(f"execution result receipt does not match request: {rid}")
                saw_result=True
            elif typ=="EXECUTION_STATE_CHANGED":
                previous=event.get("previous_state"); new=event.get("state")
                if previous != state: errors.append(f"execution lifecycle previous state mismatch: {rid}")
                if new not in _ALLOWED.get(state,set()): errors.append(f"illegal execution lifecycle transition for {rid}: {state or 'ABSENT'} -> {new}")
                if new=="RESULT_RECORDED" and not saw_result: errors.append(f"execution result state recorded before durable receipt event: {rid}")
                if new=="COMPLETED" and not saw_result: errors.append(f"execution completed without durable result receipt: {rid}")
                state=new
                if new in _TERMINAL: saw_terminal=True
            elif typ=="EXTERNAL_EXECUTION_COMPLETED":
                if state != "COMPLETED": errors.append(f"external completion event does not follow COMPLETED state: {rid}")
                if not saw_result: errors.append(f"external completion event has no result receipt: {rid}")
                if not saw_terminal: errors.append(f"external completion event is not terminally anchored: {rid}")
        if request.attributes.get("execution_state") != state: errors.append(f"canonical execution state disagrees with audit lifecycle for {rid}: canonical={request.attributes.get('execution_state')!r}, reconstructed={state!r}")
    return errors
