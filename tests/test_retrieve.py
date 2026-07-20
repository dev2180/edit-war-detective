"""The retrieval tool itself: filter the index on metadata, open ONLY the
matching chunk files, keep only matching days, hand back the aggregated
brief. No embeddings, no vectors -- the MVP rule, running.
"""
import json

import pytest

from wikitools.retrieve import investigate_conflict


def rev(revid, timestamp, user, size, is_revert=False, reverted_editor=None, comment=""):
    return {"revid": revid, "timestamp": timestamp, "user": user, "size": size,
            "is_revert": is_revert, "reverted_editor": reverted_editor,
            "comment": comment, "sha1": str(revid), "tags": []}


@pytest.fixture
def casefile(tmp_path):
    jan = [rev(1, "2024-01-05T00:00:00Z", "Alice", 100),
           rev(2, "2024-01-10T00:00:00Z", "Bob", 120, is_revert=True, reverted_editor="Alice")]
    feb = [rev(3, "2024-02-01T00:00:00Z", "Carol", 90)]
    other_article = [rev(4, "2024-01-01T00:00:00Z", "Dave", 50)]

    jan_path = tmp_path / "fifa_2024-01.json"
    feb_path = tmp_path / "fifa_2024-02.json"
    other_path = tmp_path / "other_2024-01.json"
    json.dump(jan, open(jan_path, "w"))
    json.dump(feb, open(feb_path, "w"))
    json.dump(other_article, open(other_path, "w"))

    index = [
        {"chunk_id": "fifa_2024-01", "article": "2026 FIFA World Cup", "month": "2024-01",
         "revision_count": 2, "editors": ["Alice", "Bob"], "revert_count": 1, "path": str(jan_path)},
        {"chunk_id": "fifa_2024-02", "article": "2026 FIFA World Cup", "month": "2024-02",
         "revision_count": 1, "editors": ["Carol"], "revert_count": 0, "path": str(feb_path)},
        {"chunk_id": "other_2024-01", "article": "Some Other Article", "month": "2024-01",
         "revision_count": 1, "editors": ["Dave"], "revert_count": 0, "path": str(other_path)},
    ]
    return index


def test_filters_to_matching_article_only(casefile):
    result = investigate_conflict(casefile, "2026 FIFA World Cup", "2024-01-01", "2024-12-31")
    assert result["revision_count"] == 3  # jan(2) + feb(1), not the other article
    assert "Dave" not in result["per_editor"]


def test_article_match_is_case_insensitive(casefile):
    result = investigate_conflict(casefile, "2026 fifa world cup", "2024-01-01", "2024-12-31")
    assert result["revision_count"] == 3


def test_date_range_filters_out_of_range_months(casefile):
    result = investigate_conflict(casefile, "2026 FIFA World Cup", "2024-01-01", "2024-01-31")
    assert result["revision_count"] == 2  # only jan chunk
    assert "Carol" not in result["per_editor"]


def test_only_matching_chunks_are_opened(casefile):
    result = investigate_conflict(casefile, "2026 FIFA World Cup", "2024-01-01", "2024-01-31")
    assert result["chunks_opened"] == ["fifa_2024-01"]


def test_editor_filter_narrows_to_that_editors_involvement(casefile):
    result = investigate_conflict(casefile, "2026 FIFA World Cup", "2024-01-01",
                                   "2024-12-31", editor="Alice")
    # Alice edited rev1, and was reverted in rev2 -> both involve her
    assert result["revision_count"] == 2
    assert "Carol" not in result["per_editor"]


def test_no_matching_article_returns_empty_shell(casefile):
    result = investigate_conflict(casefile, "Nonexistent Article", "2024-01-01", "2024-12-31")
    assert result["revision_count"] == 0
    assert result["per_editor"] == {}


def test_per_editor_drops_bystanders_who_never_touched_a_revert(tmp_path):
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-02T00:00:00Z", "Bob", 120, is_revert=True, reverted_editor="Alice"),
        rev(3, "2024-01-03T00:00:00Z", "SinglePassingEditor", 130),
    ]
    path = tmp_path / "fifa_2024-01.json"
    json.dump(revs, open(path, "w"))
    index = [{"chunk_id": "fifa_2024-01", "article": "2026 FIFA World Cup", "month": "2024-01",
              "revision_count": 3, "editors": ["Alice", "Bob", "SinglePassingEditor"],
              "revert_count": 1, "path": str(path)}]

    result = investigate_conflict(index, "2026 FIFA World Cup", "2024-01-01", "2024-12-31")
    assert "SinglePassingEditor" not in result["per_editor"]
    assert "Alice" in result["per_editor"]
    assert "Bob" in result["per_editor"]
    # revision_count still reflects everything actually opened, not just combatants
    assert result["revision_count"] == 3
