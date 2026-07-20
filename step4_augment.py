"""Step 4 -- Augment, in isolation. This is where the compression happens.

Takes step 3's raw retrieval output (untouched revisions) and runs
augment_safety_report: bucket by day-of-week + hour, compute revert rates,
find the historically safest bucket, check it's still safe live. No
revision text survives past this stage -- only a one-bucket verdict does.

Run: python step3_retrieve.py   (writes the inputs this script reads)
     python step4_augment.py
"""
import json

from wikitools.augment import augment_safety_report
from wikitools.ledger import count_tokens, compression_factor

if __name__ == "__main__":
    baseline_raw = json.load(open("casefiles/_step3_baseline_raw.json"))
    live_raw = json.load(open("casefiles/_step3_live_raw.json"))

    before_tokens = count_tokens(json.dumps(baseline_raw + live_raw))

    result = augment_safety_report(baseline_raw, live_raw, min_edits=5)
    after_tokens = count_tokens(json.dumps(result))

    print("AUGMENT stage output (the verdict, nothing else):")
    print(json.dumps(result, indent=2))
    print()
    print(f"BEFORE (raw retrieval from step 3): {before_tokens:,} tokens")
    print(f"AFTER  (augmented verdict)        : {after_tokens:,} tokens")
    print(f"Compression                       : {compression_factor(before_tokens, after_tokens):,.0f}x")

    json.dump(result, open("casefiles/_step4_augmented_verdict.json", "w"), indent=2)
    print("\nWrote casefiles/_step4_augmented_verdict.json")
