"""Live investigation authorization bound to an exact execution request.

Persisted authority snapshots are descriptive only. Execution requires a live
controller whose investigation identity, authority fingerprint, and lease
still match the snapshot.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from .execution_request import ExecutionRequest
from .planner import Observation

_AUTHORITY_PARAMETER = "_cydra_investigation_authority"

@dataclass(frozen=True)
class InvestigationExecutionAuthorization:
    controller: object
    investigation_id: str
    authority_fingerprint: str
    lease_generation: int
    execution_id: str
    observation_name: str
    authorization_id: str
    scope_status: str = "AUTHORIZED_EXECUTION"
    authorized: bool = True

    def __post_init__(self):
        for field in ("investigation_id", "authority_fingerprint", "execution_id", "observation_name", "authorization_id"):
            if not getattr(self, field).strip(): raise ValueError(f"{field} must not be empty")
        if self.lease_generation < 0: raise ValueError("lease_generation must be non-negative")
        if self.scope_status != "AUTHORIZED_EXECUTION": raise ValueError("investigation execution requires AUTHORIZED_EXECUTION scope status")
        if self.authorized is not True: raise PermissionError("investigation execution requires explicit authorization")

    def validate_live(self):
        controller = self.controller
        require_active = getattr(controller, "require_active", None)
        if not callable(require_active): raise PermissionError("execution authorization is not bound to an investigation controller")
        require_active()
        if getattr(controller, "investigation_id", None) != self.investigation_id: raise PermissionError("investigation execution authorization identity mismatch")
        if getattr(controller, "authority_fingerprint", None) != self.authority_fingerprint: raise PermissionError("investigation authority changed after execution authorization was issued")
        lease = getattr(controller, "lease", None)
        if lease is None or getattr(lease, "generation", None) != self.lease_generation: raise PermissionError("investigation lease generation changed after execution authorization was issued")

    def canonical_payload(self):
        return {"investigation_id": self.investigation_id, "authority_fingerprint": self.authority_fingerprint, "lease_generation": self.lease_generation, "execution_id": self.execution_id, "observation_name": self.observation_name, "authorization_id": self.authorization_id, "scope_status": self.scope_status}

def issue_execution_authorization(controller, observation: Observation, authorization, *, dependency_depth: int = 0):
    if not getattr(observation, "authorized", False): raise PermissionError("observation is not authorized for execution")
    if not isinstance(observation.execution_request, ExecutionRequest): raise ValueError("execution-bound observation requires a canonical execution request")
    controller.authorize_observation(observation, dependency_depth=dependency_depth)
    token = InvestigationExecutionAuthorization(controller, controller.investigation_id, controller.authority_fingerprint, controller.lease.generation, observation.execution_id, observation.name, authorization.authorization_id, authorization.scope_status)
    token.validate_live()
    return token

def bind_execution_request(request: ExecutionRequest, authorization: InvestigationExecutionAuthorization):
    if not isinstance(request, ExecutionRequest): raise TypeError("execution request is not canonical")
    authorization.validate_live()
    if request.execution_id != authorization.execution_id: raise ValueError("execution request identity does not match investigation authorization")
    parameters = dict(request.canonical_payload().get("parameters", {}))
    authority = authorization.canonical_payload()
    existing = parameters.get(_AUTHORITY_PARAMETER)
    if existing is not None and dict(existing) != authority: raise ValueError("execution request already carries a different investigation authority binding")
    parameters[_AUTHORITY_PARAMETER] = authority
    return ExecutionRequest(request.execution_id, request.adapter, request.target, request.command, request.project_fingerprint, request.authorization_id, request.scope_status, parameters)

def validate_execution_binding(request: ExecutionRequest, authorization: InvestigationExecutionAuthorization):
    if not isinstance(request, ExecutionRequest) or not isinstance(authorization, InvestigationExecutionAuthorization): raise TypeError("canonical execution binding required")
    authorization.validate_live()
    supplied = request.canonical_payload().get("parameters", {}).get(_AUTHORITY_PARAMETER)
    if not isinstance(supplied, Mapping): raise PermissionError("investigation-bound execution requires an authority binding")
    if dict(supplied) != authorization.canonical_payload(): raise PermissionError("execution request investigation authority binding does not match authorization")
    if request.execution_id != authorization.execution_id or request.authorization_id != authorization.authorization_id: raise PermissionError("execution request identity does not match investigation authorization")

def request_has_investigation_binding(request):
    return _AUTHORITY_PARAMETER in request.canonical_payload().get("parameters", {})

def reissue_execution_authorization(controller, request: ExecutionRequest, authorization):
    parameters = request.canonical_payload().get("parameters", {})
    binding = parameters.get(_AUTHORITY_PARAMETER)
    if not isinstance(binding, Mapping): raise PermissionError("recovery requires a persisted investigation authority binding")
    controller.require_active()
    if controller.investigation_id != str(binding.get("investigation_id")) or controller.authority_fingerprint != str(binding.get("authority_fingerprint")): raise PermissionError("persisted investigation authority no longer matches live authority")
    if controller.lease.generation != int(binding.get("lease_generation")): raise PermissionError("persisted investigation lease generation no longer matches live authority")
    if authorization.authorization_id != str(binding.get("authorization_id")) or authorization.scope_status != str(binding.get("scope_status")): raise PermissionError("persisted investigation authorization does not match base authorization")
    token = InvestigationExecutionAuthorization(controller, str(binding["investigation_id"]), str(binding["authority_fingerprint"]), int(binding["lease_generation"]), str(binding["execution_id"]), str(binding["observation_name"]), str(binding["authorization_id"]), str(binding["scope_status"]))
    token.validate_live()
    return token

def bind_observation_execution(observation: Observation, authorization: InvestigationExecutionAuthorization):
    if not isinstance(observation.execution_request, ExecutionRequest): raise ValueError("investigation-bound observation requires a canonical execution request")
    bound = bind_execution_request(observation.execution_request, authorization)
    return Observation(name=observation.name, outcomes=list(observation.outcomes), cost=observation.cost, authorized=observation.authorized, execution_id=observation.execution_id, execution_request_digest=bound.digest, execution_request=bound, domain=observation.domain, discriminates_hypothesis_ids=observation.discriminates_hypothesis_ids, target_ids=observation.target_ids, rationale=observation.rationale)
