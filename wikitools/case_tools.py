"""The two tools exposed to the detective LLM, as pure/testable wrappers
around retrieve.py and ledger.py. No network, no LLM in this module --
engine.py's run_tools() dispatches to these.
"""
import json

from wikitools.augment import augment_safety_report
from wikitools.ledger import count_tokens, compression_factor, project_cost
from wikitools.retrieve import investigate_conflict

# From step0_validate.py's live sample (50 revisions, full wikitext,
# 2026 FIFA World Cup). Used to project the naive "dump full content"
# baseline for windows we don't fetch full content for.
AVG_TOKENS_PER_REVISION_WITH_CONTENT = 61_676


def investigate_and_measure(index, all_revisions, article, start_date, end_date, editor=None):
    """Run the retrieval tool AND measure it against both naive baselines
    in one call, so the ledger tool always has fresh numbers to report.
    """
    if not article or not start_date or not end_date:
        raise ValueError("article, start_date, and end_date are all required")

    in_range = [r for r in all_revisions
                if start_date <= r["timestamp"][:10] <= end_date]

    result = investigate_conflict(index, article, start_date, end_date, editor=editor)

    after_tokens = count_tokens(json.dumps(result))
    before_metadata_tokens = count_tokens(json.dumps(in_range))
    before_full_content_tokens = len(in_range) * AVG_TOKENS_PER_REVISION_WITH_CONTENT

    measurement = {
        "revisions_in_range": len(in_range),
        "after_tokens": after_tokens,
        "before_metadata_tokens": before_metadata_tokens,
        "before_full_content_tokens": before_full_content_tokens,
    }
    return result, measurement


def build_ledger_report(measurement, price_per_million_tokens=0.59, queries_per_day=50):
    """The detective's receipts. Requires a prior investigate_and_measure
    call's measurement dict -- there is nothing to report on otherwise.
    """
    if not measurement:
        raise ValueError("no investigation has run yet -- call investigate_conflict first")

    after = measurement["after_tokens"]
    full = measurement["before_full_content_tokens"]
    meta = measurement["before_metadata_tokens"]

    return {
        "after_tokens": after,
        "before_full_content_tokens": full,
        "before_metadata_tokens": meta,
        "compression_vs_full_content": compression_factor(full, after),
        "compression_vs_metadata": compression_factor(meta, after),
        "cost_projection": project_cost(
            before_tokens=meta,
            after_tokens=after,
            price_per_million_tokens=price_per_million_tokens,
            queries_per_day=queries_per_day,
        ),
    }


# --- retrieval / augment, kept as two visibly separate stages -------------
#
# retrieve_raw_revisions is RETRIEVAL: it hits the corpus (the cached
# stand-in for a live API call) and hands back exactly what's there for
# the requested range. No filtering-for-relevance, no aggregation, no
# dropped fields -- that would be augmentation's job, not retrieval's.
#
# augment_safety_report (wikitools/augment.py) is AUGMENT: it takes that
# raw payload and does the actual compression -- bucketing, rate
# computation, argmin -- so only a conclusion-ready verdict gets wired
# into the model's context. This is where the token savings live.

def retrieve_raw_revisions(all_revisions, start_date, end_date):
    """Retrieval: return raw revisions in range, unmodified. Stands in for
    an API call (see step1_chunk.py, which is where these were actually
    fetched from the MediaWiki API and cached to disk).
    """
    return [r for r in all_revisions if start_date <= r["timestamp"][:10] <= end_date]


def find_safe_edit_window(all_revisions, live_start_date, live_end_date,
                          baseline_end_date=None, min_edits=5):
    """The safe-edit-window problem statement, wired end to end:
      1. RETRIEVAL -- pull raw baseline history and raw live-period history.
      2. AUGMENT   -- compress both into a day/hour safety verdict.
      3. MEASURE   -- token-count the raw retrieval vs the augmented result,
                      so case_ledger has real receipts to report.
    """
    if not live_start_date or not live_end_date:
        raise ValueError("live_start_date and live_end_date are both required")

    baseline_end = baseline_end_date or live_start_date

    # RETRIEVAL -- raw, unaggregated, exactly what a naive tool call would return.
    baseline_raw = retrieve_raw_revisions(all_revisions, "0000-01-01", baseline_end)
    live_raw = retrieve_raw_revisions(all_revisions, live_start_date, live_end_date)

    # AUGMENT -- the compression happens here, not in retrieval.
    result = augment_safety_report(baseline_raw, live_raw, min_edits=min_edits)

    before_tokens = count_tokens(json.dumps(baseline_raw + live_raw))
    after_tokens = count_tokens(json.dumps(result))

    measurement = {
        "baseline_revisions_retrieved": len(baseline_raw),
        "live_revisions_retrieved": len(live_raw),
        "before_tokens": before_tokens,
        "after_tokens": after_tokens,
    }
    return result, measurement
