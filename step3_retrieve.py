"""Step 3 -- Retrieval, in isolation.

Demonstrates the R in R->A->G: pull raw revisions for a date window with
zero compression -- no bucketing, no aggregation, no dropped fields. This
is the "naive tool call" a non-optimized agent would send straight to the
LLM. Step 4 takes this exact output and augments it.

Run: python step3_retrieve.py
"""
import json

from wikitools.case_tools import retrieve_raw_revisions
from wikitools.ledger import count_tokens

ARTICLE = "2026 FIFA World Cup"
BASELINE_END = "2026-06-01"
LIVE_START, LIVE_END = "2026-06-01", "2026-07-20"

if __name__ == "__main__":
    all_revisions = json.load(open("casefiles/_all_revisions_raw.json"))

    baseline_raw = retrieve_raw_revisions(all_revisions, "0000-01-01", BASELINE_END)
    live_raw = retrieve_raw_revisions(all_revisions, LIVE_START, LIVE_END)

    baseline_tokens = count_tokens(json.dumps(baseline_raw))
    live_tokens = count_tokens(json.dumps(live_raw))

    print(f"Case: {ARTICLE}")
    print(f"Baseline window: earliest revision -> {BASELINE_END}")
    print(f"  revisions retrieved: {len(baseline_raw):,}")
    print(f"  raw tokens         : {baseline_tokens:,}")
    print(f"Live window: {LIVE_START} -> {LIVE_END}")
    print(f"  revisions retrieved: {len(live_raw):,}")
    print(f"  raw tokens         : {live_tokens:,}")
    print()
    print(f"Total raw tokens retrieved (this IS the BEFORE number): {baseline_tokens + live_tokens:,}")
    print("No aggregation happened above -- that's step 4.")

    json.dump(baseline_raw, open("casefiles/_step3_baseline_raw.json", "w"))
    json.dump(live_raw, open("casefiles/_step3_live_raw.json", "w"))
    print("\nWrote casefiles/_step3_baseline_raw.json and _step3_live_raw.json")
