"""Canonical Immunefi-first program intake and contextual acquisition primitives.

Adapters produce evidence; this module never grants testing authority. Unknown scope
and unresolved resources remain fail-closed until explicitly classified.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json, re
from typing import Callable, Protocol
from urllib.parse import urljoin, urlparse

class AcquisitionState(str, Enum):
    ACQUIRED="ACQUIRED"; UNRESOLVED="UNRESOLVED"; STALE="STALE"; REJECTED="REJECTED"
class AuthorityClass(str, Enum):
    AUTHORITATIVE="AUTHORITATIVE"; PLATFORM="PLATFORM"; PROJECT="PROJECT"; AGGREGATOR="AGGREGATOR"; CONTEXTUAL="CONTEXTUAL"; UNKNOWN="UNKNOWN"
class ScopeStatus(str, Enum):
    IN_SCOPE="IN_SCOPE"; OUT_OF_SCOPE="OUT_OF_SCOPE"; CONDITIONAL="CONDITIONAL"; UNKNOWN="UNKNOWN"
class ResourceKind(str, Enum):
    PROGRAM="PROGRAM"; RULES="RULES"; SCOPE="SCOPE"; IMPACTS="IMPACTS"; REPOSITORY="REPOSITORY"; DOCUMENTATION="DOCUMENTATION"; DEPLOYMENT="DEPLOYMENT"; EXPLORER="EXPLORER"; AUDIT="AUDIT"; KNOWN_ISSUES="KNOWN_ISSUES"; OTHER="OTHER"
class KnownIssueStatus(str, Enum):
    INELIGIBLE_DUPLICATE="INELIGIBLE_DUPLICATE"; INELIGIBLE_KNOWN="INELIGIBLE_KNOWN"; RESOLVED_KNOWN="RESOLVED_KNOWN"; CONTEXT_ONLY="CONTEXT_ONLY"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class AcquiredResource:
    locator:str; content:str; acquisition_adapter:str; version:str|None=None; content_sha256:str|None=None
    def __post_init__(self):
        if not self.locator.strip() or not self.acquisition_adapter.strip(): raise ValueError("locator and acquisition_adapter must not be empty")
        if self.content_sha256 is None: object.__setattr__(self,"content_sha256",content_fingerprint(self.content))
@dataclass(frozen=True)
class KnownIssue:
    issue_id:str; title:str; source_resource_id:str; status:KnownIssueStatus; locator:str|None=None; fingerprint:str|None=None; affected_assets:tuple[str,...]=(); affected_versions:tuple[str,...]=(); notes:str=""
    def __post_init__(self):
        for n in ("issue_id","title","source_resource_id"):
            if not getattr(self,n).strip(): raise ValueError(f"{n} must not be empty")
        if self.fingerprint is not None and len(self.fingerprint)!=64: raise ValueError("fingerprint must be a SHA-256 hex digest")
@dataclass(frozen=True)
class ProgramAssertion:
    assertion_id:str; category:str; text:str; source_resource_id:str; authority:AuthorityClass; scope:ScopeStatus=ScopeStatus.UNKNOWN; required:bool=True
@dataclass(frozen=True)
class ProgramResource:
    resource_id:str; kind:ResourceKind; locator:str; authority:AuthorityClass; acquisition_adapter:str; state:AcquisitionState; scope:ScopeStatus=ScopeStatus.UNKNOWN; content_sha256:str|None=None; version:str|None=None; parent_resource_id:str|None=None; required:bool=True; reason:str=""
@dataclass(frozen=True)
class ResourceDiscovery:
    parent_resource_id:str; locator:str; kind:ResourceKind; authority:AuthorityClass; required:bool=False; reason:str=""
    def to_resource(self): return unresolved_resource(kind=self.kind,locator=self.locator,adapter="reference-discovery",authority=self.authority,parent_resource_id=self.parent_resource_id,required=self.required,reason=self.reason)
@dataclass(frozen=True)
class ProgramContract:
    program_id:str; platform:str; display_name:str; primary_resource_id:str; resources:tuple[ProgramResource,...]=(); assertions:tuple[ProgramAssertion,...]=(); known_issues:tuple[KnownIssue,...]=(); unresolved_required:tuple[str,...]=(); intake_context:str=""
    def __post_init__(self):
        if self.primary_resource_id not in {r.resource_id for r in self.resources}: raise ValueError("primary resource must exist in resources")
        ids=[r.resource_id for r in self.resources]
        if len(ids)!=len(set(ids)): raise ValueError("duplicate resource identity")
        if any(a.source_resource_id not in set(ids) for a in self.assertions): raise ValueError("assertion references unknown resource")
        if any(k.source_resource_id not in set(ids) for k in self.known_issues): raise ValueError("known issue references unknown resource")
    @property
    def ready_for_active_testing(self): return not self.unresolved_required and all(r.state is AcquisitionState.ACQUIRED or not r.required for r in self.resources)
    @property
    def fingerprint(self): return hashlib.sha256(json.dumps({"program_id":self.program_id,"platform":self.platform,"display_name":self.display_name,"primary_resource_id":self.primary_resource_id,"resources":[resource_payload(r) for r in self.resources],"assertions":[assertion_payload(a) for a in self.assertions],"known_issues":[known_issue_payload(k) for k in self.known_issues],"unresolved_required":sorted(self.unresolved_required),"intake_context":self.intake_context},sort_keys=True,separators=(",",":")).encode()).hexdigest()
    def to_json(self): return json.dumps({"program_id":self.program_id,"platform":self.platform,"display_name":self.display_name,"primary_resource_id":self.primary_resource_id,"resources":[resource_payload(r) for r in self.resources],"assertions":[assertion_payload(a) for a in self.assertions],"known_issues":[known_issue_payload(k) for k in self.known_issues],"unresolved_required":list(self.unresolved_required),"intake_context":self.intake_context,"fingerprint":self.fingerprint},sort_keys=True,indent=2)+"\n"

def resource_payload(r): return {"resource_id":r.resource_id,"kind":r.kind.value,"locator":r.locator,"authority":r.authority.value,"acquisition_adapter":r.acquisition_adapter,"state":r.state.value,"scope":r.scope.value,"content_sha256":r.content_sha256,"version":r.version,"parent_resource_id":r.parent_resource_id,"required":r.required,"reason":r.reason}
def assertion_payload(a): return {"assertion_id":a.assertion_id,"category":a.category,"text":a.text,"source_resource_id":a.source_resource_id,"authority":a.authority.value,"scope":a.scope.value,"required":a.required}
def known_issue_payload(k): return {"issue_id":k.issue_id,"title":k.title,"source_resource_id":k.source_resource_id,"status":k.status.value,"locator":k.locator,"fingerprint":k.fingerprint,"affected_assets":list(k.affected_assets),"affected_versions":list(k.affected_versions),"notes":k.notes}
def known_issue_excludes_finding(issue): return issue.status in {KnownIssueStatus.INELIGIBLE_DUPLICATE,KnownIssueStatus.INELIGIBLE_KNOWN}
def known_issue_applies(issue,*,fingerprint=None,asset=None,version=None):
    if not known_issue_excludes_finding(issue) or fingerprint is None or issue.fingerprint is None or fingerprint!=issue.fingerprint:return False
    if issue.affected_assets and (asset is None or asset not in issue.affected_assets):return False
    if issue.affected_versions and (version is None or version not in issue.affected_versions):return False
    return True
def content_fingerprint(content): return hashlib.sha256(content.encode() if isinstance(content,str) else content).hexdigest()
def canonical_resource_id(kind,locator):
    if not locator.strip():raise ValueError("resource locator must not be empty")
    return f"resource:{kind.value.lower()}:{hashlib.sha256(locator.strip().encode()).hexdigest()[:24]}"
def normalize_locator(base_locator,locator):return urljoin(base_locator,locator.strip())
def classify_link(locator):
    p=urlparse(locator); host=(p.hostname or "").lower(); path=p.path.lower()
    if host=="immunefi.com" or host.endswith(".immunefi.com"):
        if "/scope" in path:return AuthorityClass.AUTHORITATIVE,ResourceKind.SCOPE
        if "/resources" in path:return AuthorityClass.AUTHORITATIVE,ResourceKind.RULES
        return AuthorityClass.AUTHORITATIVE,ResourceKind.PROGRAM
    if host=="github.com" or host.endswith(".github.com"):return AuthorityClass.PROJECT,ResourceKind.REPOSITORY
    if host in {"etherscan.io","sepolia.etherscan.io","arbiscan.io","basescan.org"}:return AuthorityClass.CONTEXTUAL,ResourceKind.EXPLORER
    if any(x in path for x in ("audit","audits")):return AuthorityClass.CONTEXTUAL,ResourceKind.AUDIT
    if any(x in path for x in ("known-issues","known_issues")):return AuthorityClass.CONTEXTUAL,ResourceKind.KNOWN_ISSUES
    if any(x in path for x in ("docs","documentation")):return AuthorityClass.CONTEXTUAL,ResourceKind.DOCUMENTATION
    return AuthorityClass.UNKNOWN,ResourceKind.OTHER
def resource_from_acquisition(*,kind,acquired,adapter,authority,parent_resource_id=None,scope=ScopeStatus.UNKNOWN,required=True,reason=""):
    return ProgramResource(canonical_resource_id(kind,acquired.locator),kind,acquired.locator,authority,adapter,AcquisitionState.ACQUIRED,scope,acquired.content_sha256,acquired.version,parent_resource_id,required,reason)
def unresolved_resource(*,kind,locator,adapter,authority,parent_resource_id=None,required=True,reason=""):
    return ProgramResource(canonical_resource_id(kind,locator),kind,locator,authority,adapter,AcquisitionState.UNRESOLVED,ScopeStatus.UNKNOWN,None,None,parent_resource_id,required,reason)
def build_program_contract(*,program_id,display_name,primary_locator,resources,assertions=(),known_issues=(),platform="immunefi",intake_context=""):
    resources=tuple(resources); return ProgramContract(program_id,platform,display_name,canonical_resource_id(ResourceKind.PROGRAM,primary_locator),resources,tuple(assertions),tuple(known_issues),tuple(r.resource_id for r in resources if r.required and r.state is not AcquisitionState.ACQUIRED),intake_context)
def classify_scope(*,locator,explicit_in_scope=(),explicit_out_of_scope=()):
    if locator in explicit_out_of_scope:return ScopeStatus.OUT_OF_SCOPE
    if locator in explicit_in_scope:return ScopeStatus.IN_SCOPE
    return ScopeStatus.UNKNOWN
def discover_references(*,parent_resource_id,base_locator,content):
    out=[];seen=set()
    for raw in re.findall(r"(?i)(?:href|src)\s*=\s*['\"]([^'\"]+)['\"]",content):
        loc=normalize_locator(base_locator,raw)
        if urlparse(loc).scheme not in {"http","https"}:continue
        authority,kind=classify_link(loc);key=(kind,loc)
        if key not in seen:seen.add(key);out.append(ResourceDiscovery(parent_resource_id,loc,kind,authority,False,"reference discovered from acquired program material; authorization unresolved"))
    return tuple(out)
def extract_known_issues(*,acquired):
    text=re.sub(r"<[^>]+>"," ",acquired.content);text=re.sub(r"\s+"," ",text)
    if not re.search(r"known issues?|previously identified|not eligible",text,re.I):return ()
    return (KnownIssue("known:"+hashlib.sha256(acquired.locator.encode()).hexdigest()[:16],"Program-published known issues",canonical_resource_id(ResourceKind.PROGRAM,acquired.locator),KnownIssueStatus.INELIGIBLE_KNOWN),)
def parse_immunefi_program(*,locator,pages):
    slug=ImmunefiAcquisitionAdapter.program_slug(locator); info=next(p for p in pages if "/information/" in p.locator); scope=next((p for p in pages if "/scope/" in p.locator),None); resources=next((p for p in pages if "/resources/" in p.locator),None)
    primary=resource_from_acquisition(kind=ResourceKind.PROGRAM,acquired=info,adapter="immunefi",authority=AuthorityClass.AUTHORITATIVE); rs=[primary]
    if scope:rs.append(resource_from_acquisition(kind=ResourceKind.SCOPE,acquired=scope,adapter="immunefi",authority=AuthorityClass.AUTHORITATIVE,parent_resource_id=primary.resource_id))
    if resources:rs.append(resource_from_acquisition(kind=ResourceKind.RULES,acquired=resources,adapter="immunefi",authority=AuthorityClass.AUTHORITATIVE,parent_resource_id=primary.resource_id))
    text=re.sub(r"<[^>]+>"," "," ".join(p.content for p in pages)); assertions=[]
    if re.search(r"PoC|proof of concept",text,re.I):assertions.append(ProgramAssertion("assertion:poc","poc_requirement","Program requires a proof of concept",primary.resource_id,AuthorityClass.AUTHORITATIVE))
    if re.search(r"known issues?.*not eligible|previously.*not eligible",text,re.I):assertions.append(ProgramAssertion("assertion:known-issues","known_issue_policy","Known issues/duplicates are not eligible",primary.resource_id,AuthorityClass.AUTHORITATIVE))
    return build_program_contract(program_id=slug,display_name=slug,primary_locator=primary.locator,resources=rs,assertions=assertions,known_issues=extract_known_issues(acquired=info),intake_context="Immunefi authoritative program pages")
class DocumentFetcher(Protocol):
    def fetch(self,locator):...
class ImmunefiAcquisitionAdapter:
    def __init__(self,fetcher):self.fetcher=fetcher
    @staticmethod
    def program_slug(locator):
        parts=[p for p in urlparse(locator).path.split('/') if p]
        if len(parts)>=2 and parts[0] in {"bug-bounty","audit-competition"}:return parts[1]
        raise ValueError("locator is not a supported Immunefi program URL")
    @classmethod
    def canonical_locators(cls,locator):
        path=urlparse(locator).path; slug=cls.program_slug(locator); prefix="audit-competition" if "/audit-competition/" in path else "bug-bounty"; base=f"https://immunefi.com/{prefix}/{slug}/"
        return (base+"information/",base+"scope/",base+"resources/")
    def acquire(self,locator):
        if urlparse(locator).hostname!="immunefi.com":raise ValueError("Immunefi adapter refuses non-Immunefi locators")
        if locator.rstrip('/')+'/' not in self.canonical_locators(locator):raise ValueError("locator is not a canonical Immunefi program page")
        result=self.fetcher.fetch(locator) if hasattr(self.fetcher,'fetch') else self.fetcher(locator)
        if not isinstance(result,AcquiredResource):raise TypeError("fetcher must return AcquiredResource")
        if result.locator.rstrip('/')+'/'!=locator.rstrip('/')+'/':raise ValueError("fetcher locator does not match requested locator")
        return result
    def acquire_program_pages(self,locator):return tuple(self.acquire(x) for x in self.canonical_locators(locator))
    def acquire_contract(self,locator):return parse_immunefi_program(locator=locator,pages=self.acquire_program_pages(locator))
def bounded_reference_plan(*,parent,acquired,max_depth=2):return tuple(d for d in discover_references(parent_resource_id=parent.resource_id,base_locator=acquired.locator,content=acquired.content) if d.kind in {ResourceKind.REPOSITORY,ResourceKind.DOCUMENTATION,ResourceKind.DEPLOYMENT,ResourceKind.EXPLORER,ResourceKind.AUDIT,ResourceKind.KNOWN_ISSUES})
def acquire_reference(*,discovery,fetcher):
    raw=fetcher.fetch(discovery.locator) if hasattr(fetcher,'fetch') else fetcher(discovery.locator)
    return resource_from_acquisition(kind=discovery.kind,acquired=raw,adapter="reference-discovery",authority=discovery.authority,parent_resource_id=discovery.parent_resource_id,scope=ScopeStatus.UNKNOWN,required=discovery.required,reason=discovery.reason)
def expand_resource_dependency_graph(*,roots,acquired,fetcher=None,max_depth=2):
    resources={r.resource_id:r for r in roots}; contents=dict(acquired); frontier=[(r,0) for r in roots if r.resource_id in contents]
    while frontier:
        parent,depth=frontier.pop(0)
        if depth>=max_depth:continue
        for d in bounded_reference_plan(parent=parent,acquired=contents[parent.resource_id],max_depth=max_depth):
            if d.to_resource().resource_id in resources:continue
            child=d.to_resource();resources[child.resource_id]=child
            if fetcher is not None:
                raw=fetcher.fetch(d.locator) if hasattr(fetcher,'fetch') else fetcher(d.locator); fetched=resource_from_acquisition(kind=d.kind,acquired=raw,adapter="reference-discovery",authority=d.authority,parent_resource_id=d.parent_resource_id,scope=ScopeStatus.UNKNOWN,required=d.required,reason=d.reason);resources[fetched.resource_id]=fetched;contents[fetched.resource_id]=raw;frontier.append((fetched,depth+1))
    return tuple(resources.values())
def contract_to_system_model(contract):
    from .system_model import Node,Edge,SystemModel
    model=SystemModel();pid=f"program:{contract.platform}:{contract.program_id}";model.add_node(Node(pid,"program",contract.display_name,{"fingerprint":contract.fingerprint,"ready_for_active_testing":contract.ready_for_active_testing}))
    for r in contract.resources:model.add_node(Node(r.resource_id,"resource",r.locator,resource_payload(r)));model.add_edge(Edge(pid,"has_resource",r.resource_id))
    return model
