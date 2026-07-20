"""Live-query wrappers for the frontend's /api endpoints: ask_detective
(wraps engine.investigate with an in-character fallback on Groq errors)
and recount (re-derives the BEFORE token number from the cached corpus,
independent of whatever the baked dossier already claims). Fixture-driven,
no real network -- ask_detective takes an injected investigate_fn so tests
never touch Groq.
"""
import groq
import pytest

from wikitools.live import ask_detective, recount


def test_ask_detective_returns_live_mode_on_success():
    result = ask_detective("when's it safe?", investigate_fn=lambda q: "Thursday, 8am. Case closed.")
    assert result["mode"] == "live"
    assert result["detective_says"] == "Thursday, 8am. Case closed."


def test_ask_detective_falls_back_in_character_on_groq_error():
    def boom(q):
        raise groq.RateLimitError("too many tokens", response=None, body=None)

    result = ask_detective("tell me everything ever", investigate_fn=boom)
    assert result["mode"] == "error"
    assert "detective_says" in result and result["detective_says"]


def test_ask_detective_falls_back_on_any_unexpected_exception():
    def boom(q):
        raise ValueError("something else broke")

    result = ask_detective("anything", investigate_fn=boom)
    assert result["mode"] == "error"
    assert result["detective_says"]


def rev(revid, timestamp, user="A", size=100, is_revert=False):
    return {"revid": revid, "timestamp": timestamp, "user": user, "size": size,
            "is_revert": is_revert, "reverted_editor": None, "comment": "",
            "sha1": str(revid), "tags": []}


def test_recount_returns_tokens_and_tokenizer_name():
    all_revisions = [
        rev(1, "2024-01-01T00:00:00Z"),
        rev(2, "2026-06-05T00:00:00Z"),
    ]
    result = recount(all_revisions, live_start_date="2026-06-01", live_end_date="2026-07-20")
    assert result["tokenizer"] == "cl100k_base"
    assert result["tokens"] > 0


def test_recount_matches_manual_token_count():
    from wikitools.case_tools import retrieve_raw_revisions
    from wikitools.ledger import count_tokens
    import json

    all_revisions = [
        rev(1, "2024-01-01T00:00:00Z"),
        rev(2, "2026-06-05T00:00:00Z"),
    ]
    result = recount(all_revisions, live_start_date="2026-06-01", live_end_date="2026-07-20")

    baseline = retrieve_raw_revisions(all_revisions, "0000-01-01", "2026-06-01")
    live = retrieve_raw_revisions(all_revisions, "2026-06-01", "2026-07-20")
    expected = count_tokens(json.dumps(baseline + live))
    assert result["tokens"] == expected
