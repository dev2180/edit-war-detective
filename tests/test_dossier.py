"""build_dossier: assembles every field the frontend needs (story mode boss
fight, detective-mode desk) from cached data in one pure call. No network,
no LLM -- this is glue over already-tested wikitools functions, tested here
for its own assembly logic (stage token math, roster/matrix trimming, grid
shape) rather than re-testing the underlying pipeline.
"""
from wikitools.dossier import build_dossier


def rev(revid, timestamp, user, size, is_revert=False, reverted_editor=None, comment=""):
    return {"revid": revid, "timestamp": timestamp, "user": user, "size": size,
            "is_revert": is_revert, "reverted_editor": reverted_editor,
            "comment": comment, "sha1": str(revid), "tags": []}


_TUESDAYS = ["2024-01-02", "2024-01-09", "2024-01-16", "2024-01-23", "2024-01-30", "2024-02-06"]


def make_history():
    # Baseline: Tue-10 is safe (6 clean edits by Alice). A Mon-04 war
    # between Alice and Bob (Bob reverts Alice 3x) also lives in baseline
    # so it shows up in the roster/matrix/war-windows.
    baseline = [rev(i, f"{d}T10:00:00Z", "Alice", 100) for i, d in enumerate(_TUESDAYS)]
    baseline += [
        rev(100, "2025-01-06T04:00:00Z", "Alice", 200),
        rev(101, "2025-01-06T04:00:00Z", "Bob", 150, is_revert=True, reverted_editor="Alice"),
        rev(102, "2025-01-06T04:00:00Z", "Alice", 200, is_revert=True, reverted_editor="Bob"),
        rev(103, "2025-01-06T04:00:00Z", "Bob", 150, is_revert=True, reverted_editor="Alice"),
    ]
    live = [rev(200, "2026-06-02T10:00:00Z", "Carol", 300)]  # Tue-10 during live window, still safe
    return baseline + live


def test_build_dossier_returns_verdict_and_token_stages():
    history = make_history()
    dossier = build_dossier(
        history, article="Test Article",
        live_start_date="2026-06-01", live_end_date="2026-07-20", min_edits=5,
    )

    assert dossier["article"] == "Test Article"
    assert dossier["verdict"]["safest_baseline_window"] == "Tue-10"
    assert dossier["verdict"]["still_safe"] is True

    stage_names = [s["name"] for s in dossier["stages"]]
    assert stage_names == ["baseline_retrieved", "live_retrieved", "augmented"]
    # tokens must strictly decrease -- retrieval-only stages, then the drop
    baseline_t, live_t, augmented_t = (s["tokens_so_far"] for s in dossier["stages"])
    assert baseline_t <= live_t
    assert live_t > augmented_t
    assert dossier["after_tokens"] == augmented_t
    assert dossier["before_tokens"] == live_t


def test_build_dossier_compression_x_matches_before_after():
    history = make_history()
    dossier = build_dossier(history, article="Test Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20")
    assert dossier["compression_x"] == dossier["before_tokens"] / dossier["after_tokens"]


def test_build_dossier_roster_only_has_combatants_sorted_by_involvement():
    history = make_history()
    dossier = build_dossier(history, article="Test Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20")

    roster_names = [entry["name"] for entry in dossier["revert_roster"]]
    assert roster_names[0] in {"Alice", "Bob"}  # the two combatants lead
    assert "Carol" not in roster_names  # Carol never reverted or was reverted
    for entry in dossier["revert_roster"]:
        assert "reverts_made" in entry and "reverts_received" in entry


def test_build_dossier_roster_respects_size_limit():
    history = make_history()
    dossier = build_dossier(history, article="Test Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20",
                             roster_size=1)
    assert len(dossier["revert_roster"]) == 1


def test_build_dossier_revert_matrix_and_war_windows_present():
    history = make_history()
    dossier = build_dossier(history, article="Test Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20")

    assert dossier["revert_matrix"][0] == {"reverter": "Bob", "reverted": "Alice", "count": 2}
    assert {"reverter": "Alice", "reverted": "Bob", "count": 1} in dossier["revert_matrix"]
    assert len(dossier["war_windows"]) == 1


def test_build_dossier_revert_matrix_excludes_self_reverts():
    # Someone undoing their own edit isn't a rivalry -- the VS-roster
    # screen needs two distinct people, so self-reverts don't belong here.
    history = make_history()
    history += [
        rev(300, "2025-03-01T00:00:00Z", "Dave", 50),
        rev(301, "2025-03-01T01:00:00Z", "Dave", 40, is_revert=True, reverted_editor="Dave"),
    ]
    dossier = build_dossier(history, article="Test Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20")
    for pair in dossier["revert_matrix"]:
        assert pair["reverter"] != pair["reverted"]
    assert dossier["war_windows"][0]["revert_count"] == 3


def test_build_dossier_safety_grid_includes_buckets_below_min_edits():
    # Mon-04 only has 4 edits total -- below min_edits=5 -- so it can't win
    # the verdict, but the heatmap still needs it plotted.
    history = make_history()
    dossier = build_dossier(history, article="Test Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20",
                             min_edits=5)
    assert "Mon-04" in dossier["safety_grid"]
    assert dossier["safety_grid"]["Mon-04"]["edits"] == 4


def test_build_dossier_cost_projection_present():
    history = make_history()
    dossier = build_dossier(history, article="Test Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20",
                             price_per_million_tokens=0.59, queries_per_day=50)
    assert dossier["cost_projection"]["clears_volume_bar"] is True
    assert "savings" in dossier["cost_projection"]


def test_build_dossier_on_empty_history_does_not_crash():
    dossier = build_dossier([], article="Empty Article",
                             live_start_date="2026-06-01", live_end_date="2026-07-20")
    assert dossier["verdict"]["safest_baseline_window"] is None
    assert dossier["revert_roster"] == []
    assert dossier["revert_matrix"] == []
    assert dossier["war_windows"] == []
    assert dossier["safety_grid"] == {}
