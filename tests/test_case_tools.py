"""The two tool functions exposed to the LLM, as pure/testable wrappers.
No network, no LLM -- these are what run_tools() in engine.py calls.
"""
import json

from wikitools.case_tools import (
    investigate_and_measure,
    build_ledger_report,
    retrieve_raw_revisions,
    find_safe_edit_window,
)


def rev(revid, timestamp, user, size, is_revert=False, reverted_editor=None, comment=""):
    return {"revid": revid, "timestamp": timestamp, "user": user, "size": size,
            "is_revert": is_revert, "reverted_editor": reverted_editor,
            "comment": comment, "sha1": str(revid), "tags": []}


def make_casefile(tmp_path):
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-02T00:00:00Z", "Bob", 120, is_revert=True, reverted_editor="Alice"),
    ]
    path = tmp_path / "fifa_2024-01.json"
    json.dump(revs, open(path, "w"))
    index = [{"chunk_id": "fifa_2024-01", "article": "2026 FIFA World Cup", "month": "2024-01",
              "revision_count": 2, "editors": ["Alice", "Bob"], "revert_count": 1, "path": str(path)}]
    return index, revs


def test_investigate_and_measure_returns_result_and_measurement(tmp_path):
    index, all_revs = make_casefile(tmp_path)
    result, measurement = investigate_and_measure(
        index, all_revs, "2026 FIFA World Cup", "2024-01-01", "2024-12-31")

    assert result["revision_count"] == 2
    assert measurement["after_tokens"] > 0
    # the full-content baseline dwarfs everything even on a 2-revision
    # fixture, since it's revisions * ~61K tokens each; metadata-vs-brief
    # compression only shows up at realistic volume (validated in
    # step5_prove_it.py against the real case file: ~20x)
    assert measurement["before_full_content_tokens"] > measurement["before_metadata_tokens"]
    assert measurement["revisions_in_range"] == 2


def test_investigate_and_measure_missing_article_raises_value_error(tmp_path):
    index, all_revs = make_casefile(tmp_path)
    try:
        investigate_and_measure(index, all_revs, "", "2024-01-01", "2024-12-31")
        assert False, "expected ValueError for missing article"
    except ValueError:
        pass


def test_build_ledger_report_computes_compression_and_cost(tmp_path):
    index, all_revs = make_casefile(tmp_path)
    _, measurement = investigate_and_measure(
        index, all_revs, "2026 FIFA World Cup", "2024-01-01", "2024-12-31")

    report = build_ledger_report(measurement, price_per_million_tokens=0.59, queries_per_day=50)
    assert report["compression_vs_full_content"] > 1
    assert "compression_vs_metadata" in report
    assert "yearly_cost" in report["cost_projection"]["savings"]


def test_build_ledger_report_with_no_prior_measurement_raises():
    try:
        build_ledger_report(None, price_per_million_tokens=0.59, queries_per_day=50)
        assert False, "expected ValueError when no investigation has run yet"
    except ValueError:
        pass


# --- retrieval / augment split for the safe-edit-window problem statement ---

def test_retrieve_raw_revisions_filters_by_date_range_only_no_compression():
    all_revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2025-06-01T00:00:00Z", "Bob", 120),
    ]
    raw = retrieve_raw_revisions(all_revs, "2025-01-01", "2025-12-31")
    assert len(raw) == 1
    assert raw[0]["revid"] == 2
    # retrieval returns the SAME shape it was given -- no aggregation, no dropped fields
    assert raw[0] == all_revs[1]


def test_find_safe_edit_window_requires_live_dates():
    try:
        find_safe_edit_window([], live_start_date="", live_end_date="2026-07-01")
        assert False, "expected ValueError for missing live_start_date"
    except ValueError:
        pass


def test_find_safe_edit_window_returns_verdict_and_measurement():
    tuesdays = ["2024-01-02", "2024-01-09", "2024-01-16", "2024-01-23", "2024-01-30", "2024-02-06"]
    baseline = [rev(i, f"{d}T10:00:00Z", "Alice", 100) for i, d in enumerate(tuesdays)]  # all safe

    live = [rev(200, "2026-06-02T10:00:00Z", "Bob", 100)]  # same Tue-10 bucket, still safe

    result, measurement = find_safe_edit_window(
        baseline + live, live_start_date="2026-06-01", live_end_date="2026-07-20", min_edits=5)

    assert result["safest_baseline_window"] == "Tue-10"
    assert result["still_safe"] is True
    assert measurement["after_tokens"] > 0
    assert measurement["before_tokens"] > measurement["after_tokens"]
