"""The index is a list of dictionaries: metadata about each chunk, small
enough to reason over before ever opening a chunk file. Never contains
revision content/wikitext.
"""
import json

from wikitools.indexing import build_index, write_chunks


def rev(revid, timestamp, user="A", sha1="x", is_revert=False):
    return {"revid": revid, "timestamp": timestamp, "sha1": sha1, "user": user,
            "comment": "", "tags": [], "size": 10, "is_revert": is_revert}


def test_build_index_one_entry_per_chunk():
    chunks = {
        "2024-01": [rev(1, "2024-01-01T00:00:00Z", user="Alice")],
        "2024-02": [rev(2, "2024-02-01T00:00:00Z", user="Bob", is_revert=True)],
    }
    index = build_index("2026 FIFA World Cup", chunks, chunk_dir="casefiles")
    assert len(index) == 2
    assert {e["month"] for e in index} == {"2024-01", "2024-02"}


def test_index_entry_has_required_metadata_fields():
    chunks = {"2024-01": [rev(1, "2024-01-01T00:00:00Z", user="Alice")]}
    index = build_index("2026 FIFA World Cup", chunks, chunk_dir="casefiles")
    entry = index[0]
    for field in ("chunk_id", "article", "month", "revision_count", "editors", "revert_count", "path"):
        assert field in entry


def test_index_counts_are_correct():
    chunks = {
        "2024-01": [
            rev(1, "2024-01-01T00:00:00Z", user="Alice"),
            rev(2, "2024-01-02T00:00:00Z", user="Bob", is_revert=True),
            rev(3, "2024-01-03T00:00:00Z", user="Alice"),
        ]
    }
    index = build_index("2026 FIFA World Cup", chunks, chunk_dir="casefiles")
    entry = index[0]
    assert entry["revision_count"] == 3
    assert entry["revert_count"] == 1
    assert sorted(entry["editors"]) == ["Alice", "Bob"]


def test_index_never_contains_wikitext_or_comment_fields():
    chunks = {"2024-01": [rev(1, "2024-01-01T00:00:00Z")]}
    index = build_index("2026 FIFA World Cup", chunks, chunk_dir="casefiles")
    dumped = json.dumps(index)
    assert "content" not in dumped
    assert '"comment"' not in dumped


def test_write_chunks_writes_one_json_file_per_month(tmp_path):
    chunks = {"2024-01": [rev(1, "2024-01-01T00:00:00Z")]}
    write_chunks("2026 FIFA World Cup", chunks, chunk_dir=str(tmp_path))
    written = json.load(open(tmp_path / "2026_FIFA_World_Cup_2024-01.json"))
    assert written[0]["revid"] == 1


def test_index_path_matches_written_chunk_filename(tmp_path):
    chunks = {"2024-01": [rev(1, "2024-01-01T00:00:00Z")]}
    write_chunks("2026 FIFA World Cup", chunks, chunk_dir=str(tmp_path))
    index = build_index("2026 FIFA World Cup", chunks, chunk_dir=str(tmp_path))
    assert (tmp_path / index[0]["path"].split("/")[-1]).exists() or __import__("os").path.exists(index[0]["path"])
