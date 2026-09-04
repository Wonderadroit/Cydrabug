from cydra.solidity_model import project_solidity_ast


def sample_ast():
    return {
        "nodeType": "SourceUnit", "id": 1,
        "nodes": [{
            "nodeType": "ContractDefinition", "id": 2, "name": "Vault", "scope": 1,
            "nodes": [
                {"nodeType": "VariableDeclaration", "id": 3, "name": "balance", "scope": 2, "stateVariable": True,
                 "typeDescriptions": {"typeString": "uint256"}},
                {"nodeType": "FunctionDefinition", "id": 4, "name": "deposit", "scope": 2,
                 "visibility": "external", "stateMutability": "nonpayable", "body": {
                    "nodeType": "Block", "id": 5, "src": "0:20:0", "statements": [{
                        "nodeType": "Assignment", "id": 6, "operator": "+=",
                        "leftHandSide": {"nodeType": "Identifier", "id": 7, "name": "balance", "referencedDeclaration": 3, "src": "0:7:0"},
                        "rightHandSide": {"nodeType": "Identifier", "id": 8, "name": "amount", "referencedDeclaration": 9, "src": "10:6:0"}
                    }]
                }}
            ]
        }]
    }


def test_projection_preserves_compiler_declaration_identity():
    result = project_solidity_ast(sample_ast(), file="src/Vault.sol", source="balance += amount")
    model = result.model
    assert model.nodes["contract:src/Vault.sol:ast:2"].kind == "contract"
    assert model.nodes["state_variable:src/Vault.sol:ast:3"].kind == "state_variable"
    assert model.nodes["function:src/Vault.sol:ast:4"].kind == "function"


def test_assignment_produces_explicit_transition_and_write():
    result = project_solidity_ast(sample_ast(), file="src/Vault.sol", source="balance += amount")
    edges = result.model.edges
    assert any(e.relation == "transition_expression" and e.target.endswith(":ast:3") for e in edges)
    assert any(e.relation == "writes" and e.target.endswith(":ast:3") for e in edges)


def test_projection_does_not_create_security_claim():
    result = project_solidity_ast(sample_ast(), file="src/Vault.sol", source="balance += amount")
    assert not any(n.kind in {"finding", "security_claim", "security_predicate"} for n in result.model.nodes.values())
