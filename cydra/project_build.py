"""Repository build identity and toolchain preparation primitives.

Build preparation records what the target declares and what CYDRA observes. It does
not silently substitute toolchains or turn a successful build into testing authority.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, re, shutil, subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

@dataclass(frozen=True)
class ToolchainSpec:
    tool: str
    version: str | None = None
    source: str = "undetermined"
    executable: str | None = None

@dataclass(frozen=True)
class BuildProfile:
    system: str
    command: tuple[str, ...]
    artifact_roots: tuple[str, ...]
    ast_format: str = "none"
    language: str | None = None
    toolchain: ToolchainSpec | None = None
    config_files: tuple[str, ...] = ()

@dataclass(frozen=True)
class BuildIdentity:
    repository: str
    revision: str
    profile: BuildProfile
    config_fingerprint: str | None
    declared_toolchain: ToolchainSpec | None
    observed_tool_versions: Mapping[str, str | None]
    dependency_lock_files: tuple[str, ...]

@dataclass(frozen=True)
class BuildResult:
    status: str
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    profile: BuildProfile
    artifacts: Mapping[str, dict[str, Any]]
    artifact_paths: tuple[str, ...]
    tool_version: str | None = None
    config_fingerprint: str | None = None
    reproducibility: str = "UNKNOWN"
    dependency_metadata: Mapping[str, Any] | None = None
    dependency_fingerprint: str | None = None

def _read(root:Path,name:str)->str|None:
    try:return (root/name).read_text(encoding="utf-8")
    except (OSError,UnicodeDecodeError):return None

def _node_toolchain(root:Path)->ToolchainSpec:
    for name in (".nvmrc",".node-version"):
        v=_read(root,name)
        if v and v.strip():return ToolchainSpec("node",v.strip().splitlines()[0],name,"node")
    try:p=json.loads(_read(root,"package.json") or "{}")
    except json.JSONDecodeError:p={}
    engines=p.get("engines",{}) if isinstance(p,dict) else {}
    return ToolchainSpec("node",engines.get("node") if isinstance(engines,dict) else None,"package.json:engines.node","node")

def detect_project(root:str|Path)->BuildProfile:
    root=Path(root)
    if (root/"pnpm-workspace.yaml").is_file() or (root/"package.json").is_file():
        package=_read(root,"package.json") or "{}"
        try:p=json.loads(package)
        except json.JSONDecodeError:p={}
        manager=p.get("packageManager") if isinstance(p,dict) else None
        executable="pnpm" if isinstance(manager,str) and manager.startswith("pnpm@") else "npm"
        command=(executable,"run","build")
        return BuildProfile("node",command,("dist","build"),"none","typescript/javascript",_node_toolchain(root),tuple(x for x in ("package.json","pnpm-lock.yaml","package-lock.json",".nvmrc",".node-version") if (root/x).is_file()))
    if (root/"foundry.toml").is_file():return BuildProfile("foundry",("forge","build","--build-info"),("out","build-info"),"solc-json-ast","solidity",ToolchainSpec("solc",None,"foundry.toml","forge"),("foundry.toml",))
    if (root/"Cargo.toml").is_file():return BuildProfile("cargo",("cargo","check"),("target",),"none","rust",ToolchainSpec("rustc",None,"repository-default","cargo"),("Cargo.toml","Cargo.lock"))
    raise ValueError(f"unsupported or undetected project build system: {root}")

def _fingerprint_files(root:Path,files:Sequence[str])->str|None:
    digest=hashlib.sha256();seen=False
    for name in sorted(set(files)):
        p=root/name
        if p.is_file():seen=True;digest.update(name.encode());digest.update(b"\0");digest.update(hashlib.sha256(p.read_bytes()).digest())
    return digest.hexdigest() if seen else None

def _version(executable:str|None,root:Path)->str|None:
    if not executable:return None
    path=shutil.which(executable)
    if not path:return None
    try:r=subprocess.run([path,"--version"],cwd=root,capture_output=True,text=True,timeout=20,check=False)
    except (OSError,subprocess.TimeoutExpired):return None
    text=(r.stdout or r.stderr).strip();return text.splitlines()[0][:1000] if r.returncode==0 and text else None

def build_identity(root:str|Path,revision:str,repository:str="") -> BuildIdentity:
    root=Path(root).resolve();profile=detect_project(root)
    return BuildIdentity(repository,revision,profile,_fingerprint_files(root,profile.config_files),profile.toolchain,{profile.toolchain.tool:_version(profile.toolchain.executable,root)} if profile.toolchain else {},tuple(x for x in profile.config_files if "lock" in x.lower()))

class ProjectBuilder:
    def __init__(self,root:str|Path,profile:BuildProfile|None=None):self.root=Path(root).resolve();self.profile=profile or detect_project(root)
    def build(self,*,command:Sequence[str]|None=None,timeout:int=600)->BuildResult:
        argv=tuple(command or self.profile.command);executable=shutil.which(argv[0]);observed=_version(argv[0],self.root);config=_fingerprint_files(self.root,self.profile.config_files)
        if executable is None:return BuildResult("TOOLCHAIN_UNAVAILABLE",argv,127,"",f"executable unavailable: {argv[0]}",self.profile,{},(),observed,config,"NOT_ESTABLISHED")
        try:r=subprocess.run(list(argv),cwd=self.root,capture_output=True,text=True,timeout=timeout,check=False);status="SUCCEEDED" if r.returncode==0 else "FAILED";return BuildResult(status,argv,r.returncode,r.stdout,r.stderr,self.profile,{},(),observed,config,"LOCKED_DEPENDENCIES" if any("lock" in x.lower() for x in self.profile.config_files) and status=="SUCCEEDED" else "PARTIAL")
        except subprocess.TimeoutExpired as e:return BuildResult("TIMEOUT",argv,124,e.stdout or "",e.stderr or "",self.profile,{},(),observed,config,"NOT_ESTABLISHED")
