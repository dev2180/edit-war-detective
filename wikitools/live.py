"""Wrappers for the frontend's live /api endpoints.

ask_detective  -- runs a query through the detective agent, with an
                  in-character fallback if Groq errors (rate limit, bad
                  request, etc.) instead of surfacing a raw stack trace.
recount        -- re-derives the BEFORE token number from the cached
                  corpus independently, so the frontend's RECOUNT button
                  proves the number rather than repeating it.
"""
import json

import groq

from wikitools.case_tools import retrieve_raw_revisions
from wikitools.ledger import count_tokens

_FALLBACK_LINE = (
    "\"Whoa, slow down, kid. That question's got more history in it than "
    "my case file can hold in one sitting. Ask me something narrower -- "
    "a date range, a name -- and I'll get you the real answer.\""
)


def ask_detective(query, investigate_fn):
    try:
        answer = investigate_fn(query)
        return {"detective_says": answer, "mode": "live"}
    except groq.GroqError:
        return {"detective_says": _FALLBACK_LINE, "mode": "error"}
    except Exception:
        return {"detective_says": _FALLBACK_LINE, "mode": "error"}


def recount(all_revisions, live_start_date, live_end_date, baseline_end_date=None):
    baseline_end = baseline_end_date or live_start_date
    baseline_raw = retrieve_raw_revisions(all_revisions, "0000-01-01", baseline_end)
    live_raw = retrieve_raw_revisions(all_revisions, live_start_date, live_end_date)
    tokens = count_tokens(json.dumps(baseline_raw + live_raw))
    return {"tokens": tokens, "tokenizer": "cl100k_base"}
