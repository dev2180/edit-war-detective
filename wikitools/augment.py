"""The augment stage for the safe-edit-window problem statement.

Retrieval hands over raw revisions (see wikitools.case_tools.retrieve_raw_revisions).
This module is where compression actually happens for THIS question:
bucket by day-of-week + hour, compute a revert-rate table, find the
historically safest bucket, and check whether it's still safe during a
given live period (e.g. a tournament). Pure functions, deterministic,
zero LLM calls -- exactly the "pre-aggregate wherever the tool's
resolution is finer than the user's question" move.
"""
from collections import defaultdict
from datetime import datetime

_WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def day_hour_key(timestamp):
    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    return f"{_WEEKDAY_ABBR[dt.weekday()]}-{dt.hour:02d}"


def build_safety_table(revisions):
    """One bucket per (weekday, hour): edit count, revert count, rate."""
    buckets = defaultdict(lambda: {"edits": 0, "reverts": 0})
    for r in revisions:
        key = day_hour_key(r["timestamp"])
        buckets[key]["edits"] += 1
        if r.get("is_revert"):
            buckets[key]["reverts"] += 1

    table = {}
    for key, counts in buckets.items():
        table[key] = {
            "edits": counts["edits"],
            "reverts": counts["reverts"],
            "rate": counts["reverts"] / counts["edits"],
        }
    return table


def safest_window(table, min_edits=5):
    """The bucket with the lowest revert rate among buckets that have
    enough samples to trust (min_edits) -- avoids a 1-edit, 0-revert
    bucket looking "perfectly safe" by sample-size luck.
    """
    candidates = [(key, stats) for key, stats in table.items() if stats["edits"] >= min_edits]
    if not candidates:
        return None
    return min(candidates, key=lambda kv: kv[1]["rate"])


def augment_safety_report(baseline_revisions, live_revisions, min_edits=5):
    """Find the historically safest day/hour window from baseline history,
    then check that same window's revert rate during a live period
    (e.g. a tournament). This IS the answer: one bucket, two rates, one
    verdict -- no revision text ever leaves this function.
    """
    baseline_table = build_safety_table(baseline_revisions)
    result = safest_window(baseline_table, min_edits=min_edits)

    if result is None:
        return {
            "safest_baseline_window": None,
            "baseline_rate": None,
            "live_rate": None,
            "still_safe": None,
        }

    key, baseline_stats = result
    live_table = build_safety_table(live_revisions)
    live_stats = live_table.get(key, {"edits": 0, "reverts": 0, "rate": 0.0})

    # "Still safe" if the live rate hasn't gotten worse than baseline.
    still_safe = live_stats["rate"] <= baseline_stats["rate"]

    return {
        "safest_baseline_window": key,
        "baseline_rate": baseline_stats["rate"],
        "baseline_edits_sampled": baseline_stats["edits"],
        "live_rate": live_stats["rate"],
        "live_edits_sampled": live_stats["edits"],
        "still_safe": still_safe,
    }
