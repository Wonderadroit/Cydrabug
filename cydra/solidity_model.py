"""Compiler-AST-backed Solidity projection into CYDRA's canonical SystemModel.

This adapter deliberately emits observed declarations, reads, writes and assignment
relationships only when the Solidity compiler supplies explicit declaration links.
It does not infer a vulnerability or security conclusion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from .system_model import Node, SystemModel


@dataclass(frozen=True)
class SolidityProjection:
    model: SystemModel
    contract_ids: tuple[str, ...]
    function_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    relationship_count: int


def _walk(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        if isinstance(node.get("nodeType"), str):
            yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _location(node: dict[str, Any]) -> list[int] | None:
    raw = node.get("src")
    if not isinstance(raw, str):
        return None
    parts = raw.split(":")
    if len(parts) != 3:
        return None
    try:
        return [int(parts[0]), int(parts[1]), int(parts[2])]
    except ValueError:
        return None


def _slice(source: str, node: dict[str, Any]) -> str | None:
    location = _location(node)
    if location is None:
        return None
    start, length, _ = location
    if start < 0 or length < 0 or start + length > len(source):
        return None
    return source[start:start + length].strip()


def _children(node: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield from _walk(node)


def project_solidity_ast(
    ast: dict[str, Any],
    *,
    file: str,
    source: str = "",
    canonical: SystemModel | None = None,
) -> SolidityProjection:
    """Project one solc AST into canonical declarations and evidence-backed edges."""
    model = canonical or SystemModel()
    declarations: dict[int, dict[str, Any]] = {}
    contracts: dict[int, str] = {}
    states: dict[int, str] = {}
    contract_ids: list[str] = []
    function_ids: list[str] = []
    state_ids: list[str] = []

    for node in _walk(ast):
        node_id = node.get("id")
        if not isinstance(node_id, int):
            continue
        declarations[node_id] = node
        if node.get("nodeType") == "ContractDefinition":
            name = node.get("name") or f"contract@{node_id}"
            cid = f"contract:{file}:ast:{node_id}"
            contracts[node_id] = cid
            model.add_node(Node(cid, "contract", str(name), {
                "source": file,
                "ast_node_id": node_id,
                "provenance": f"solc-json-ast:{file}",
                "identity_status": "compiler_declaration",
            }))
            contract_ids.append(cid)

    for node in _walk(ast):
        node_id = node.get("id")
        if not isinstance(node_id, int):
            continue
        if node.get("nodeType") != "VariableDeclaration" or node.get("stateVariable") is not True:
            continue
        name = node.get("name")
        scope = node.get("scope")
        if not isinstance(name, str) or not isinstance(scope, int) or scope not in contracts:
            continue
        sid = f"state_variable:{file}:ast:{node_id}"
        states[node_id] = sid
        model.add_node(Node(sid, "state_variable", name, {
            "source": file,
            "ast_node_id": node_id,
            "contract_id": contracts[scope],
            "type": ((node.get("typeDescriptions") or {}).get("typeString")
                     if isinstance(node.get("typeDescriptions"), dict) else None),
            "provenance": f"solc-json-ast:{file}",
            "identity_status": "compiler_declaration",
        }))
        model.connect(contracts[scope], "declares", sid, provenance=f"solc-json-ast:{file}", evidence_backed=True)
        state_ids.append(sid)

    relationship_count = 0
    for node in _walk(ast):
        node_id = node.get("id")
        if node.get("nodeType") != "FunctionDefinition" or not isinstance(node_id, int):
            continue
        scope = node.get("scope")
        if not isinstance(scope, int) or scope not in contracts:
            continue
        name = node.get("name") or ("constructor" if node.get("kind") == "constructor" else "fallback")
        fid = f"function:{file}:ast:{node_id}"
        model.add_node(Node(fid, "function", str(name), {
            "source": file,
            "ast_node_id": node_id,
            "contract_id": contracts[scope],
            "visibility": node.get("visibility"),
            "state_mutability": node.get("stateMutability"),
            "provenance": f"solc-json-ast:{file}",
            "identity_status": "compiler_declaration",
        }))
        model.connect(contracts[scope], "contains", fid, provenance=f"solc-json-ast:{file}", evidence_backed=True)
        function_ids.append(fid)
        body = node.get("body")
        if not isinstance(body, dict):
            continue

        identifiers = [x for x in _children(body) if x.get("nodeType") == "Identifier" and isinstance(x.get("referencedDeclaration"), int)]
        by_state = [x for x in identifiers if x["referencedDeclaration"] in states]
        written: set[int] = set()
        for assignment in _children(body):
            if assignment.get("nodeType") != "Assignment":
                continue
            lhs = assignment.get("leftHandSide")
            if not isinstance(lhs, dict):
                continue
            ref = lhs.get("referencedDeclaration")
            if isinstance(ref, int) and ref in states:
                written.add(ref)
                rhs = assignment.get("rightHandSide")
                deps = []
                if isinstance(rhs, dict):
                    deps = sorted({x["referencedDeclaration"] for x in _children(rhs) if x.get("nodeType") == "Identifier" and isinstance(x.get("referencedDeclaration"), int) and x["referencedDeclaration"] in states})
                expression = _slice(source, rhs) if isinstance(rhs, dict) else None
                if expression:
                    edge = model.edges
                    model.connect(fid, "transition_expression", states[ref],
                                  provenance=f"solc-json-ast:{file}", evidence_backed=True, candidate=True,
                                  confidence=0.95, ast_node_id=assignment.get("id"),
                                  function_ast_node_id=node_id, target_ast_node_id=ref,
                                  source_location=_location(assignment), operation=assignment.get("operator"),
                                  expression=expression,
                                  dependency_ids=[states[d] for d in deps])
                    relationship_count += 1

        for identifier in by_state:
            ref = identifier["referencedDeclaration"]
            relation = "writes" if ref in written and identifier.get("id") == ref else "reads"
            # The compiler's declaration ID is authoritative; identifier id and declaration id
            # are intentionally kept separate so a write cannot be fabricated by name matching.
            if ref in written:
                relation = "writes" if identifier.get("id") != ref else "reads"
            model.connect(fid, relation, states[ref],
                          provenance=f"solc-json-ast:{file}", evidence_backed=True, candidate=True,
                          confidence=0.90, ast_node_id=identifier.get("id"),
                          function_ast_node_id=node_id, target_ast_node_id=ref,
                          source_location=_location(identifier))
            relationship_count += 1

    return SolidityProjection(model, tuple(contract_ids), tuple(function_ids), tuple(state_ids), relationship_count)
