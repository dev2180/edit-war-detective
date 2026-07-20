let DOSSIER = null;
let selectedRogues = [];
let lastAskWasLive = false;

/* ---- chiptune stingers: tiny square-wave notes, no audio files.
   Created lazily on first user gesture so autoplay policy never bites. */
let audioCtx = null;
function sting(notes) {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const now = audioCtx.currentTime;
    notes.forEach(([freq, start, len]) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "square";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.06, now + start);
      gain.gain.exponentialRampToValueAtTime(0.001, now + start + len);
      osc.connect(gain).connect(audioCtx.destination);
      osc.start(now + start);
      osc.stop(now + start + len);
    });
  } catch (e) { /* sound is garnish, never a blocker */ }
}
const STING = {
  coin: [[988, 0, 0.08], [1319, 0.08, 0.18]],
  hit: [[196, 0, 0.1], [131, 0.06, 0.16]],
  stamp: [[523, 0, 0.1], [659, 0.1, 0.1], [784, 0.2, 0.22]],
  click: [[660, 0, 0.06]],
};

function juice(kind) {
  const crt = document.querySelector(".crt");
  crt.classList.remove("shake", "flash");
  void crt.offsetWidth; // restart animation
  if (kind === "hit") { crt.classList.add("shake", "flash"); sting(STING.hit); }
  if (kind === "stamp") { crt.classList.add("shake"); sting(STING.stamp); }
}

const PALETTE = ["#39ff14", "#ffb000", "#ff2d55", "#00e5ff", "#c46eff"];

function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function spriteFor(username, canvas) {
  const cols = 5, rows = 7, scale = 8;
  canvas.width = cols * scale;
  canvas.height = rows * scale;
  const ctx = canvas.getContext("2d");
  const hash = hashStr(username);
  const color = PALETTE[hash % PALETTE.length];
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = color;
  const half = Math.ceil(cols / 2);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < half; c++) {
      const bit = (hash >> (r * half + c)) & 1;
      if (bit) {
        ctx.fillRect(c * scale, r * scale, scale, scale);
        ctx.fillRect((cols - 1 - c) * scale, r * scale, scale, scale);
      }
    }
  }
}

function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function typewrite(el, text, speed = 22) {
  return new Promise(resolve => {
    el.textContent = "";
    let i = 0;
    const timer = setInterval(() => {
      el.textContent += text[i];
      i++;
      if (i >= text.length) { clearInterval(timer); resolve(); }
    }, speed);
    el._skip = () => { clearInterval(timer); el.textContent = text; resolve(); };
  });
}

/* ---------------- title / attract ---------------- */

function startAttract() {
  const marquee = document.getElementById("attract-marquee");
  const names = DOSSIER.revert_roster.map(r => `${r.name.toUpperCase()} — ${r.reverts_made} REVERTS MADE`);
  const wars = DOSSIER.war_windows.map(w => `WAR WINDOW: ${w.revert_count} REVERTS IN 24H`);
  const items = [...names, ...wars, `COMPRESSION: ${Math.round(DOSSIER.compression_x).toLocaleString()}x`];
  let i = 0;
  marquee.textContent = items[0] || "";
  setInterval(() => {
    i = (i + 1) % items.length;
    marquee.textContent = items[i];
  }, 2200);
}

/* ---------------- story mode ---------------- */

const BEATS = ["beat-cold-open", "beat-pain", "beat-boss", "beat-facts", "beat-verdict", "beat-closed"];
let beatIndex = 0;
let beatRunning = false;

function enterStory() {
  sting(STING.coin);
  showScreen("screen-story");
  beatIndex = 0;
  runBeat(0);
}

