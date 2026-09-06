from cydra.live_contest import _extract_revision_assertion


def test_revision_extraction_ignores_unrelated_hashes_before_audited_revision():
    unrelated = "d0a31c5b4b8e0f653b9b0f856191612d3072976f"
    audited = "63772fd872af472ced58b009499355f3430c2a86"
    content = (
        f'<a href="https://github.com/example/repo/commit/{unrelated}">'
        f"context</a> Audited revision — commit hash: `{audited}`"
    )

    assert _extract_revision_assertion(content) == audited


def test_revision_extraction_requires_audited_revision_label():
    unrelated = "d0a31c5b4b8e0f653b9b0f856191612d3072976f"
    assert _extract_revision_assertion(f"context commit {unrelated}") is None
