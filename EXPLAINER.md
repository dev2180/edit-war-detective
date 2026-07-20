# The Edit-War Detective — How and Why

## The problem statement

**100xEngineers — Token Optimization Hackathon (24 hours).** Take a tool-calling
LLM app, measure what its tool outputs cost in tokens today (BEFORE), apply the
module 1 RAG pipeline — chunk, index, metadata filter, pre-aggregate, augment,
generate — using **keyword search only** (no embeddings, no vector DB), and
report the AFTER number and the reduction factor. The optimization must clear
a volume bar: if nobody queries this daily or across multiple users, don't
bother — say so and pick something else instead.

Two tracks were offered:
- **Track A** — bring your own tool-calling app.
- **Track B** — start from Aarav's Workflow Diagnoser (a two-tool Groq agent:
  `search_web` via Tavily, `estimate_time_saved`) and crank the noise up.

We chose **Track A**, building from scratch rather than modifying Aarav's repo.

## What we studied first

Two reference materials, read in full before writing any code:

1. **`module1_weather` (WeatherRAG)** — the course's own worked example.
   Ten years of hourly Bengaluru weather, a wedding query that dies at
   128K tokens, then five steps that fix it: chunk by year, index by
   metadata, filter + pre-aggregate into daily summaries, wire it into a
   Groq tool-calling loop, measure the win. Result: 600K → ~12K tokens,
   **~200x**, entirely from a filter and a `defaultdict`. The comments in
   its `step4_toolcall.py` literally label three lines `# retrieval`,
   `# augmentation`, `# generation` — that three-line shape became our
   template for `engine.py`.

