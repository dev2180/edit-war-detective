"""Metadata filtering: the retrieval tool itself. Filter the index on
metadata, open ONLY the matching chunk files, keep only matching days,
hand back the aggregated brief. No embeddings, no vectors, no GPU.
"""
import json

from wikitools.aggregate import aggregate, filter_combatants


def investigate_conflict(index, article, start_date, end_date, editor=None):
    """Daily-resolution case brief for an article between two dates.

    Pass editor to narrow the brief to that editor's involvement (their
    edits, or edits made to revert them).
    """
    y0m0, y1m1 = start_date[:7], end_date[:7]

    # THE METADATA FILTER -- decide which chunks to open before opening any.
    hits = [
        entry for entry in index
        if entry["article"].lower() == article.lower()
        and y0m0 <= entry["month"] <= y1m1
    ]

    revisions = []
    for entry in hits:
        chunk_revisions = json.load(open(entry["path"]))
        for r in chunk_revisions:
            day = r["timestamp"][:10]
            if day < start_date or day > end_date:
                continue
            revisions.append(r)

    if editor:
        revisions = [
            r for r in revisions
            if r["user"] == editor or r.get("reverted_editor") == editor
        ]

    result = aggregate(revisions)
    result["per_editor"] = filter_combatants(result["per_editor"])
    result["chunks_opened"] = [entry["chunk_id"] for entry in hits]
    result["revision_count"] = len(revisions)
    return result
