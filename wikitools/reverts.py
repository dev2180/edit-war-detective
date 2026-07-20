"""Deterministic revert detection. Zero LLM calls.

Priority order per revision:
  1. sha1 matches an earlier revision in the same list -> exact restore
  2. mw-undo / mw-rollback / mw-manual-revert tag -> the API told us
  3. comment matches revert/rv/undid/rvv -> heuristic backstop
"""
import re

REVERT_TAGS = {"mw-undo", "mw-rollback", "mw-manual-revert"}
REVERT_COMMENT_RE = re.compile(r"\brevert|\brv\b|\bundid\b|\brvv\b", re.IGNORECASE)


def detect_reverts(revisions):
    """Revisions must be in chronological order (oldest first).

    Returns a new list of dicts, each with is_revert (bool) and
    reverted_editor (str or None) added.
    """
    seen_sha1_to_editor = {}
    out = []

    for r in revisions:
        rev = dict(r)
        is_revert = False
        reverted_editor = None

        is_sha1_match = r["sha1"] in seen_sha1_to_editor
        is_tagged = bool(set(r.get("tags") or []) & REVERT_TAGS)
        is_commented = bool(REVERT_COMMENT_RE.search(r.get("comment") or ""))

        if is_sha1_match or is_tagged or is_commented:
            is_revert = True
            reverted_editor = out[-1]["user"] if out else None

        rev["is_revert"] = is_revert
        rev["reverted_editor"] = reverted_editor
        out.append(rev)

        seen_sha1_to_editor.setdefault(r["sha1"], r["user"])

    return out
