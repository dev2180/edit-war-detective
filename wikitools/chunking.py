"""Chunking is a for loop. The seam is the calendar month."""
from collections import defaultdict


def chunk_by_month(revisions):
    """Group revisions by their timestamp's YYYY-MM. Order within a group
    is preserved from the input order.
    """
    chunks = defaultdict(list)
    for r in revisions:
        month_key = r["timestamp"][:7]  # "2024-01-05T10:00:00Z" -> "2024-01"
        chunks[month_key].append(r)
    return dict(chunks)
