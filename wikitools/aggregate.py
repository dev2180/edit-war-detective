"""Deterministic pre-aggregation. Raw revisions in, a conclusion-ready case
brief out. This is the single biggest token saving in the pipeline: the
model never sees a revision, only the numbers computed from them.

Revisions must already be chronologically ordered and have is_revert /
reverted_editor set (see wikitools.reverts.detect_reverts).
"""
from collections import defaultdict


def _iso_week_key(timestamp):
    from datetime import datetime
    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def _parse_ts(timestamp):
    from datetime import datetime
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")


def _per_editor_stats(revisions):
    stats = defaultdict(lambda: {"edits": 0, "reverts_made": 0,
                                  "reverts_received": 0, "net_bytes": 0})
    prev_size = 0
    for r in revisions:
        editor = r["user"]
        delta = r["size"] - prev_size
        prev_size = r["size"]

        stats[editor]["edits"] += 1
        stats[editor]["net_bytes"] += delta

        if r["is_revert"]:
            stats[editor]["reverts_made"] += 1
            if r["reverted_editor"]:
                stats[r["reverted_editor"]]["reverts_received"] += 1

    return dict(stats)


def _revert_matrix(revisions):
    pair_counts = defaultdict(int)
    for r in revisions:
        if r["is_revert"] and r["reverted_editor"]:
            pair_counts[(r["user"], r["reverted_editor"])] += 1
    return [{"reverter": reverter, "reverted": reverted, "count": count}
            for (reverter, reverted), count in sorted(pair_counts.items())]


def _weekly_churn(revisions):
    churn = defaultdict(int)
    prev_size = 0
    for r in revisions:
        delta = r["size"] - prev_size
        prev_size = r["size"]
        churn[_iso_week_key(r["timestamp"])] += abs(delta)
    return dict(churn)


def _war_windows(revisions, threshold):
    """Slide over revert timestamps; flag any run where >= threshold
    reverts occur within a 24h span."""
    revert_times = [_parse_ts(r["timestamp"]) for r in revisions if r["is_revert"]]
    windows = []
    i = 0
    while i < len(revert_times):
        j = i
        while j + 1 < len(revert_times) and (revert_times[j + 1] - revert_times[i]).total_seconds() <= 86400:
            j += 1
        count = j - i + 1
        if count >= threshold:
            windows.append({
                "start": revert_times[i].isoformat() + "Z",
                "end": revert_times[j].isoformat() + "Z",
                "revert_count": count,
            })
            i = j + 1
        else:
            i += 1
    return windows


def _sample_comments(revisions, limit=5):
    return [r["comment"] for r in revisions if r["is_revert"] and r["comment"]][:limit]


def filter_combatants(per_editor, top_n_bystanders=0):
    """Drop editors who never made or received a revert -- pure bystanders
    add nothing to a war brief. Optionally keep the top N bystanders by
    edit count anyway (someone who made 50 edits is still relevant even
    if none were reverted).
    """
    combatants = {name: stats for name, stats in per_editor.items()
                  if stats["reverts_made"] > 0 or stats["reverts_received"] > 0}

    if top_n_bystanders:
        bystanders = {name: stats for name, stats in per_editor.items()
                      if name not in combatants}
        top_bystanders = sorted(bystanders.items(), key=lambda kv: -kv[1]["edits"])[:top_n_bystanders]
        combatants.update(dict(top_bystanders))

    return combatants


def aggregate(revisions, war_window_threshold=3):
    return {
        "per_editor": _per_editor_stats(revisions),
        "revert_matrix": _revert_matrix(revisions),
        "weekly_churn": _weekly_churn(revisions),
        "war_windows": _war_windows(revisions, war_window_threshold),
        "sample_comments": _sample_comments(revisions),
    }
