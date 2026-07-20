"""Step 5 — Prove it: measure the win on the real case file.

Two reports, back to back:

1. investigate_conflict() -- the case-brief tool. Two BEFORE baselines,
   reported honestly:
     naive_full_content  -- what a tool naively returning full wikitext
                             per revision would send (projected from a
                             sampled avg tokens/revision, since fetching
                             full content for thousands of revisions is
                             impractical)
     naive_metadata_only -- the fairer baseline: what a tool returning
                             just revision metadata (no content) would send

2. find_safe_edit_window() -- the primary tool (steps 3+4 wired end to
   end). This is where the headline compression number comes from.

Run: python step5_prove_it.py
"""
import json

from wikitools.case_tools import find_safe_edit_window
from wikitools.ledger import count_tokens, compression_factor, project_cost
from wikitools.retrieve import investigate_conflict

ARTICLE = "2026 FIFA World Cup"
QUERY_START, QUERY_END = "2026-06-01", "2026-07-20"

# from step0_validate.py's live sample (50 revisions, full wikitext)
AVG_TOKENS_PER_REVISION_WITH_CONTENT = 61_676


def measure():
    index = json.load(open("casefiles/index.json"))
    all_revisions = json.load(open("casefiles/_all_revisions_raw.json"))

    in_range = [r for r in all_revisions
                if QUERY_START <= r["timestamp"][:10] <= QUERY_END]

    naive_full_content = len(in_range) * AVG_TOKENS_PER_REVISION_WITH_CONTENT
    naive_metadata_only = count_tokens(json.dumps(in_range))

    result = investigate_conflict(index, ARTICLE, QUERY_START, QUERY_END)
    after_tokens = count_tokens(json.dumps(result))

    return {
        "revisions_in_range": len(in_range),
        "naive_full_content_tokens": naive_full_content,
        "naive_metadata_only_tokens": naive_metadata_only,
        "after_tokens": after_tokens,
        "result": result,
    }


if __name__ == "__main__":
    m = measure()

    print(f"Case: {ARTICLE}  |  Query window: {QUERY_START} to {QUERY_END}")
    print(f"Revisions in range: {m['revisions_in_range']:,}")
    print()
    print(f"BEFORE (naive, full wikitext per revision, projected): {m['naive_full_content_tokens']:>12,} tokens")
    print(f"BEFORE (honest secondary, metadata-only)             : {m['naive_metadata_only_tokens']:>12,} tokens")
    print(f"AFTER  (investigate_conflict case brief)              : {m['after_tokens']:>12,} tokens")
    print()

    cx_full = compression_factor(m["naive_full_content_tokens"], m["after_tokens"])
    cx_meta = compression_factor(m["naive_metadata_only_tokens"], m["after_tokens"])
    print(f"Compression vs full-content baseline : {cx_full:,.0f}x")
    print(f"Compression vs metadata-only baseline: {cx_meta:,.0f}x  (the fair, conservative number)")
    print()

    # cost projection: Wikipedia's edit-warring noticeboard gets checked by
    # patrollers/admins many times a day on active disputes -- 50 queries/day
    # is a conservative estimate for a hot article during a live tournament.
    projection = project_cost(
        before_tokens=m["naive_metadata_only_tokens"],
        after_tokens=m["after_tokens"],
        price_per_million_tokens=0.59,  # llama-3.3-70b-versatile on Groq, input price
        queries_per_day=50,
    )
    print(f"Cost projection @ 50 queries/day, $0.59/M input tokens (conservative baseline):")
    print(f"  BEFORE: ${projection['before']['daily_cost']:.4f}/day  "
          f"${projection['before']['monthly_cost']:.2f}/mo  ${projection['before']['yearly_cost']:.2f}/yr")
    print(f"  AFTER : ${projection['after']['daily_cost']:.4f}/day  "
          f"${projection['after']['monthly_cost']:.2f}/mo  ${projection['after']['yearly_cost']:.2f}/yr")
    print(f"  SAVED : ${projection['savings']['yearly_cost']:.2f}/yr")
    print(f"  Clears volume bar: {projection['clears_volume_bar']}")

    with open("casefiles/case_brief_2026-06_2026-07.json", "w") as f:
        json.dump(m["result"], f, indent=2)
    print("\nFull case brief written to casefiles/case_brief_2026-06_2026-07.json")

    print()
    print("=" * 60)
    print("PRIMARY TOOL: find_safe_edit_window (steps 3+4 wired end to end)")
    print("=" * 60)

    all_revisions = json.load(open("casefiles/_all_revisions_raw.json"))
    verdict, headline = find_safe_edit_window(
        all_revisions, live_start_date=QUERY_START, live_end_date=QUERY_END)

    print(f"Verdict: {json.dumps(verdict, indent=2)}")
    print()
    print(f"BEFORE (raw retrieval, baseline + live): {headline['before_tokens']:>12,} tokens")
    print(f"AFTER  (augmented verdict)              : {headline['after_tokens']:>12,} tokens")
    headline_cx = compression_factor(headline["before_tokens"], headline["after_tokens"])
    print(f"Compression (the headline number)       : {headline_cx:,.0f}x")
