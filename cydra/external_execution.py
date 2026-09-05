"""Adapter-neutral gateway for explicitly authorized external execution.

Planning never executes. This gateway is the sole execution boundary: it checks
request/authorization identity, persists the exact request, enforces lifecycle
transitions, delegates through a gateway-owned capability, validates the exact
result, and requires a durable receipt before completion.
"""
from __future__ import annotations
from hashlib import sha256
import json
from typing import Callable, Mapping, Protocol, runtime_checkable
from .execution_request import ExecutionRequest

EXECUTION_STATES=frozenset({"PERSISTED","RUNNING","RESULT_RECORDED","COMPLETED","FAILED","OUTCOME_UNRECORDED"})
_ALLOWED_TRANSITIONS={None:{"PERSISTED"},"PERSISTED":{"RUNNING"},"RUNNING":{"RESULT_RECORDED","FAILED","OUTCOME_UNRECORDED"},"RESULT_RECORDED":{"COMPLETED","OUTCOME_UNRECORDED"},"OUTCOME_UNRECORDED":{"COMPLETED","FAILED"},"COMPLETED":set(),"FAILED":set()}

@runtime_checkable
class ExternalExecutionResult(Protocol):
    execution_id:str; request_digest:str|None; outcome:str
    def canonical_payload(self)->Mapping[str,object]: ...

@runtime_checkable
class ExternalExecutionAdapter(Protocol):
    def _bind_gateway_capability(self, capability:object)->None: ...
    def execute(self, *, request:ExecutionRequest, authorization:object, gateway_capability:object)->ExternalExecutionResult: ...
    def rehydrate_result(self, *, payload:Mapping[str,object], request:ExecutionRequest)->ExternalExecutionResult: ...

