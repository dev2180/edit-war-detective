# Edit-War Detective

A noir-detective tool-calling agent that investigates Wikipedia edit wars —
built for the 100xEngineers Token Optimization Hackathon (Track A).

Given the full revision history of a Wikipedia article, the detective
answers questions like *"when is it safe to edit this page without getting
reverted?"* by retrieving raw revision data and running it through a
keyword-only RAG pipeline (chunk → index → metadata filter → deterministic
pre-aggregation) before anything reaches the LLM.

**Headline number:** 1,193,518 → 61 tokens, **~19,566x compression**, on the
article "2026 FIFA World Cup." Full breakdown in [SUBMISSION.md](SUBMISSION.md);
design rationale and process in [EXPLAINER.md](EXPLAINER.md).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY
```

## Run

```bash
python -m pytest              # 59 tests, no network calls
python step0_validate.py      # sanity-check the live Wikipedia API
python step1_chunk.py         # fetch + cache full revision history
python step2_index.py         # build casefiles/index.json
python step3_retrieve.py      # RETRIEVAL only -- raw revisions, no compression
python step4_augment.py       # AUGMENT only -- compresses step 3's output into a verdict
python step5_prove_it.py      # BEFORE/AFTER report (both tools, incl. the headline number)
python engine.py              # run the live detective agent (needs GROQ_API_KEY)
```

## Structure

```
wikitools/         core engine — reverts, chunking, indexing, aggregate,
                   augment (compression stage), retrieve, ledger, case_tools
engine.py          Groq agent loop + detective persona + tool schemas
casefiles/         cached revision data (index.json + monthly chunks)
tests/             59 tests, fixture-driven, zero network calls
```
