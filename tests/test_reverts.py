"""Revert detection is pure code, zero LLM. Three signals, in priority order:
  1. sha1 matches an earlier revision in the same article -> exact restore
  2. mw-undo / mw-rollback / mw-manual-revert tag -> API told us directly
  3. comment matches revert/rv/undid/rvv -> heuristic backstop
"""
from wikitools.reverts import detect_reverts


def rev(revid, sha1, user="A", comment="", tags=None, timestamp="2024-01-01T00:00:00Z"):
    return {
        "revid": revid, "sha1": sha1, "user": user,
        "comment": comment, "tags": tags or [], "timestamp": timestamp,
        "size": 100,
    }


def test_no_reverts_when_all_sha1_unique():
    revs = [rev(1, "aaa"), rev(2, "bbb"), rev(3, "ccc")]
    out = detect_reverts(revs)
    assert all(not r["is_revert"] for r in out)


def test_sha1_match_to_earlier_revision_is_a_revert():
    # rev 3 restores exactly what rev 1 looked like
    revs = [rev(1, "aaa", user="Alice"), rev(2, "bbb", user="Bob"), rev(3, "aaa", user="Alice")]
    out = detect_reverts(revs)
    assert out[0]["is_revert"] is False
    assert out[1]["is_revert"] is False
    assert out[2]["is_revert"] is True
    assert out[2]["reverted_editor"] == "Bob"


def test_rollback_tag_marks_revert_even_without_sha1_match():
    revs = [rev(1, "aaa", user="Alice"), rev(2, "bbb", user="Bob", tags=["mw-rollback"])]
    out = detect_reverts(revs)
    assert out[1]["is_revert"] is True
    assert out[1]["reverted_editor"] == "Alice"


def test_undo_tag_marks_revert():
    revs = [rev(1, "aaa", user="Alice"), rev(2, "bbb", user="Bob", tags=["mw-undo"])]
    out = detect_reverts(revs)
    assert out[1]["is_revert"] is True


def test_comment_regex_backstop_catches_revert_without_tag_or_sha1():
    revs = [rev(1, "aaa", user="Alice"),
            rev(2, "bbb", user="Bob", comment="Reverted edits by Alice to last version")]
    out = detect_reverts(revs)
    assert out[1]["is_revert"] is True


def test_comment_regex_is_case_insensitive_and_matches_rv_and_undid():
    revs = [
        rev(1, "aaa"),
        rev(2, "bbb", comment="rv vandalism"),
        rev(3, "ccc", comment="Undid revision 2"),
    ]
    out = detect_reverts(revs)
    assert out[1]["is_revert"] is True
    assert out[2]["is_revert"] is True


def test_unrelated_comment_is_not_a_revert():
    revs = [rev(1, "aaa"), rev(2, "bbb", comment="Fixed typo in infobox")]
    out = detect_reverts(revs)
    assert out[1]["is_revert"] is False


def test_reverted_editor_is_none_when_no_prior_editor_identifiable():
    revs = [rev(1, "aaa", user="Alice", tags=["mw-rollback"])]
    out = detect_reverts(revs)
    assert out[0]["is_revert"] is True
    assert out[0]["reverted_editor"] is None
