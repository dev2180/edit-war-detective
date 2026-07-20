"""Step 1 — Chunking is a for loop, applied to a real case file.

Fetch the FULL revision history (metadata only: no wikitext) for the
2026 FIFA World Cup article, run deterministic revert detection, chunk by
calendar month, and write one JSON file per month to casefiles/.

Run: python step1_chunk.py
"""
import json
import time

import requests

from wikitools.chunking import chunk_by_month
from wikitools.indexing import write_chunks
from wikitools.reverts import detect_reverts

ARTICLE = "2026 FIFA World Cup"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "EditWarDetective/0.1 (hackathon project; contact: dev.sra2180@gmail.com)"}


def fetch_all_revisions(article):
    """All revisions, oldest first (rvdir=newer), metadata only."""
    revisions = []
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": article,
        "rvprop": "ids|timestamp|user|comment|size|sha1|tags",
        "rvslots": "main",
        "rvlimit": 500,
        "rvdir": "newer",
        "format": "json",
        "formatversion": "2",
    }
    while True:
        r = requests.get(API, params=params, headers=HEADERS, timeout=30)
        data = r.json()
        pages = data["query"]["pages"]
        batch = pages[0].get("revisions", [])
        revisions.extend(batch)
        print(f"  fetched {len(revisions)} revisions so far...")
        if "continue" not in data:
            break
        params.update(data["continue"])
        time.sleep(0.2)  # be polite to the free API
    return revisions


if __name__ == "__main__":
    print(f"Fetching full revision history: {ARTICLE}")
    revisions = fetch_all_revisions(ARTICLE)
    print(f"\nTotal revisions: {len(revisions)}")

    print("Running deterministic revert detection...")
    revisions = detect_reverts(revisions)
    revert_count = sum(1 for r in revisions if r["is_revert"])
    print(f"Reverts detected: {revert_count} ({revert_count / len(revisions):.1%})")

    print("Chunking by month...")
    chunks = chunk_by_month(revisions)
    print(f"Months spanned: {len(chunks)} ({min(chunks)} to {max(chunks)})")

    write_chunks(ARTICLE, chunks, chunk_dir="casefiles")
    print(f"Wrote {len(chunks)} chunk files to casefiles/")

    # stash the full revision list too, for step0's honest BEFORE baseline
    json.dump(revisions, open("casefiles/_all_revisions_raw.json", "w"))