def _receipt_digest(payload: Mapping[str, object]) -> str:
    encoded=json.dumps(dict(payload),sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
    return sha256(encoded).hexdigest()

def validate_result_binding(result, request):
    if not isinstance(result,ExternalExecutionResult): raise TypeError("external result does not implement the CYDRA result contract")
    if result.execution_id!=request.execution_id: raise ValueError("external result execution identity does not match the execution request")
    if not result.request_digest: raise ValueError("external result is missing the execution request digest")
    if result.request_digest!=request.digest: raise ValueError("external result request digest does not match the execution request")
    if not isinstance(result.outcome,str) or not result.outcome.strip(): raise ValueError("external result outcome must be a non-empty string")
    payload=result.canonical_payload()
    if not isinstance(payload,Mapping): raise TypeError("external result canonical payload must be a mapping")
    if payload.get("execution_id")!=result.execution_id or payload.get("request_digest")!=result.request_digest or payload.get("outcome")!=result.outcome: raise ValueError("external result canonical payload identity does not match its result identity")

def require_external_execution_contract(adapter):
    if not isinstance(adapter,ExternalExecutionAdapter): raise TypeError("external adapter does not implement the CYDRA execution contract")
    return adapter

class ExternalExecutionGateway:
    # Adapter identity is a process-wide capability boundary. Keeping the
    # strong adapter reference prevents id reuse from reopening a binding.
    _GLOBAL_ADAPTER_GATEWAYS={}

    def __init__(self,persist_request:Callable[[ExecutionRequest],object]|None=None,set_execution_state:Callable[[ExecutionRequest,str],object]|None=None,get_execution_state:Callable[[ExecutionRequest],str|None]|None=None,persist_result:Callable[[ExecutionRequest,ExternalExecutionResult],object]|None=None,get_result:Callable[[ExecutionRequest],ExternalExecutionResult|None]|None=None):
        self._adapters={}; self._persist_request=persist_request; self._set_execution_state=set_execution_state; self._get_execution_state=get_execution_state; self._persist_result=persist_result; self._get_result=get_result; self._executed_digests=set(); self._local_states={}; self._execution_capabilities={}; self._trusted_results={}
    def register(self,name,adapter):
        if not isinstance(name,str) or not name.strip(): raise ValueError("adapter name must not be empty")
        if name in self._adapters: raise ValueError(f"external adapter is already registered: {name}")
        canonical=require_external_execution_contract(adapter)
        key=id(canonical)
        owner=ExternalExecutionGateway._GLOBAL_ADAPTER_GATEWAYS.get(key)
        if owner is not None and owner is not self:
            raise RuntimeError("external adapter is already bound to a different gateway")
        capability=object(); canonical._bind_gateway_capability(capability); self._execution_capabilities[name]=capability; self._adapters[name]=canonical; ExternalExecutionGateway._GLOBAL_ADAPTER_GATEWAYS[key]=self
    def adapter(self,name):
        if name not in self._adapters: raise KeyError(f"external adapter is not registered: {name}")
        return self._adapters[name]
    def _current_state(self,request):
        persisted=self._get_execution_state(request) if self._get_execution_state else None
        return persisted if persisted is not None else self._local_states.get(request.digest)
    def _state(self,request,state):
        current=self._current_state(request)
        if state not in EXECUTION_STATES: raise ValueError(f"unsupported external execution state: {state}")
        if state not in _ALLOWED_TRANSITIONS.get(current,set()): raise RuntimeError(f"invalid external execution lifecycle transition: {current or 'ABSENT'} -> {state}")
        if self._set_execution_state: self._set_execution_state(request,state)
        self._local_states[request.digest]=state
    def _mark_failure(self,request):
        try:self._state(request,"FAILED")
        except Exception:self._local_states[request.digest]="FAILED"
    def _mark_unrecorded(self,request):
        try:self._state(request,"OUTCOME_UNRECORDED")
        except Exception:self._local_states[request.digest]="OUTCOME_UNRECORDED"
    def execute(self,name,request:ExecutionRequest,*,authorization,investigation_authorization=None):
        if not isinstance(request,ExecutionRequest): raise TypeError("execution request is not a canonical ExecutionRequest")
        if authorization is None or getattr(authorization,"authorization_id",None)!=request.authorization_id: raise PermissionError("authorization identity does not match the execution request")
        if getattr(authorization,"scope_status",None)!=request.scope_status or getattr(authorization,"authorized",False) is not True: raise PermissionError("external execution requires explicit authorization")
        if request.adapter!=name: raise ValueError("execution request adapter does not match the registered adapter")
        if request.digest in self._executed_digests: raise RuntimeError("external execution request has already been executed")
        current=self._current_state(request)
        if current in {"RUNNING","RESULT_RECORDED","COMPLETED","FAILED","OUTCOME_UNRECORDED"}: raise RuntimeError(f"external execution request is already terminal or in-flight: {current}")
        if self._persist_request is None or self._persist_result is None: raise RuntimeError("canonical external execution gateway requires request and result persistence")
        if investigation_authorization is not None:
            from .investigation_execution import validate_execution_binding
            validate_execution_binding(request,investigation_authorization)
        self._persist_request(request)
        if self._current_state(request) is None:self._state(request,"PERSISTED")
        self._state(request,"RUNNING")
        adapter=self.adapter(name)
        try: result=adapter.execute(request=request,authorization=authorization,gateway_capability=self._execution_capabilities[name])
        except Exception:
            self._mark_failure(request); raise
        try: validate_result_binding(result,request)
        except Exception:
            self._mark_unrecorded(request); raise
        try:
            self._persist_result(request,result); self._state(request,"RESULT_RECORDED"); self._state(request,"COMPLETED")
        except Exception as exc:
            self._mark_unrecorded(request); raise RuntimeError("external execution succeeded but durable result/completion recording failed") from exc
        self._executed_digests.add(request.digest); self._trusted_results[id(result)]=(_receipt_digest(result.canonical_payload()),result); return result
    def rehydrate_result(self,name,request,payload):
        current=self._current_state(request)
        if current not in {"RESULT_RECORDED","COMPLETED","OUTCOME_UNRECORDED"}: raise RuntimeError(f"result rehydration requires a recorded external result, found {current or 'ABSENT'}")
        result=self.adapter(name).rehydrate_result(payload=payload,request=request); validate_result_binding(result,request)
        if dict(result.canonical_payload())!=dict(payload): raise ValueError("rehydrated result does not exactly match the durable receipt payload")
        self._trusted_results[id(result)]=(_receipt_digest(result.canonical_payload()),result)
        return result
    def require_trusted_result(self, result):
        entry=self._trusted_results.get(id(result))
        if entry is None or entry[1] is not result: raise ValueError("external execution result was not produced or rehydrated by this gateway")
        try: current=_receipt_digest(result.canonical_payload())
        except Exception as exc: raise ValueError("trusted external execution result canonical payload is no longer valid") from exc
        if current!=entry[0]: raise ValueError("trusted external execution result was mutated after trust was established")
        return result
    def reconcile_result(self,request,result,*,terminal_state="COMPLETED"):
        if terminal_state not in {"COMPLETED","FAILED"}: raise ValueError("reconciliation requires terminal_state COMPLETED or FAILED")
        validate_result_binding(result,request)
        if self._current_state(request) not in {"OUTCOME_UNRECORDED","RESULT_RECORDED"}: raise RuntimeError("execution reconciliation requires OUTCOME_UNRECORDED or RESULT_RECORDED state")
        if self._persist_result is None: raise RuntimeError("execution reconciliation requires durable result persistence")
        if self._get_result is None: raise RuntimeError("execution reconciliation requires an existing durable result")
        durable = self._get_result(request)
        if not isinstance(durable, ExternalExecutionResult) or dict(durable.canonical_payload()) != dict(result.canonical_payload()):
            raise ValueError("reconciled result does not match the existing durable result")
        self._persist_result(request,result); self._state(request,terminal_state); self._executed_digests.add(request.digest); self._trusted_results[id(result)]=(_receipt_digest(result.canonical_payload()),result)
    @property
    def registered_adapters(self): return tuple(sorted(self._adapters))