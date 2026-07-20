"""The core engine -- character-for-character the diagnoser.py pattern:
decide, execute, respond, in a loop with one exit (no more tool calls).

Three tools:
  find_safe_edit_window -- THE problem statement (the wedding-query
                            equivalent). Two explicit stages inside:
                              RETRIEVAL -- raw revisions for a baseline
                                period and a live period, unmodified.
                              AUGMENT   -- bucket by day/hour, compute
                                revert rates, find the historically safest
                                window, check if it's still safe live.
                            Compression happens in augment, not retrieval.
  investigate_conflict   -- secondary tool: full case brief (combatants,
                            revert matrix, war windows) for a date range.
  case_ledger             -- the receipts. Reports token/cost compression
                            for whichever tool ran most recently.

The persona lives entirely in SYSTEM_PROMPT. The retrieval/augment
pipeline underneath doesn't know it's talking to a detective.
"""
import json
import os

from dotenv import load_dotenv
from groq import Groq

from wikitools.case_tools import (
    investigate_and_measure,
    build_ledger_report,
    find_safe_edit_window,
)
from wikitools.ledger import compression_factor, project_cost

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

ARTICLE = "2026 FIFA World Cup"
INDEX = json.load(open("casefiles/index.json"))
ALL_REVISIONS = json.load(open("casefiles/_all_revisions_raw.json"))

SYSTEM_PROMPT = (
    "You are Detective Marlowe, a hard-boiled noir investigator who solves "
    "Wikipedia edit wars instead of murders. The case you work is always "
    f'"{ARTICLE}". For any question about when it is SAFE to edit, call '
    "find_safe_edit_window. For any question about who fought whom, revert "
    "counts, or contentious periods, call investigate_conflict. Never guess "
    "or recall dates from memory -- always call a tool. If the question "
    "lacks a clear date range, ask the user a short follow-up question "
    "instead of guessing. Never do arithmetic yourself; if asked about "
    "token savings or cost, call case_ledger. Report findings as case "
    "notes: name names, cite the numbers the tool gave you, and close with "
    "a one-line verdict. Stay in character but keep every fact grounded in "
    "tool output."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_safe_edit_window",
            "description": (
                "Find the historically safest day-of-week and hour-of-day to "
                "edit this article (lowest revert rate), then check whether "
                "that same window is still safe during a given live period "
                "(e.g. the tournament dates). Answers 'when can I edit "
                "without getting reverted?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "live_start_date": {"type": "string", "description": "YYYY-MM-DD, start of the period to check safety during"},
                    "live_end_date": {"type": "string", "description": "YYYY-MM-DD, end of that period"},
                },
                "required": ["live_start_date", "live_end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "investigate_conflict",
            "description": (
                "Pull the case brief for the edit war on the article between "
                "two dates: per-editor revert stats, who-reverts-whom matrix, "
                "weekly edit churn, and detected war windows (bursts of "
                "reverts within 24h). Optionally narrow to one editor's "
                "involvement."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "editor": {
                        "type": ["string", "null"],
                        "description": "Narrow the brief to one editor's involvement, if named.",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "case_ledger",
            "description": (
                "Report the token and cost receipts for the most recent "
                "tool call: before/after token counts, compression factor, "
                "and daily/monthly/yearly cost at realistic query volume."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

_last_measurement = None
_last_kind = None


def run_tools(name, args):
    global _last_measurement, _last_kind
    print(f"  [tool call] {name}({args})")

    if name == "find_safe_edit_window":
        # RETRIEVAL happens inside find_safe_edit_window (raw revisions
        # pulled from the cached corpus), AUGMENT happens right after it
        # (day/hour bucketing + rate computation) -- see wikitools/case_tools.py
        # and wikitools/augment.py for the two stages, kept as separate functions.
        result, measurement = find_safe_edit_window(
            ALL_REVISIONS, args.get("live_start_date"), args.get("live_end_date"),
        )
        _last_measurement, _last_kind = measurement, "safe_window"
        return result

    if name == "investigate_conflict":
        result, measurement = investigate_and_measure(
            INDEX, ALL_REVISIONS, ARTICLE,
            args.get("start_date"), args.get("end_date"), args.get("editor"),
        )
        _last_measurement, _last_kind = measurement, "conflict_brief"
        return result

    if name == "case_ledger":
        if _last_kind == "safe_window":
            before, after = _last_measurement["before_tokens"], _last_measurement["after_tokens"]
            return {
                "before_tokens": before,
                "after_tokens": after,
                "compression_x": compression_factor(before, after),
                "cost_projection": project_cost(before, after, 0.59, queries_per_day=50),
            }
        if _last_kind == "conflict_brief":
            return build_ledger_report(_last_measurement)
        return {"error": "no investigation has run yet"}

    return {"error": f"unknown tool: {name}"}


def investigate(query):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    while True:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile", messages=messages, tools=TOOLS,
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content  # GENERATE

        messages.append(msg)
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = run_tools(call.function.name, args)  # RETRIEVE (+ AUGMENT inside)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })  # the augmented (already-compressed) result enters the model's context here


if __name__ == "__main__":
    print(investigate(
        "I'm a new editor and I want to add the final match result to the "
        "2026 FIFA World Cup article without getting reverted. Based on the "
        "full history, when's the safest time to edit -- and is that "
        "window still safe during the tournament (June 1 to July 20, 2026)?"
    ))
    print()
    print(investigate("What did that lookup cost in tokens, and what did it save?"))
