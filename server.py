"""Serves the frontend and the two live endpoints it calls: /api/ask
(the detective agent, live Groq) and /api/recount (independent token
re-derivation from the cached corpus). Everything else the frontend needs
(story mode rail, detective-mode desk data) is the static baked dossier at
frontend/data/case_worldcup2026.json -- no endpoint needed for that.

Run: python server.py
"""
import json

from flask import Flask, jsonify, request, send_from_directory

import engine
from wikitools.live import ask_detective, recount

app = Flask(__name__, static_folder="frontend", static_url_path="")

ALL_REVISIONS = engine.ALL_REVISIONS
LIVE_START, LIVE_END = "2026-06-01", "2026-07-20"


@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


@app.route("/api/ask", methods=["POST"])
def api_ask():
    query = (request.get_json(silent=True) or {}).get("query", "")
    if not query:
        return jsonify({"detective_says": "Give me something to work with, kid.", "mode": "error"}), 400
    return jsonify(ask_detective(query, investigate_fn=engine.investigate))


@app.route("/api/recount", methods=["POST"])
def api_recount():
    return jsonify(recount(ALL_REVISIONS, live_start_date=LIVE_START, live_end_date=LIVE_END))


if __name__ == "__main__":
    app.run(port=5000, debug=True)