2. **`diagnoser.py` (Aarav's Workflow Diagnoser, Track B reference)** — the
   plain agent-loop pattern: system prompt, two tool schemas, a `while True`
   loop that keeps calling tools until the model stops and answers. We copied
   this loop shape exactly rather than inventing our own.

## What we originally proposed (and what changed)

We ran the **ADHD skill** (parallel divergent ideation across cognitive
frames) twice during this project — once to pick the Track A idea, once to
pick the exact query.

**Round 1 — picking the app.** 30 candidates across 5 frames (logistics,
speedrunner, attacker, biology, 1-hour-budget). Shortlist: a GitHub Actions
CI-log triage bot, an npm/PyPI dependency auditor, and a Wikipedia edit-war
referee. We picked **the edit-war referee**, gamed up with a noir-detective
theme per your direction, and set it on the **2026 FIFA World Cup** article —
live, contentious, and topical during an actual tournament.

**Round 2 — picking the query.** Early on, our "representative query" was too
broad: *"how bad was the edit war during the tournament?"* over a full
2-month window. That's a fine demo, but it isn't the wedding query's shape —
it doesn't force a *personal, scheduling* decision the way "which weekend is
safe for the wedding" does. We ran ADHD again, this time explicitly hunting
for the wedding-query's structural twin, and landed on:

> *"I'm a new editor who wants to add the final match result without
> getting reverted. Based on the full history, when's the safest time to
> edit — and is that window still safe during the tournament?"*

This is deliberately the safety-inverse of "who fought the hardest" — same
shape as "which weekend is least likely to rain," just for edit wars instead
of weather.

**Architecture correction, mid-build.** Initially the "retrieval" tool did
filtering *and* aggregation in one function (mirroring `get_weather_history`
in the reference, which does the same thing). You pointed out that retrieval,
augment, and generate are three distinct steps and that augmentation is
usually where compression happens — so we split it explicitly:

- `retrieve_raw_revisions()` — pulls raw revisions for a date range, unmodified,
  no filtering-for-relevance. This is Retrieval, and it's what we measure for
  BEFORE.
- `augment_safety_report()` — bucket by day-of-week × hour, compute revert
  rates, find the historically safest bucket, check whether it's still safe
  live. This is where the actual compression happens, and it's what we
  measure for AFTER.
- `engine.py`'s loop appends the *already-compressed* augment output into the
  conversation — augmentation-as-plumbing, not augmentation-as-compression,
  matching how the reference module also does it (`get_weather_history`
  compresses; the loop just appends the result).

## Our estimate, before running anything

Following the "predict before you run" rule: we expected

- Full revision history for a 14-year-old, high-traffic article to run into
  the **thousands** of revisions, with reverts concentrated around the live
  tournament (June–July 2026).
- A naive tool call returning full wikitext per revision to be **enormous** —
  we projected north of 30 million tokens for a 500-revision sample, based on
  a real 50-revision sample averaging ~61,676 tokens/revision (this article's
  infoboxes and stats tables are dense).
- The compressed safety verdict to land under a few hundred tokens, since it's
  a handful of numbers (one bucket, two rates, one boolean).
- Compression in the **thousands-to-tens-of-thousands-x** range against the
  full-content baseline, and a more modest (but still real) multiple against
  a metadata-only baseline, since metadata itself is already fairly lean.

## What we actually found

Validation (`step0_validate.py`) confirmed the shape of the bet:

- **9,224 revisions**, spanning **2012 to 2026-07** (165 months of history).
- **1,576 reverts (17.1%)** overall.
- The two hottest months by far: **2026-06 (84 reverts) and 2026-07 (77
  reverts)** — the live tournament, exactly as predicted.

Running the actual pipeline on the real problem statement
(`find_safe_edit_window`, live period 2026-06-01 to 2026-07-20):

| | Tokens |
|---|---|
| BEFORE (raw revisions retrieved: 7,532 baseline + 1,701 live) | **1,193,518** |
| AFTER (the safety verdict) | **61** |
| **Compression** | **~19,566x** |

Verdict returned: *"Thursday at 08:00 is the historically safest time to
edit (4.35% revert rate, 23 samples), and it's still safe during the
tournament (0 reverts in 7 samples)."*

One honest caveat we're keeping in the writeup rather than hiding: 23
baseline samples for the winning bucket is a thin evidential base for a
confident claim, spread across 14 years of history. The pipeline is correct;
the underlying data for this one specific hour-bucket is sparse. A real
deployment would want a larger `min_edits` threshold or a coarser bucket
(e.g. day-of-week only) before shipping the claim as advice.

A live run against Groq also surfaced an unplanned but useful data point: our
secondary tool (`investigate_conflict`, the full edit-war case brief) for the
same 2-month window produces an ~11,000-token brief — which is itself *too
big* for Groq's free-tier rate limit (413, "Request too large," 12,000 TPM).
That's a real demonstration that compression isn't a one-time checkbox; even
a 95%+ reduction can still be too large for a constrained deployment tier,
which is why the narrower, single-purpose safety query is the better default
tool, not just the more dramatic one.

## How we built it — process

1. **Studied both reference repos in full** before writing code (see above).
2. **TDD throughout, no exceptions.** Every pipeline stage — revert detection,
   chunking, indexing, aggregation, retrieval, ledger math, the augment
   stage — was written test-first: red, then green, one module at a time.
   59 tests, all passing, zero network calls in the test suite (fixtures
   only; the one live-data script is separate and explicitly not part of
   `pytest`).
3. **Validated against the real API before building anything else**
   (`step0_validate.py`) — confirmed sha1/revert tags exist in the MediaWiki
   response, got a real token baseline, and only then started writing the
   pipeline.
4. **Pulled the full case file once, cached to disk** (`step1_chunk.py`,
   `step2_index.py`) — 9,224 revisions fetched once via the MediaWiki API,
   chunked by month, written to `casefiles/`, indexed into `index.json`. Every
   subsequent run reads from disk — no repeated API calls, which also keeps
   token/compute cost of *building* the demo near zero.
5. **A real bug caught by real data, not by a test:** the first version of
   the case brief for a genuinely busy window listed all 506 editors who ever
   touched the article in that period, including 244 who made exactly one
   edit and were never part of any revert. That's noise the question didn't
   ask for. We added `filter_combatants()` (TDD'd) to drop bystanders from
   the brief — the same "pre-aggregate to what the question needs" principle
   the reference module teaches with hourly-to-daily weather collapse, just
   applied to editors instead of readings.
6. **Wired the persona entirely into the system prompt**, not into the
   pipeline. `wikitools/` has no idea it's talking to a noir detective — the
   retrieval/augment/generate mechanics are persona-agnostic, which is what
   lets the frontend (90s-arcade, detective-noir, Contra-style — built next,
   with your sign-off, via another ADHD round) sit on top without touching
   any of the tested backend code.
