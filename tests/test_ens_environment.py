from cydra.ens_build_identity import ENS_NODE_REQUIREMENT, ENS_PNPM_VERSION, ENS_TSGO_VERSION
from cydra.ens_environment import authoritative_requirements


def test_authoritative_ens_requirements_bind_build_identity():
    requirements = authoritative_requirements()
    assert [(r.name, r.version) for r in requirements] == [
        ("node", ENS_NODE_REQUIREMENT),
        ("pnpm", ENS_PNPM_VERSION),
        ("tsgo", ENS_TSGO_VERSION),
    ]
    assert all(r.required for r in requirements)
    assert [r.authority for r in requirements] == ["PLATFORM", "PLATFORM", "PROJECT"]
    assert all(r.purpose == "canonical-build" for r in requirements)
