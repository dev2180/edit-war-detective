"""Step 0 — validate the case before building anything.

Pull revision metadata for the 2026 FIFA World Cup article, confirm:
  - sha1 and revert tags are present in the API response (needed for
    deterministic revert detection later)
  - the BEFORE token number (full wikitext) is genuinely huge
  - the metadata-only baseline is much smaller but still big

Run: python step0_validate.py
"""
import json

import requests
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")
ARTICLE = "2026 FIFA World Cup"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "EditWarDetective/0.1 (hackathon project; contact: dev.sra2180@gmail.com)"}


def count_tokens(text):
    return len(enc.encode(text))


def fetch_revisions_metadata(article, limit=500):
    """Metadata-only: ids, timestamp, user, comment, size, sha1, tags. No wikitext."""
    revisions = []
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": article,
        "rvprop": "ids|timestamp|user|comment|size|sha1|tags",
        "rvslots": "main",
        "rvlimit": 50,
        "format": "json",
        "formatversion": "2",
    }
    while len(revisions) < limit:
        r = requests.get(API, params=params, headers=HEADERS, timeout=30)
        data = r.json()
        pages = data["query"]["pages"]
        revisions.extend(pages[0].get("revisions", []))
        if "continue" not in data:
            break
        params.update(data["continue"])
    return revisions[:limit]


def fetch_revisions_with_content(article, limit=50):
    """Same as above but with full wikitext (rvprop includes content). Expensive."""
    revisions = []
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": article,
        "rvprop": "ids|timestamp|user|comment|size|sha1|tags|content",
        "rvslots": "main",
        "rvlimit": 50,
        "format": "json",
        "formatversion": "2",
    }
    while len(revisions) < limit:
        r = requests.get(API, params=params, headers=HEADERS, timeout=30)
        data = r.json()
        pages = data["query"]["pages"]
        revisions.extend(pages[0].get("revisions", []))
        if "continue" not in data or len(revisions) >= limit:
            break
        params.update(data["continue"])
    return revisions[:limit]


if __name__ == "__main__":
    print(f"Case file: {ARTICLE}")
    print("=" * 60)

    meta = fetch_revisions_metadata(ARTICLE, limit=500)
    print(f"\nFetched {len(meta)} revisions (metadata-only)")

    # sanity check: sha1 and tags present?
    sample = meta[0]
    print(f"Sample revision keys: {list(sample.keys())}")
    has_sha1 = all("sha1" in r for r in meta[:20])
    has_tags = any(r.get("tags") for r in meta[:100])
    print(f"sha1 present on all sampled: {has_sha1}")
    print(f"at least one tagged revision in first 100: {has_tags}")

    meta_payload = json.dumps(meta)
    meta_tokens = count_tokens(meta_payload)
    print(f"\nBASELINE (metadata-only, {len(meta)} revisions): {meta_tokens:,} tokens")

    # full content on a smaller sample (500 would be very slow/huge)
    content_sample = fetch_revisions_with_content(ARTICLE, limit=50)
    content_payload = json.dumps(content_sample)
    content_tokens = count_tokens(content_payload)
    avg_per_rev = content_tokens / len(content_sample)
    projected_500 = int(avg_per_rev * 500)

    print(f"\nFULL WIKITEXT sample ({len(content_sample)} revisions): {content_tokens:,} tokens")
    print(f"  avg tokens/revision (with content): {avg_per_rev:,.0f}")
    print(f"  PROJECTED for 500 revisions: {projected_500:,} tokens")
    print(f"\nBEFORE (naive, projected 500-rev full content): {projected_500:,} tokens")
    print(f"BEFORE (honest secondary baseline, metadata-only 500): {meta_tokens:,} tokens")
