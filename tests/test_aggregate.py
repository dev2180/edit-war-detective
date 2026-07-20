"""Deterministic pre-aggregation: the biggest token saving in the pipeline.
Raw revisions in, a conclusion-ready case brief out. Pure functions,
fixture-driven, no network, no LLM.
"""
from wikitools.aggregate import aggregate, filter_combatants


def rev(revid, timestamp, user, size, is_revert=False, reverted_editor=None, comment=""):
    return {
        "revid": revid, "timestamp": timestamp, "user": user, "size": size,
        "is_revert": is_revert, "reverted_editor": reverted_editor,
        "comment": comment, "sha1": str(revid), "tags": [],
    }


def test_per_editor_edit_counts():
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-01T01:00:00Z", "Bob", 120),
        rev(3, "2024-01-01T02:00:00Z", "Alice", 90),
    ]
    result = aggregate(revs)
    assert result["per_editor"]["Alice"]["edits"] == 2
    assert result["per_editor"]["Bob"]["edits"] == 1


def test_per_editor_reverts_made_and_received():
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-01T01:00:00Z", "Bob", 120, is_revert=True, reverted_editor="Alice"),
    ]
    result = aggregate(revs)
    assert result["per_editor"]["Bob"]["reverts_made"] == 1
    assert result["per_editor"]["Alice"]["reverts_received"] == 1


def test_net_bytes_is_last_size_minus_first_size_per_editor():
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-01T01:00:00Z", "Alice", 150),
    ]
    result = aggregate(revs)
    # Alice's contributions: sum of bytes_delta across her edits.
    # rev1 delta = 100 (from 0), rev2 delta = 50 (150-100) -> net 150
    assert result["per_editor"]["Alice"]["net_bytes"] == 150


def test_revert_matrix_counts_who_reverts_whom():
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-01T01:00:00Z", "Bob", 120, is_revert=True, reverted_editor="Alice"),
        rev(3, "2024-01-01T02:00:00Z", "Bob", 130, is_revert=True, reverted_editor="Alice"),
    ]
    result = aggregate(revs)
    assert result["revert_matrix"] == [{"reverter": "Bob", "reverted": "Alice", "count": 2}]


def test_revert_matrix_ignores_non_reverts():
    revs = [rev(1, "2024-01-01T00:00:00Z", "Alice", 100)]
    result = aggregate(revs)
    assert result["revert_matrix"] == []


def test_weekly_churn_sums_absolute_byte_deltas_by_iso_week():
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),   # delta 100 (from 0)
        rev(2, "2024-01-02T00:00:00Z", "Bob", 50),       # delta -50
    ]
    result = aggregate(revs)
    week_key = "2024-W01"
    assert result["weekly_churn"][week_key] == 150


def test_war_window_flags_burst_of_reverts_within_24h():
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-01T01:00:00Z", "Bob", 100, is_revert=True, reverted_editor="Alice"),
        rev(3, "2024-01-01T05:00:00Z", "Alice", 100, is_revert=True, reverted_editor="Bob"),
        rev(4, "2024-01-01T10:00:00Z", "Bob", 100, is_revert=True, reverted_editor="Alice"),
    ]
    result = aggregate(revs, war_window_threshold=3)
    assert len(result["war_windows"]) == 1
    window = result["war_windows"][0]
    assert window["revert_count"] == 3


def test_no_war_window_when_reverts_are_sparse():
    revs = [
        rev(1, "2024-01-01T00:00:00Z", "Alice", 100),
        rev(2, "2024-01-05T00:00:00Z", "Bob", 100, is_revert=True, reverted_editor="Alice"),
    ]
    result = aggregate(revs, war_window_threshold=3)
    assert result["war_windows"] == []


def test_sample_comments_limited_to_five_from_reverts():
    revs = [rev(i, f"2024-01-0{i}T00:00:00Z", "Bob", 100, is_revert=True,
                reverted_editor="Alice", comment=f"rv edit {i}")
            for i in range(1, 8)]
    result = aggregate(revs)
    assert len(result["sample_comments"]) == 5


def test_empty_revisions_returns_empty_shell():
    result = aggregate([])
    assert result["per_editor"] == {}
    assert result["revert_matrix"] == []
    assert result["weekly_churn"] == {}
    assert result["war_windows"] == []
    assert result["sample_comments"] == []


def test_filter_combatants_drops_editors_with_no_revert_involvement():
    per_editor = {
        "Alice": {"edits": 5, "reverts_made": 2, "reverts_received": 0, "net_bytes": 100},
        "Bob": {"edits": 1, "reverts_made": 0, "reverts_received": 0, "net_bytes": 10},
        "Carol": {"edits": 3, "reverts_made": 0, "reverts_received": 1, "net_bytes": 20},
    }
    result = filter_combatants(per_editor)
    assert set(result.keys()) == {"Alice", "Carol"}


def test_filter_combatants_keeps_top_n_by_edits_even_without_reverts():
    per_editor = {
        "Prolific": {"edits": 50, "reverts_made": 0, "reverts_received": 0, "net_bytes": 100},
        "OneOff": {"edits": 1, "reverts_made": 0, "reverts_received": 0, "net_bytes": 10},
    }
    result = filter_combatants(per_editor, top_n_bystanders=1)
    assert "Prolific" in result
    assert "OneOff" not in result


def test_filter_combatants_on_empty_dict():
    assert filter_combatants({}) == {}
