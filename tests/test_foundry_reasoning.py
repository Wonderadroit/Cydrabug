from cydra.foundry_reasoning import discover_foundry_invariant_candidates
from cydra.invariants import InvariantCandidate
from cydra.system_model import Edge, Node, SystemModel


class _AcceptedBuild:
    pass


def test_trusted_foundry_projection_feeds_existing_candidate_discovery(monkeypatch):
    model = SystemModel()
    model.add_node(Node("function:Vault:ast:10", "function", "deposit"))
    model.add_node(Node("state_variable:Vault:ast:20", "state_variable", "balance"))

    def project(target_model, build):
        assert build is accepted
        target_model.add_edge(Edge(
            "function:Vault:ast:10",
            "transition_expression",
            "state_variable:Vault:ast:20",
            {
                "evidence_backed": True,
                "candidate": True,
                "provenance": "solc-json-ast:contracts/Vault.sol",
                "confidence": 0.9,
                "ast_node_id": 30,
                "expression": "balance + amount",
                "operation": "+=",
                "rhs_expression": "amount",
                "dependency_ids": [],
            },
        ))
        return list(target_model.edges)

    accepted = _AcceptedBuild()
    monkeypatch.setattr("cydra.foundry_reasoning.project_accepted_ast_evidence", project)

    result = discover_foundry_invariant_candidates(model, accepted)

    assert result.evidence_edges
    assert result.candidates
    assert any(item.metadata["category"] == "state_transition_expression" for item in result.candidates)
    assert all(isinstance(item, InvariantCandidate) for item in result.candidates)


def test_foundry_reasoning_does_not_promote_candidates_to_verified_invariants(monkeypatch):
    model = SystemModel()
    model.add_node(Node("function:Vault:ast:10", "function", "deposit"))
    model.add_node(Node("state_variable:Vault:ast:20", "state_variable", "balance"))

    def project(target_model, build):
        target_model.add_edge(Edge(
            "function:Vault:ast:10", "writes", "state_variable:Vault:ast:20",
            {
                "evidence_backed": True,
                "candidate": True,
                "provenance": "solc-json-ast:contracts/Vault.sol",
                "confidence": 0.9,
                "ast_node_id": 30,
            },
        ))
        return list(target_model.edges)

    monkeypatch.setattr("cydra.foundry_reasoning.project_accepted_ast_evidence", project)

    result = discover_foundry_invariant_candidates(model, _AcceptedBuild())

    assert result.candidates
    assert not any(node.kind == "invariant" for node in model.nodes.values())
    assert not any(node.attributes.get("verification_state") for node in model.nodes.values())
