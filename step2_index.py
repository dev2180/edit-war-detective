"""Step 2 — Build index.json from the chunks written in step1.

Run: python step2_index.py
"""
import json

from wikitools.chunking import chunk_by_month
from wikitools.indexing import build_index
from wikitools.reverts import detect_reverts

ARTICLE = "2026 FIFA World Cup"

if __name__ == "__main__":
    revisions = json.load(open("casefiles/_all_revisions_raw.json"))
    revisions = detect_reverts(revisions)
    chunks = chunk_by_month(revisions)

    index = build_index(ARTICLE, chunks, chunk_dir="casefiles")
    json.dump(index, open("casefiles/index.json", "w"), indent=2)

    print(f"wrote casefiles/index.json with {len(index)} chunk entries")
    index_tokens_estimate = len(json.dumps(index))
    print(f"index.json size: {index_tokens_estimate:,} chars")

    busiest = sorted(index, key=lambda e: e["revert_count"], reverse=True)[:5]
    print("\nMost contentious months (by revert count):")
    for entry in busiest:
        print(f"  {entry['month']}: {entry['revert_count']} reverts, "
              f"{entry['revision_count']} revisions, editors={entry['editors'][:5]}")
