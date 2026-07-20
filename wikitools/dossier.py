"""build_dossier: one call that assembles every field the frontend needs --
the boss-fight token stages, the safe-window verdict, the war-window
heatmap, and the rogues'-gallery roster/matrix -- from cached data. Pure
glue over already-tested wikitools functions (retrieve, augment, aggregate,
ledger); no network, no LLM.
"""
import json

from wikitools.aggregate import aggregate, filter_combatants
from wikitools.augment import build_safety_table
from wikitools.case_tools import find_safe_edit_window, retrieve_raw_revisions
from wikitools.ledger import count_tokens, compression_factor, project_cost


def _roster(per_editor, roster_size):
    combatants = filter_combatants(per_editor)
    ranked = sorted(
        combatants.items(),
        key=lambda kv: -(kv[1]["reverts_made"] + kv[1]["reverts_received"]),
    )
    return [{"name": name, **stats} for name, stats in ranked[:roster_size]]


def build_dossier(all_revisions, article, live_start_date, live_end_date,
                   baseline_end_date=None, min_edits=5, roster_size=5,
                   matrix_size=10, war_window_size=5,
                   price_per_million_tokens=0.59, queries_per_day=50):
    baseline_end = baseline_end_date or live_start_date

    verdict, measurement = find_safe_edit_window(
        all_revisions, live_start_date, live_end_date,
        baseline_end_date=baseline_end_date, min_edits=min_edits,
    )

    # Re-walk the same two retrieval calls find_safe_edit_window made, so
    # the boss fight has a token count AFTER baseline alone and AFTER
    # baseline+live -- two real checkpoints, not fabricated stage names.
    baseline_raw = retrieve_raw_revisions(all_revisions, "0000-01-01", baseline_end)
    live_raw = retrieve_raw_revisions(all_revisions, live_start_date, live_end_date)

    baseline_tokens = count_tokens(json.dumps(baseline_raw))
    live_tokens = count_tokens(json.dumps(baseline_raw + live_raw))
    after_tokens = measurement["after_tokens"]

    stages = [
        {"name": "baseline_retrieved", "tokens_so_far": baseline_tokens},
        {"name": "live_retrieved", "tokens_so_far": live_tokens},
        {"name": "augmented", "tokens_so_far": after_tokens},
    ]

    full_agg = aggregate(all_revisions)
    # A self-revert (undoing your own edit) isn't a rivalry -- the VS
    # roster needs two distinct people, so exclude those pairs here.
    rivalries = [p for p in full_agg["revert_matrix"] if p["reverter"] != p["reverted"]]
    matrix_top = sorted(rivalries, key=lambda p: -p["count"])[:matrix_size]
    war_windows_top = sorted(
        full_agg["war_windows"], key=lambda w: -w["revert_count"]
    )[:war_window_size]

    return {
        "article": article,
        "live_start_date": live_start_date,
        "live_end_date": live_end_date,
        "before_tokens": live_tokens,
        "after_tokens": after_tokens,
        "compression_x": compression_factor(live_tokens, after_tokens),
        "stages": stages,
        "verdict": verdict,
        "cost_projection": project_cost(
            before_tokens=live_tokens, after_tokens=after_tokens,
            price_per_million_tokens=price_per_million_tokens,
            queries_per_day=queries_per_day,
        ),
        "safety_grid": build_safety_table(baseline_raw),
        "revert_roster": _roster(full_agg["per_editor"], roster_size),
        "revert_matrix": matrix_top,
        "war_windows": war_windows_top,
    }
