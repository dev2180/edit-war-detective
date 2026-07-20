"""Bake the static dossier the frontend runs on -- both story mode's
scripted rail and detective mode's desk read this one file. Baking it
ahead of time means the demo never depends on Groq being reachable; the
CACHED lamp mode IS this file.

Run: python bake_dossier.py
"""
import json

from wikitools.dossier import build_dossier

ARTICLE = "2026 FIFA World Cup"
LIVE_START, LIVE_END = "2026-06-01", "2026-07-20"
OUT_PATH = "frontend/data/case_worldcup2026.json"


def narration_for(dossier):
    """Static noir lines keyed to real numbers from this dossier -- written
    once, not LLM-generated, so story mode never needs a network call.
    """
    v = dossier["verdict"]
    before, after = dossier["before_tokens"], dossier["after_tokens"]
    cx = dossier["compression_x"]
    return {
        "cold_open": (
            f'"{dossier["revert_roster"][0]["name"] if dossier["revert_roster"] else "Somebody"} '
            f'started it. Nobody remembers who finishes these things. '
            f'{before:,} tokens of history landed on my desk. Somebody had to read it all. '
            f'That somebody was me."'
        ),
        "the_pain": f'"This is what the case looked like when it hit my desk: {before:,} tokens, raw."',
        "boss_fight_intro": '"Watch me work it down."',
        "verdict": (
            f'"{v["safest_baseline_window"]}. That\'s your window, kid. '
            f'{v["baseline_rate"]:.1%} revert rate in {v["baseline_edits_sampled"]} sampled edits, going back years. '
            f'And it held up live: {v["live_rate"]:.0%} reverts in {v["live_edits_sampled"]} edits during the tournament. '
            f'{"Still safe." if v["still_safe"] else "Not anymore -- things changed."}"'
        ) if v["safest_baseline_window"] else '"No safe window in this data. Some cases don\'t close clean."',
        "case_closed": f'"{before:,} down to {after}. {cx:,.0f}x. Case closed."',
    }


if __name__ == "__main__":
    all_revisions = json.load(open("casefiles/_all_revisions_raw.json"))

    dossier = build_dossier(
        all_revisions, article=ARTICLE,
        live_start_date=LIVE_START, live_end_date=LIVE_END,
    )
    dossier["narration"] = narration_for(dossier)

    import os
    os.makedirs("frontend/data", exist_ok=True)
    json.dump(dossier, open(OUT_PATH, "w"), indent=2)

    print(f"Wrote {OUT_PATH}")
    print(f"  before_tokens: {dossier['before_tokens']:,}")
    print(f"  after_tokens : {dossier['after_tokens']:,}")
    print(f"  compression  : {dossier['compression_x']:,.0f}x")
    print(f"  verdict      : {dossier['verdict']['safest_baseline_window']}")
    print(f"  roster size  : {len(dossier['revert_roster'])}")
    print(f"  war windows  : {len(dossier['war_windows'])}")
