"""The index is a list of dictionaries: metadata about each chunk, small
enough to reason over before ever opening a chunk file. No wikitext, no
per-revision comment text -- just enough to decide which chunks to open.
"""
import json
import os


def _safe_article_slug(article):
    return article.replace(" ", "_")


def chunk_filename(article, month):
    return f"{_safe_article_slug(article)}_{month}.json"


def write_chunks(article, chunks, chunk_dir="casefiles"):
    """One JSON file per month chunk. Full revision metadata goes here
    (not in the index)."""
    os.makedirs(chunk_dir, exist_ok=True)
    for month, revisions in chunks.items():
        path = os.path.join(chunk_dir, chunk_filename(article, month))
        with open(path, "w") as f:
            json.dump(revisions, f)


def build_index(article, chunks, chunk_dir="casefiles"):
    """One dict per month chunk: chunk_id, article, month, revision_count,
    editors, revert_count, path. Never revision content or comments.
    """
    index = []
    for month, revisions in sorted(chunks.items()):
        editors = sorted({r["user"] for r in revisions})
        revert_count = sum(1 for r in revisions if r.get("is_revert"))
        index.append({
            "chunk_id": f"{_safe_article_slug(article)}_{month}",
            "article": article,
            "month": month,
            "revision_count": len(revisions),
            "editors": editors,
            "revert_count": revert_count,
            "path": os.path.join(chunk_dir, chunk_filename(article, month)),
        })
    return index