async function runBeat(i) {
  document.querySelectorAll(".beat").forEach(b => b.classList.remove("active"));
  const id = BEATS[i];
  document.getElementById(id).classList.add("active");
  beatRunning = true;

  if (id === "beat-cold-open") {
    await typewrite(document.getElementById("line-cold-open"), DOSSIER.narration.cold_open);
  } else if (id === "beat-pain") {
    animateRawDump();
    animateCounter(document.getElementById("pain-counter"), DOSSIER.before_tokens, 1400);
    await sleep(1600);
    await typewrite(document.getElementById("line-pain"), DOSSIER.narration.the_pain);
  } else if (id === "beat-boss") {
    await runBossFight();
  } else if (id === "beat-facts") {
    document.getElementById("old-facts-number").textContent = DOSSIER.before_tokens.toLocaleString() + " TOKENS";
    document.getElementById("new-facts-number").textContent = DOSSIER.after_tokens + " TOKENS";
    await sleep(2200);
  } else if (id === "beat-verdict") {
    const v = DOSSIER.verdict;
    document.getElementById("verdict-stamp").textContent = v.safest_baseline_window || "NO CLEAN VERDICT";
    juice("stamp");
    await typewrite(document.getElementById("line-verdict"), DOSSIER.narration.verdict);
  } else if (id === "beat-closed") {
    await typewrite(document.getElementById("line-closed"), DOSSIER.narration.case_closed);
    renderHighscore();
  }
  beatRunning = false;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function animateRawDump() {
  const el = document.getElementById("raw-dump-scroll");
  const chars = "0123456789abcdef{}[]\":,revid timestamp reverted_editor sha1 tags comment ";
  let out = "";
  for (let i = 0; i < 400; i++) out += chars[Math.floor(Math.random() * chars.length)];
  el.textContent = out;
}

function animateCounter(el, target, duration) {
  const start = performance.now();
  function tick(now) {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic: fast start, gentle landing
    el.textContent = Math.round(target * eased).toLocaleString();
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

async function runBossFight() {
  const bar = document.getElementById("hp-bar");
  const number = document.getElementById("hp-number");
  const pop = document.getElementById("damage-pop");
  const stages = DOSSIER.stages;

  bar.style.width = "100%";
  number.textContent = stages[0].tokens_so_far.toLocaleString() + " HP";
  await sleep(600);

  for (let i = 1; i < stages.length; i++) {
    const prev = stages[i - 1].tokens_so_far;
    const cur = stages[i].tokens_so_far;
    const widthPct = Math.max(2, (cur / stages[0].tokens_so_far) * 100);
    juice("hit");
    bar.style.width = Math.min(100, widthPct) + "%";
    number.textContent = cur.toLocaleString() + " HP";
    pop.textContent = `-${(prev - cur).toLocaleString()} ${stages[i].name.toUpperCase().replace(/_/g, " ")}`;
    pop.classList.remove("pop");
    void pop.offsetWidth;
    pop.classList.add("pop");
    await sleep(1000);
  }
  const combo = document.getElementById("combo-line");
  combo.textContent = `${Math.round(DOSSIER.compression_x).toLocaleString()}x COMPRESSION COMBO — NEW RECORD`;
  combo.classList.add("pop");
  sting(STING.coin);
  await sleep(1200);
}

function renderHighscore() {
  const el = document.getElementById("highscore-table");
  const cp = DOSSIER.cost_projection;
  el.innerHTML = `
    <div><span>COMPRESSION</span><span>${Math.round(DOSSIER.compression_x).toLocaleString()}x</span></div>
    <div><span>BEFORE / YEAR</span><span>$${cp.before.yearly_cost.toFixed(2)}</span></div>
    <div><span>AFTER / YEAR</span><span>$${cp.after.yearly_cost.toFixed(2)}</span></div>
    <div><span>SAVED / YEAR</span><span>$${cp.savings.yearly_cost.toFixed(2)}</span></div>
  `;
}

function advanceStory() {
  if (beatRunning) {
    const activeBeat = document.querySelector(".beat.active");
    const typing = activeBeat && activeBeat.querySelector(".detective-line");
    if (typing && typing._skip) typing._skip();
    // A beat with no typewriter (e.g. the boss fight) can't be skipped
    // mid-animation -- ignore the click rather than racing runBeat twice.
    return;
  }
  if (beatIndex >= BEATS.length - 1) {
    enterDesk();
    return;
  }
  beatIndex++;
  runBeat(beatIndex);
}

/* ---------------- detective mode desk ---------------- */

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function enterDesk() {
  showScreen("screen-desk");
  renderHeatmap();
  renderRoster();
  renderCaseCards();
  renderEvidence();
}

function rateClass(rate) {
  if (rate === undefined || rate === null) return "";
  if (rate === 0) return "safe";
  if (rate < 0.1) return "warm";
  return "danger";
}

function renderHeatmap() {
  const el = document.getElementById("heatmap");
  el.innerHTML = "";
  DAYS.forEach(day => {
    for (let h = 0; h < 24; h++) {
      const key = `${day}-${String(h).padStart(2, "0")}`;
      const stats = DOSSIER.safety_grid[key];
      const cell = document.createElement("div");
      cell.className = "heat-cell " + rateClass(stats ? stats.rate : null);
      cell.title = key;
      cell.addEventListener("click", () => {
        const caption = document.getElementById("map-caption");
        if (!stats) {
          caption.textContent = `${key}: no history here. Detective's never seen this hour.`;
        } else {
          const pct = (stats.rate * 100).toFixed(1);
          const verdict = stats.rate === 0 ? "Clean. Nobody's watching."
            : stats.rate < 0.1 ? "Mostly quiet, but keep your head down."
            : "That's a warzone, kid. Walk away.";
          caption.textContent = `${key}: ${stats.edits} edits, ${stats.reverts} reverts, ${pct}% revert rate. ${verdict}`;
        }
      });
      el.appendChild(cell);
    }
  });
}

function renderRoster() {
  const el = document.getElementById("roster");
  el.innerHTML = "";
  DOSSIER.revert_roster.forEach(r => {
    const card = document.createElement("div");
    card.className = "rogue-card";
    const canvas = document.createElement("canvas");
    spriteFor(r.name, canvas);
    card.appendChild(canvas);
    const label = document.createElement("div");
    label.textContent = r.name.length > 12 ? r.name.slice(0, 12) + "…" : r.name;
    card.appendChild(label);
    const stat = document.createElement("div");
    stat.textContent = `${r.reverts_made} MADE / ${r.reverts_received} TAKEN`;
    card.appendChild(stat);
    card.addEventListener("click", () => toggleRogueSelection(r, card));
    el.appendChild(card);
  });
}

function toggleRogueSelection(rogue, card) {
  const idx = selectedRogues.findIndex(r => r.name === rogue.name);
  if (idx >= 0) {
    selectedRogues.splice(idx, 1);
    card.classList.remove("selected");
  } else {
    if (selectedRogues.length >= 2) {
      const removed = selectedRogues.shift();
      document.querySelectorAll(".rogue-card").forEach(c => {
        if (c.textContent.includes(removed.name.slice(0, 12))) c.classList.remove("selected");
      });
    }
    selectedRogues.push(rogue);
    card.classList.add("selected");
  }
  renderVsScreen();
}

function renderVsScreen() {
  const el = document.getElementById("vs-screen");
  if (selectedRogues.length < 2) {
    el.textContent = "Pick two rogues for a VS screen.";
    return;
  }
  const [a, b] = selectedRogues;
  const pair = DOSSIER.revert_matrix.find(
    p => (p.reverter === a.name && p.reverted === b.name) || (p.reverter === b.name && p.reverted === a.name)
  );
  if (!pair) {
    el.classList.remove("fight");
    el.textContent = `${a.name} vs ${b.name}: no recorded clashes. Not every rogue crosses paths.`;
  } else {
    el.classList.remove("fight");
    void el.offsetWidth;
    el.classList.add("fight");
    sting(STING.stamp);
    el.textContent = `FIGHT! ${pair.reverter} reverted ${pair.reverted} ${pair.count}x. That's the beef.`;
  }
}

const CASE_CARDS = [
  { label: "When can I edit safely?", query: "I'm a new editor. When's the safest time to edit this article without getting reverted?" },
  { label: "Who's behind the worst flare-up?", query: "Who was involved in the biggest edit war on this article, and when did it happen?" },
  { label: "Show me the receipts.", query: "What did that lookup cost in tokens, and what did it save?" },
];

function renderCaseCards() {
  const el = document.getElementById("case-cards");
  el.innerHTML = "";
  CASE_CARDS.forEach(c => {
    const btn = document.createElement("button");
    btn.className = "case-card";
    btn.textContent = c.label;
    btn.addEventListener("click", () => askDetective(c.query));
    el.appendChild(btn);
  });
}

async function askDetective(query) {
  const reply = document.getElementById("detective-reply");
  reply.innerHTML = '<span class="reply-badge">...</span> Working the case...';
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();
    lastAskWasLive = data.mode === "live";
    updateLamp();
    reply.innerHTML = `<span class="reply-badge ${data.mode}">${data.mode.toUpperCase()}</span>${data.detective_says}`;
  } catch (e) {
    reply.innerHTML = '<span class="reply-badge error">ERROR</span>Backend\'s not reachable — is server.py running?';
  }
}

function updateLamp() {
  const lamp = document.getElementById("mode-lamp");
  if (lastAskWasLive) { lamp.textContent = "LIVE"; lamp.classList.add("live"); }
  else { lamp.textContent = "CACHED"; lamp.classList.remove("live"); }
}

function renderEvidence() {
  updateLamp();
  const cp = DOSSIER.cost_projection;
  const maxCost = Math.max(cp.before.yearly_cost, cp.after.yearly_cost, 1);
  document.getElementById("jar-before").innerHTML =
    `<div class="jar-fill" style="height:${(cp.before.yearly_cost / maxCost) * 100}%"></div>`;
  document.getElementById("jar-after").innerHTML =
    `<div class="jar-fill" style="height:${Math.max(2, (cp.after.yearly_cost / maxCost) * 100)}%"></div>`;
  document.getElementById("jar-before-cost").textContent = `$${cp.before.yearly_cost.toFixed(2)}/yr`;
  document.getElementById("jar-after-cost").textContent = `$${cp.after.yearly_cost.toFixed(2)}/yr`;
  document.getElementById("savings-line").textContent =
    `SAVED: $${cp.savings.yearly_cost.toFixed(2)}/yr · clears volume bar: ${cp.clears_volume_bar}`;
}

async function recount() {
  const readout = document.getElementById("recount-readout");
  readout.textContent = "3... 2... 1...";
  await sleep(900);
  try {
    const res = await fetch("/api/recount", { method: "POST" });
    const data = await res.json();
    readout.textContent = `RECOUNTED: ${data.tokens.toLocaleString()} tokens (${data.tokenizer}). Matches the case file: ${data.tokens === DOSSIER.before_tokens}.`;
  } catch (e) {
    readout.textContent = "Backend's not reachable — recount needs server.py running.";
  }
}

/* ---------------- wiring ---------------- */

document.addEventListener("DOMContentLoaded", async () => {
  const res = await fetch("data/case_worldcup2026.json");
  DOSSIER = await res.json();

  startAttract();

  document.getElementById("btn-story").addEventListener("click", enterStory);
  document.getElementById("btn-desk").addEventListener("click", enterDesk);
  document.getElementById("btn-back-title").addEventListener("click", () => showScreen("screen-title"));
  document.getElementById("btn-recount").addEventListener("click", recount);
  document.getElementById("ask-submit").addEventListener("click", () => {
    const input = document.getElementById("ask-input");
    if (input.value.trim()) { askDetective(input.value.trim()); input.value = ""; }
  });
  document.getElementById("ask-input").addEventListener("keydown", e => {
    if (e.key === "Enter") document.getElementById("ask-submit").click();
  });

  document.addEventListener("keydown", () => {
    if (document.getElementById("screen-story").classList.contains("active")) advanceStory();
  });
  document.addEventListener("click", e => {
    if (!document.getElementById("screen-story").classList.contains("active")) return;
    if (e.target.closest("button, input")) return;
    advanceStory();
  });
});
