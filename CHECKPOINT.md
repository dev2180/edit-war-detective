# Session checkpoint (for context restore)

## State: backend DONE, shipped. Frontend NOT started.

- Repo: https://github.com/dev2180/edit-war-detective (public, pushed, master)
- Local: C:\Users\devsr\OneDrive\Desktop\Claude\edit-war-detective
- 59/59 tests green (`python -m pytest -q`). TDD throughout — keep it that way.
- .env has real GROQ_API_KEY (gitignored). .env.example committed.
- Headline: 1,193,518 -> 61 tokens = ~19,566x on find_safe_edit_window
  ("Thu-08" verdict, live-tested via engine.py on llama-3.3-70b-versatile).
- Docs: EXPLAINER.md (process), SUBMISSION.md (deliverables), README.md.

## Key architecture facts
- engine.py = Aarav diagnoser.py-shaped loop; Detective Marlowe persona in
  SYSTEM_PROMPT only; three tools: find_safe_edit_window (primary, the
  "wedding query" analog), investigate_conflict (case brief), case_ledger
  (token receipts, narrated in character).
- R/A/G split explicit per user request: retrieve_raw_revisions (raw, no
  compression) -> augment_safety_report in wikitools/augment.py (day-of-week
  x hour buckets, revert rates, argmin, still-safe check = ALL compression)
  -> generate.
- Known caveats (disclosed in docs): Thu-08 bucket only 23 samples; 11K-token
  full-window conflict brief trips Groq free-tier 12K TPM (413) — narrow
  queries work.

## Frontend plan (NEXT, needs user's go)
- Theme: 90s arcade / Contra-style 8-bit, noir detective who narrates
  findings via text; dramatic "OLD FACTS vs NEW FACTS" reveal of
  before/after token numbers; music if possible; consistent theme across
  every element (user emphasized consistency).
- Process user wants: experience/decide the UX FIRST, then build UI.
  ADHD skill to be used for frontend ideation (user said so earlier).
- Pending question I asked: ADHD-brainstorm the UX flow vs I draft one
  clickable low-fi flow. User said "wait for instructions" — frontend
  direction comes from their next message.
- Backend contract for frontend (designed earlier): engine returns
  detective_says / old_facts / new_facts / ledger / war_windows /
  revert_matrix — engine.py currently prints text; a thin JSON wrapper may
  be needed when frontend starts.

## Working agreements
- Terse output; user switches models: fable-5 for ADHD/design, sonnet-5 for
  implementation (prompt them at phase changes). Groq: 8b-instant for
  wiring tests, 70b for final runs.
- Ask permission before starting frontend build; TDD + neat code mandatory.
