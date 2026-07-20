"""Chunking is a for loop. The natural seam here is the calendar month,
taken from each revision's timestamp.
"""
from wikitools.chunking import chunk_by_month


def rev(revid, timestamp):
    return {"revid": revid, "timestamp": timestamp, "sha1": str(revid), "user": "A",
            "comment": "", "tags": [], "size": 10}


def test_groups_revisions_by_year_month():
    revs = [
        rev(1, "2024-01-05T10:00:00Z"),
        rev(2, "2024-01-20T10:00:00Z"),
        rev(3, "2024-02-01T10:00:00Z"),
    ]
    chunks = chunk_by_month(revs)
    assert set(chunks.keys()) == {"2024-01", "2024-02"}
    assert len(chunks["2024-01"]) == 2
    assert len(chunks["2024-02"]) == 1


def test_chunk_membership_sums_to_original_count():
    revs = [rev(i, f"2024-0{(i % 3) + 1}-01T00:00:00Z") for i in range(1, 10)]
    chunks = chunk_by_month(revs)
    total = sum(len(v) for v in chunks.values())
    assert total == len(revs)


def test_empty_input_returns_empty_dict():
    assert chunk_by_month([]) == {}


def test_revisions_within_a_chunk_preserve_original_order():
    revs = [
        rev(1, "2024-01-05T10:00:00Z"),
        rev(2, "2024-01-01T10:00:00Z"),
    ]
    chunks = chunk_by_month(revs)
    assert [r["revid"] for r in chunks["2024-01"]] == [1, 2]
