"""Compiler-AST-backed Solidity projection into CYDRA's canonical SystemModel."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator
from .system_model import Node, SystemModel

@dataclass(frozen=True)
class SolidityBuildInfoSource:
    build_info_file: str
    source_file: str
    ast: dict[str, Any]
    source: str
    solc_version: str | None
    solc_long_version: str | None
    source_fingerprint: str

@dataclass(frozen=True)
class SolidityProjection:
    model: SystemModel
    contract_ids: tuple[str, ...]
    function_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    relationship_count: int

def _walk(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        if isinstance(node.get("nodeType"), str): yield node
        for value in node.values(): yield from _walk(value)
    elif isinstance(node, list):
        for value in node: yield from _walk(value)

def _location(node: dict[str, Any]) -> list[int] | None:
    raw = node.get("src")
    if not isinstance(raw, str): return None
    parts = raw.split(":")
    if len(parts) != 3: return None
    try: return [int(parts[0]), int(parts[1]), int(parts[2])]
    except ValueError: return None

def _slice(source: str, node: dict[str, Any] | None) -> str | None:
    if not node: return None
    loc = _location(node)
    if loc is None: return None
    start, length, _ = loc
    if start < 0 or length < 0 or start + length > len(source): return None
    return source[start:start + length].strip()

def _source_fingerprint(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()

def load_foundry_build_info(root: str | Path) -> tuple[SolidityBuildInfoSource, ...]:
    """Load only build-info ASTs carrying compiler and source identity.

    Missing AST, source content, or compiler identity is skipped rather than
    converted into authoritative semantic evidence.
    """
    root = Path(root).resolve()
    base = root / "build-info"
    if not base.is_dir(): return ()
    records: list[SolidityBuildInfoSource] = []
    for path in sorted(base.glob("*.json")):
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError): continue
        solc = data.get("solcVersion")
        long_version = data.get("solcLongVersion")
        output = data.get("output")
        inputs = data.get("input", {}).get("sources") if isinstance(data.get("input"), dict) else None
        sources = output.get("sources") if isinstance(output, dict) else None
        if not isinstance(sources, dict) or not isinstance(inputs, dict): continue
        if not isinstance(solc, str) or not solc.strip(): continue
        for source_file in sorted(sources):
            source_entry = sources.get(source_file)
            input_entry = inputs.get(source_file)
            ast = source_entry.get("ast") if isinstance(source_entry, dict) else None
            source = input_entry.get("content") if isinstance(input_entry, dict) else None
            if not isinstance(ast, dict) or not isinstance(source, str): continue
            records.append(SolidityBuildInfoSource(
                path.relative_to(root).as_posix(), source_file, ast, source,
                solc, long_version if isinstance(long_version, str) else None,
                _source_fingerprint(source),
            ))
    return tuple(records)

def project_solidity_ast(ast: dict[str, Any], *, file: str, source: str = "", canonical: SystemModel | None = None) -> SolidityProjection:
    """Project declarations and compiler-linked state relationships; never a finding."""
    model = canonical or SystemModel()
    contracts: dict[int, str] = {}
    states: dict[int, str] = {}
    contract_ids: list[str] = []
    function_ids: list[str] = []
    state_ids: list[str] = []
    provenance = f"solc-json-ast:{file}"
    for node in _walk(ast):
        node_id = node.get("id")
        if isinstance(node_id, int) and node.get("nodeType") == "ContractDefinition":
            cid = f"contract:{file}:ast:{node_id}"
            contracts[node_id] = cid
            model.add_node(Node(cid, "contract", str(node.get("name") or f"contract@{node_id}"), {"source": file, "ast_node_id": node_id, "provenance": provenance, "identity_status": "compiler_declaration"}))
            contract_ids.append(cid)
    for node in _walk(ast):
        node_id, scope = node.get("id"), node.get("scope")
        if not isinstance(node_id, int) or node.get("nodeType") != "VariableDeclaration" or node.get("stateVariable") is not True: continue
        if not isinstance(scope, int) or scope not in contracts or not isinstance(node.get("name"), str): continue
        sid = f"state_variable:{file}:ast:{node_id}"
        states[node_id] = sid
        td = node.get("typeDescriptions")
        model.add_node(Node(sid, "state_variable", node["name"], {"source": file, "ast_node_id": node_id, "contract_id": contracts[scope], "type": td.get("typeString") if isinstance(td, dict) else None, "provenance": provenance, "identity_status": "compiler_declaration"}))
        model.connect(contracts[scope], "declares", sid, provenance=provenance, evidence_backed=True)
        state_ids.append(sid)
    relationships = 0
    for function in _walk(ast):
        fid_ast, scope = function.get("id"), function.get("scope")
        if function.get("nodeType") != "FunctionDefinition" or not isinstance(fid_ast, int) or not isinstance(scope, int) or scope not in contracts: continue
        name = function.get("name") or ("constructor" if function.get("kind") == "constructor" else "fallback")
        fid = f"function:{file}:ast:{fid_ast}"
        model.add_node(Node(fid, "function", str(name), {"source": file, "ast_node_id": fid_ast, "contract_id": contracts[scope], "visibility": function.get("visibility"), "state_mutability": function.get("stateMutability"), "provenance": provenance, "identity_status": "compiler_declaration"}))
        model.connect(contracts[scope], "contains", fid, provenance=provenance, evidence_backed=True)
        function_ids.append(fid)
        body = function.get("body")
        if not isinstance(body, dict): continue
        write_ids: set[int] = set()
        for node in _walk(body):
            if node.get("nodeType") != "Assignment": continue
            lhs = node.get("leftHandSide")
            if not isinstance(lhs, dict): continue
            ref, lhs_id = lhs.get("referencedDeclaration"), lhs.get("id")
            if not isinstance(ref, int) or ref not in states or not isinstance(lhs_id, int): continue
            write_ids.add(lhs_id)
            rhs = node.get("rightHandSide")
            deps = sorted({x["referencedDeclaration"] for x in _walk(rhs) if x.get("nodeType") == "Identifier" and isinstance(x.get("referencedDeclaration"), int) and x["referencedDeclaration"] in states}) if isinstance(rhs, dict) else []
            expression = _slice(source, rhs if isinstance(rhs, dict) else None)
            if expression:
                model.connect(fid, "transition_expression", states[ref], provenance=provenance, evidence_backed=True, candidate=True, confidence=0.95, ast_node_id=node.get("id"), function_ast_node_id=fid_ast, target_ast_node_id=ref, source_location=_location(node), operation=node.get("operator"), expression=expression, dependency_ids=[states[d] for d in deps])
                relationships += 1
        for identifier in _walk(body):
            if identifier.get("nodeType") != "Identifier": continue
            ref, identifier_id = identifier.get("referencedDeclaration"), identifier.get("id")
            if not isinstance(ref, int) or ref not in states: continue
            relation = "writes" if isinstance(identifier_id, int) and identifier_id in write_ids else "reads"
            model.connect(fid, relation, states[ref], provenance=provenance, evidence_backed=True, candidate=True, confidence=0.90, ast_node_id=identifier_id, function_ast_node_id=fid_ast, target_ast_node_id=ref, source_location=_location(identifier))
            relationships += 1
    return SolidityProjection(model, tuple(contract_ids), tuple(function_ids), tuple(state_ids), relationships)
