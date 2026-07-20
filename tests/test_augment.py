"""The augment stage. Retrieval (a separate tool) hands over RAW revisions;
augment is where compression for THIS problem statement happens: bucket by
day-of-week + hour, compute a revert-rate table, find the historically
safest window, and check whether that window is still safe during a given
period (e.g. a live tournament). Pure functions, no network, no LLM.
"""
from wikitools.augment import (
    day_hour_key,
    build_safety_table,
    safest_window,
    augment_safety_report,
)


def rev(revid, timestamp, user="A", is_revert=False, size=100):
    return {"revid": revid, "timestamp": timestamp, "user": user,
            "is_revert": is_revert, "size": size, "sha1": str(revid),
            "comment": "", "tags": [], "reverted_editor": None}


def test_day_hour_key_formats_weekday_and_hour():
    # 2024-01-01 is a Monday
    assert day_hour_key("2024-01-01T04:30:00Z") == "Mon-04"
    # 2024-01-07 is a Sunday
    assert day_hour_key("2024-01-07T23:00:00Z") == "Sun-23"


def test_build_safety_table_counts_edits_and_reverts_per_bucket():
    revs = [
        rev(1, "2024-01-01T04:00:00Z"),                      # Mon-04 edit
        rev(2, "2024-01-08T04:00:00Z", is_revert=True),      # Mon-04 revert
        rev(3, "2024-01-01T04:00:00Z"),                      # Mon-04 edit
        rev(4, "2024-01-02T10:00:00Z"),                      # Tue-10 edit
    ]
    table = build_safety_table(revs)
    assert table["Mon-04"]["edits"] == 3
    assert table["Mon-04"]["reverts"] == 1
    assert table["Mon-04"]["rate"] == 1 / 3
    assert table["Tue-10"]["edits"] == 1
    assert table["Tue-10"]["rate"] == 0.0


def test_build_safety_table_on_empty_input():
    assert build_safety_table([]) == {}


def test_safest_window_picks_lowest_rate_meeting_min_edits():
    table = {
        "Mon-04": {"edits": 10, "reverts": 5, "rate": 0.5},
        "Tue-10": {"edits": 10, "reverts": 1, "rate": 0.1},
        "Wed-02": {"edits": 2, "reverts": 0, "rate": 0.0},  # too few edits, excluded
    }
    key, stats = safest_window(table, min_edits=5)
    assert key == "Tue-10"
    assert stats["rate"] == 0.1


def test_safest_window_returns_none_when_nothing_meets_threshold():
    table = {"Mon-04": {"edits": 2, "reverts": 0, "rate": 0.0}}
    result = safest_window(table, min_edits=5)
    assert result is None


_TUESDAYS = ["2024-01-02", "2024-01-09", "2024-01-16", "2024-01-23", "2024-01-30", "2024-02-06"]
_MONDAYS = ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22", "2024-01-29", "2024-02-05"]


def test_augment_safety_report_compares_baseline_and_live_period():
    # Baseline: Tue-10 is safest (0 reverts in 6 edits). During the "live"
    # period, that same bucket gets hit with reverts -> no longer safe.
    baseline = [rev(i, f"{d}T10:00:00Z") for i, d in enumerate(_TUESDAYS)]  # Tue-10, all safe
    baseline += [rev(100 + i, f"{d}T04:00:00Z", is_revert=(i % 2 == 0))
                 for i, d in enumerate(_MONDAYS)]  # Mon-04, half reverted

    live = [rev(200, "2026-06-02T10:00:00Z", is_revert=True),   # Tue-10 during tournament
            rev(201, "2026-06-02T10:00:00Z")]

    report = augment_safety_report(
        baseline_revisions=baseline,
        live_revisions=live,
        min_edits=5,
    )
    assert report["safest_baseline_window"] == "Tue-10"
    assert report["baseline_rate"] == 0.0
    assert report["live_rate"] == 0.5
    assert report["still_safe"] is False


def test_augment_safety_report_still_safe_when_live_rate_stays_low():
    baseline = [rev(i, f"{d}T10:00:00Z") for i, d in enumerate(_TUESDAYS)]
    live = [rev(200, "2026-06-02T10:00:00Z"), rev(201, "2026-06-09T10:00:00Z")]

    report = augment_safety_report(baseline_revisions=baseline, live_revisions=live, min_edits=5)
    assert report["still_safe"] is True


def test_augment_safety_report_handles_no_baseline_safe_window():
    baseline = [rev(i, "2024-01-01T04:00:00Z", is_revert=True) for i in range(2)]
    live = [rev(200, "2026-06-02T10:00:00Z")]
    report = augment_safety_report(baseline_revisions=baseline, live_revisions=live, min_edits=5)
    assert report["safest_baseline_window"] is None
    assert report["still_safe"] is None
