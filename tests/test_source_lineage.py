from cydra.source_lineage import (
    EvidenceKind,
    LineageStatus,
    SourceCandidate,
    resolve_source_identity,
)


REVISION = "63772fd872af472ced58b009499355f3430c2a86"


def test_exact_git_identity_is_verified():
    result = resolve_source_identity(
        REVISION,
        (
            SourceCandidate(
                locator="https://example.invalid/project.git",
                observed_revision=REVISION,
                advertised_revision_available=True,
                observed_head_matches=True,
            ),
        ),
    )

    assert result.status is LineageStatus.VERIFIED
    assert result.ready_for_analysis is True
    assert result.selected_locator == "https://example.invalid/project.git"
    assert result.exact_identity_verified is True
    assert EvidenceKind.EXACT_GIT_OBJECT in {e.kind for e in result.evidence}
    assert EvidenceKind.EXACT_HEAD_MATCH in {e.kind for e in result.evidence}


def test_object_presence_alone_is_not_verified():
    result = resolve_source_identity(
        REVISION,
        (
            SourceCandidate(
                locator="https://example.invalid/project.git",
                observed_revision="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                advertised_revision_available=True,
                observed_head_matches=False,
            ),
        ),
    )

    assert result.status is LineageStatus.UNRESOLVED
    assert result.ready_for_analysis is False
    assert result.exact_identity_verified is False


def test_head_match_flag_with_wrong_revision_is_not_verified():
    result = resolve_source_identity(
        REVISION,
        (
            SourceCandidate(
                locator="https://example.invalid/project.git",
                observed_revision="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                advertised_revision_available=True,
                observed_head_matches=True,
            ),
        ),
    )

    assert result.status is LineageStatus.UNRESOLVED
    assert result.ready_for_analysis is False
    assert EvidenceKind.IDENTITY_CONTRADICTION in {e.kind for e in result.evidence}


def test_declared_fork_lineage_does_not_become_verified():
    result = resolve_source_identity(
        REVISION,
        (
            SourceCandidate(
                locator="https://github.com/immunefi-team/audit-comp-ens",
                observed_revision="cda79acaad59711b943fc68207ebb3f1d0ff8596",
                advertised_revision_available=False,
                declared_lineage=True,
            ),
        ),
    )

    assert result.status is LineageStatus.PROVENANCE_SUPPORTED
    assert result.ready_for_analysis is False
    assert result.exact_identity_verified is False
    assert EvidenceKind.DECLARED_LINEAGE in {e.kind for e in result.evidence}
    assert EvidenceKind.OBJECT_ABSENT in {e.kind for e in result.evidence}


def test_ancestry_without_exact_object_remains_provenance_only():
    result = resolve_source_identity(
        REVISION,
        (
            SourceCandidate(
                locator="https://example.invalid/snapshot.git",
                observed_revision="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                advertised_revision_available=False,
                lineage_to_advertised=True,
            ),
        ),
    )

    assert result.status is LineageStatus.PROVENANCE_SUPPORTED
    assert result.exact_identity_verified is False


def test_missing_lineage_evidence_remains_unresolved():
    result = resolve_source_identity(
        REVISION,
        (
            SourceCandidate(
                locator="https://example.invalid/project.git",
                observed_revision="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                advertised_revision_available=False,
            ),
        ),
    )

    assert result.status is LineageStatus.UNRESOLVED
    assert result.ready_for_analysis is False
    assert result.selected_locator is None


def test_explicit_contradiction_is_mismatch_when_no_candidate_survives():
    result = resolve_source_identity(
        REVISION,
        (
            SourceCandidate(
                locator="https://example.invalid/project-a.git",
                observed_revision="cccccccccccccccccccccccccccccccccccccccc",
                contradictory_identity=True,
            ),
            SourceCandidate(
                locator="https://example.invalid/project-b.git",
                observed_revision="dddddddddddddddddddddddddddddddddddddddd",
                contradictory_identity=True,
            ),
        ),
    )

    assert result.status is LineageStatus.MISMATCH
    assert result.ready_for_analysis is False
