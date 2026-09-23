#!/usr/bin/env python3
"""
A320 ATQ 2026 - Group Answer Voting App
-----------------------------------------
Run this on one computer (e.g. your Windows PC):

    python app.py

Then share your local IP with friends on the same network, e.g.:

    http://192.168.1.42:8000

Everyone opens that link in a browser, picks a name, and votes on each
question. Results (vote counts per option + comments) update live.

No external packages required - just the Python standard library.
"""

import json
import sqlite3
import threading
import socketserver
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os

PORT = int(os.environ.get("PORT", 8000))
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quiz_votes.db")
AUDIT_TXT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_log.txt")

# ---------------------------------------------------------------------------
# Question bank (A320 2026 Annual Technical Questionnaire)
# ---------------------------------------------------------------------------
QUESTIONS = [
    {"id": 1, "text": "You get on G-EUUT for the first flight of the day. The AML shows a missing root fillet fairing on the left wing, which you spot on your walkaround. Unfortunately, you also spot a missing nacelle strake on the left hand engine, which is not in the AML. Which of the following is correct?",
     "options": {"a": "You can dispatch as long as you increase the approach speed to VAPP + 5 kt and increase the landing distance by a factor of 1.08",
                 "b": "The combination of the missing root fillet and the missing nacelle strake means you cannot dispatch",
                 "c": "You can dispatch but the takeoff performance limiting weight is reduced by 170 kg (375 lb). This performance penalty is not applicable if the flight crew can check that V2 is greater than 1.15 VS1G",
                 "d": "None of the above."}},
    {"id": 2, "text": "You have an upcoming day trip to Split (SPU/LDSP) on your roster. Having not been there before, what must you do before reporting for this duty?",
     "options": {"a": "Watch the audio visual presentation and read the written briefing",
                 "b": "Only read the written briefing.",
                 "c": "Only watch the audio visual presentation",
                 "d": "None of the above."}},
    {"id": 3, "text": "Whilst reviewing the eLog, prior to your LHR-LIS flight, you notice the aircraft has come in from CDG early this morning with an ACF for ILS 1 INOP. Which of the following is true regarding the ACF?",
     "options": {"a": "The ACF is linked to the originating Captain",
                 "b": "The ACF is linked to the defect and may be carried forward",
                 "c": "Once back at LHR the defect cannot be ACF'd",
                 "d": "None of the above."}},
    {"id": 4, "text": "When dispatching with multiple MEL items inoperative, which of the following is correct?",
     "options": {"a": "The MEL can take into account all multiple unserviceabilities automatically",
                 "b": "Selecting each MEL item in FlySmart means no further action is required",
                 "c": "The MEL cannot take into account all inter-relationships, therefore safety and workload must be assessed",
                 "d": "None of the above."}},
    {"id": 5, "text": "Whilst sat in Heathrow's Terminal 5 waiting for your delayed inbound Aircraft, which of the following is true regarding FDP management?",
     "options": {"a": "Global Ops defines LTOT",
                 "b": "The Commander defines LTOT with Ops agreement",
                 "c": "Global Ops defines LTOT and informs the Captain (who has the final decision)",
                 "d": "None of the above."}},
    {"id": 6, "text": "Which of the following is true regarding single pack operation on the ground?",
     "options": {"a": "Prohibited on NEO only",
                 "b": "Prohibited on CEO only",
                 "c": "Permitted on both CEOs and NEOs if one pack is sufficient",
                 "d": "None of the above."}},
    {"id": 7, "text": "After PM has set the ENG MASTER to ON during a manual start, how would you abort the sequence?",
     "options": {"a": "ENG MAN START pb-sw OFF",
                 "b": "MAN START pb-sw OFF then ENG MASTER lever OFF",
                 "c": "ENG MASTER lever OFF then ENG MAN START pb-sw OFF",
                 "d": "None of the above."}},
    {"id": 8, "text": "When does In-Flight Fuel Management take effect?",
     "options": {"a": "When aircraft has pushed back off stand",
                 "b": "When aircraft is airborne (take off time)",
                 "c": "When aircraft moves under its own power",
                 "d": "None of the above."}},
    {"id": 9, "text": "For destination alternates, a type B aerodrome has a minima of:",
     "options": {"a": "< 250ft",
                 "b": "\u2264 250ft",
                 "c": "\u2265 250ft",
                 "d": "None of the above."}},
    {"id": 10, "text": "Anti/De-Ice fluid ingestion would be classed as which source of odour?",
     "options": {"a": "Aircraft",
                 "b": "Cabin",
                 "c": "Environmental",
                 "d": "None of the above."}},
    {"id": 11, "text": "You board G-TTNA to operate LHR to GCI and there is an MEL 27-92-02B open in the tech log. Which of the following applies?",
     "options": {"a": "Yes, dispatch is permitted but MAX reverse is required",
                 "b": "No, dispatch is not permitted",
                 "c": "Yes, dispatch is permitted",
                 "d": "None of the above."}},
    {"id": 12, "text": "What makes up REQUIRED FUEL at the time of departure?",
     "options": {"a": "TAXI, TRIP, CONTINGENCY, DESTINATION ALTERNATE (or 15 MINS OF HOLDING FUEL; if flight is planned without a Destination Alternate), EXTRA, ETOPS/CRITF (if required)",
                 "b": "APU, TAXI, TRIP, CONTINGENCY, DESTINATION ALTERNATE (or 15 MINS OF HOLDING FUEL; if flight is planned without a Destination Alternate), FINAL RESERVE, ETOPS/CRITF (if required)",
                 "c": "TAXI, TRIP, CONTINGENCY, DESTINATION ALTERNATE (or 15 MINS OF HOLDING FUEL; if flight is planned without a Destination Alternate), FINAL RESERVE, ETOPS/CRITF (if required)",
                 "d": "None of the above."}},
    {"id": 13, "text": "What conditions must be met before selecting the Ready To Go (RTG) prompt on aircraft with A-RTG functionality?",
     "options": {"a": "Both flight crew and ground crew fully ready, pre departure cockpit and ground crew procedures completed, aircraft attached to a tug",
                 "b": "Both flight crew and ground crew fully ready, pre departure cockpit and ground crew procedures completed, aircraft connected to a tug (unless departing from a self manoeuvring stand)",
                 "c": "Flight crew fully ready, pre departure cockpit procedures completed, aircraft connected to a tug (unless departing from a self manoeuvring stand)",
                 "d": "None of the above."}},
    {"id": 14, "text": "Door 2R will not close properly before pushback. What should you do?",
     "options": {"a": "Slightly re-open from inside",
                 "b": "Liaise with SCCM and ground crew for door re-opening",
                 "c": "One flight crew member re-opens door",
                 "d": "None of the above."}},
    {"id": 15, "text": "During Takeoff, which of the below is most accurate? The FO when PF can call \u201cSTOP\u201d for?",
     "options": {"a": "Any ECAM up to V1",
                 "b": "Fire warning, severe damage, loss of thrust up to V1",
                 "c": "Fire warning, severe damage, loss of thrust, blocked runway, handling difficulty up to V1",
                 "d": "None of the above."}},
    {"id": 16, "text": "At 1000 ft AAL your speed is 14 knots above target approach speed and reducing due to an appropriate ATC instruction. Which is correct?",
     "options": {"a": "Unstable \u2013 Go Around",
                 "b": "PM reassesses stability at 500 ft",
                 "c": "PM may call \u201cSpeed\u201d, stable by 500 ft",
                 "d": "None of the above."}},
    {"id": 17, "text": "Prior to entering RVSM airspace, what is required?",
     "options": {"a": "2 primary altimeter systems to agree within +/- 200ft",
                 "b": "2 primary altimeter systems to agree within +/- 150ft",
                 "c": "1 primary altimeter system, providing it has a serviceable automatic altitude control and alerting system.",
                 "d": "None of the above."}},
    {"id": 18, "text": "Following an Engine Failure After Takeoff, when would you suspect Engine Damage?",
     "options": {"a": "Loud bang alone",
                 "b": "One abnormal symptom",
                 "c": "Two or more abnormal symptoms",
                 "d": "None of the above."}},
    {"id": 19, "text": "A momentary overspeed warning occurs during flap retraction. What is true?",
     "options": {"a": "Overspeed based on lever position, no report",
                 "b": "Based on actual slat and flap position, report required",
                 "c": "Immediate maintenance inspection required",
                 "d": "None of the above."}},
    {"id": 20, "text": "A landing above MLW may be required in which circumstances?",
     "options": {"a": "When delaying landing increases hazard or QRH permits",
                 "b": "LAND ASAP only",
                 "c": "Never",
                 "d": "None of the above."}},
    {"id": 21, "text": "ENG oil quantity pulses green at high thrust. Which is true?",
     "options": {"a": "Oil gulping may cause temporary decrease",
                 "b": "Engine failure imminent",
                 "c": "Apply IDG QRH actions",
                 "d": "None of the above."}},
    {"id": 22, "text": "TCAS RA occurs but required V/S cannot be achieved. What should PF do?",
     "options": {"a": "Leave AP engaged",
                 "b": "Disconnect AP, override FD if necessary",
                 "c": "Disconnect AP, follow FD",
                 "d": "None of the above."}},
    {"id": 23, "text": "Which statement is true when dispatching without a destination alternate?",
     "options": {"a": "Diversion fuel reduced to zero",
                 "b": "Replace diversion fuel with 15 minutes holding",
                 "c": "Replace diversion fuel with 30 minutes holding",
                 "d": "None of the above."}},
    {"id": 24, "text": "MSA is 15,300 ft with winds 60 kt. What is the MOA?",
     "options": {"a": "15,300 ft",
                 "b": "17,300 ft",
                 "c": "19,700 ft",
                 "d": "None of the above."}},
    {"id": 25, "text": "On Aircraft G-TTSK, what is the default non-precision approach type on the PERF APPR page?",
     "options": {"a": "FLS",
                 "b": "FINAL APP",
                 "c": "RNAV",
                 "d": "None of the above."}},
    {"id": 26, "text": "After FINAL APP engagement, how must the vertical profile be monitored?",
     "options": {"a": "Altitudes checked at waypoints",
                 "b": "V/DEV only",
                 "c": "No monitoring required",
                 "d": "None of the above."}},
    {"id": 27, "text": "How is a safe rollout achieved?",
     "options": {"a": "Maintain planned deceleration devices until stop is assured and appropriate runway exit speed is reached",
                 "b": "Maintain decel until 70 kt",
                 "c": "Early cancel A/BRK if decel is high",
                 "d": "None of the above."}},
    {"id": 28, "text": "Which is true for go-arounds near the ground in an A321NEO?",
     "options": {"a": "Below 100 ft, thrust effect must be countered",
                 "b": "Below 50 ft, thrust effect applies",
                 "c": "Flare law compensates fully",
                 "d": "None of the above."}},
    {"id": 29, "text": "What is the recommended action when encountering a significant CB?",
     "options": {"a": "Avoid \u226510 NM",
                 "b": "Decide 20 NM away",
                 "c": "Decide 40 NM away, avoid \u226520 NM",
                 "d": "None of the above."}},
    {"id": 30, "text": "On G-EUPD, after A.FLOOR disengages during a windshear GA, what is true?",
     "options": {"a": "Thrust reverts to previous A/THR mode",
                 "b": "Thrust reverts to MAN if A/THR off",
                 "c": "TOGA LK requires A/THR disconnect",
                 "d": "None of the above."}},
    {"id": 31, "text": "Directional control is difficult on a contaminated runway. What should you do?",
     "options": {"a": "Maintain reverse, release brakes",
                 "b": "Set reverse idle, maintain braking",
                 "c": "Idle reverse, release brakes, regain centreline",
                 "d": "None of the above."}},
    {"id": 32, "text": "What is the recommended contaminated runway landing technique?",
     "options": {"a": "Brief flare, firm touchdown, MAX REV",
                 "b": "Long flare, IDLE REV",
                 "c": "No autobrake use",
                 "d": "None of the above."}},
    {"id": 33, "text": "How must a fuel check be completed in flight?",
     "options": {"a": "FOB + used fuel, FMGC prediction, Fuel Delta",
                 "b": "Balance only",
                 "c": "Delta only",
                 "d": "None of the above."}},
    {"id": 34, "text": "When shall Sterile Flight Deck procedures be applied?",
     "options": {"a": "Below 10,000 ft only",
                 "b": "During critical phases only",
                 "c": "Below 10,000 ft, critical phases, and as designated by Captain",
                 "d": "None of the above."}},
    {"id": 35, "text": "How soon after turning off the APU can BAT 1 & 2 be turned off?",
     "options": {"a": "Immediately",
                 "b": "After flap closure",
                 "c": "After 3 minutes",
                 "d": "None of the above."}},
]

QUESTIONS_JSON = json.dumps(QUESTIONS)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
db_lock = threading.Lock()


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            question_id INTEGER NOT NULL,
            voter TEXT NOT NULL,
            option TEXT NOT NULL,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (question_id, voter)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            voter TEXT NOT NULL,
            comment TEXT NOT NULL,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # audit_log is append-only: unlike "votes" (which only keeps each
    # person's latest answer), this keeps every vote/comment event ever
    # submitted, so you can see if someone changed their answer repeatedly
    # or voted suspiciously. Also doubles as the backup export source.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            question_id INTEGER,
            voter TEXT NOT NULL,
            value TEXT NOT NULL,
            remote_addr TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_event(event_type, question_id, voter, value, remote_addr=None):
    """Append one row to the audit_log table AND to a plain-text log file
    next to the database, so there are two independent copies of the
    history (handy if you just want to eyeball audit_log.txt directly)."""
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (event_type, question_id, voter, value, remote_addr) VALUES (?, ?, ?, ?, ?)",
        (event_type, question_id, voter, value, remote_addr),
    )
    conn.commit()
    conn.close()
    try:
        with open(AUDIT_TXT_PATH, "a", encoding="utf-8") as f:
            ts = __import__("datetime").datetime.now().isoformat(timespec="seconds")
            f.write(f"{ts}\t{event_type}\tQ{question_id}\t{voter}\t{value!r}\t{remote_addr or ''}\n")
    except Exception:
        pass  # never let logging break the app


def get_results():
    conn = get_db()
    results = {}
    for q in QUESTIONS:
        qid = q["id"]
        counts = {opt: 0 for opt in q["options"]}
        voters = {opt: [] for opt in q["options"]}
        for row in conn.execute("SELECT voter, option FROM votes WHERE question_id=?", (qid,)):
            if row["option"] in counts:
                counts[row["option"]] += 1
                voters[row["option"]].append(row["voter"])
        comments = [
            {"voter": r["voter"], "comment": r["comment"]}
            for r in conn.execute(
                "SELECT voter, comment FROM comments WHERE question_id=? ORDER BY ts", (qid,)
            )
        ]
        results[qid] = {"counts": counts, "voters": voters, "comments": comments}
    conn.close()
    return results


# ---------------------------------------------------------------------------
# Frontend (single page app, no external dependencies)
# ---------------------------------------------------------------------------
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A320 ATQ 2026 - Group Vote</title>
<style>
  :root {
    --bg: #0f1621; --panel: #182234; --panel2: #1f2c42; --text: #e8edf5;
    --muted: #93a1b8; --accent: #4fa3ff; --accent2: #35d08f; --border: #2a3652;
  }
  * { box-sizing: border-box; }
  body { margin:0; font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); padding-bottom: 60px; }
  header { position: sticky; top:0; background: var(--panel); border-bottom: 1px solid var(--border);
    padding: 14px 20px; z-index: 10; display:flex; align-items:center; justify-content: space-between; flex-wrap: wrap; gap: 10px;}
  header h1 { font-size: 17px; margin: 0; }
  header .sub { color: var(--muted); font-size: 12px; }
  #nameBox { display:flex; gap:8px; align-items:center; }
  #nameBox input { background: var(--panel2); border: 1px solid var(--border); color: var(--text);
    padding: 8px 10px; border-radius: 6px; font-size: 14px; width: 160px;}
  #nameBox button { background: var(--accent); border:none; color:#08182b; font-weight:600;
    padding: 8px 14px; border-radius: 6px; cursor:pointer; font-size: 14px;}
  #status { font-size: 12px; color: var(--accent2); min-height: 16px; }
  main { max-width: 820px; margin: 20px auto; padding: 0 16px; }
  .q { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px 18px; margin-bottom: 16px; }
  .q .qhead { display:flex; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
  .q .qnum { color: var(--accent); font-weight: 700; font-size: 13px; }
  .q .qtext { font-size: 15px; line-height: 1.45; margin: 4px 0 12px 0; }
  .opt { display:flex; align-items:center; gap:10px; padding: 8px 10px; border-radius: 8px;
    border: 1px solid transparent; margin-bottom: 6px; cursor: pointer; }
  .opt:hover { background: var(--panel2); }
  .opt.selected { border-color: var(--accent); background: rgba(79,163,255,0.12); }
  .opt input { accent-color: var(--accent); }
  .optlabel { flex: 1; font-size: 14px; }
  .bar-wrap { flex: 1; height: 8px; background: #0b111c; border-radius: 4px; overflow: hidden; margin-left: 8px; }
  .bar { height: 100%; background: var(--accent2); }
  .count { font-size: 12px; color: var(--muted); min-width: 70px; text-align: right; }
  .voters { font-size: 11px; color: var(--muted); margin-left: 34px; margin-top: -2px; margin-bottom: 4px;}
  details.comments { margin-top: 10px; }
  details.comments summary { cursor: pointer; color: var(--muted); font-size: 13px; }
  .clist { margin: 8px 0; padding-left: 0; list-style: none; }
  .clist li { background: var(--panel2); border-radius: 6px; padding: 6px 10px; margin-bottom: 6px; font-size: 13px;}
  .clist li b { color: var(--accent); }
  .caddrow { display:flex; gap: 8px; margin-top: 6px; }
  .caddrow input { flex:1; background: var(--panel2); border: 1px solid var(--border); color: var(--text);
    padding: 7px 10px; border-radius: 6px; font-size: 13px;}
  .caddrow button { background: var(--panel2); border: 1px solid var(--border); color: var(--text);
    padding: 7px 12px; border-radius: 6px; cursor: pointer; font-size: 13px;}
  .locked-msg { color: var(--muted); font-size: 12px; margin-bottom: 12px; }
  footer { text-align:center; color: var(--muted); font-size: 12px; margin-top: 30px;}
</style>
</head>
<body>
<header>
  <div>
    <h1>A320 ATQ 2026 - Group Vote</h1>
    <div class="sub" id="voterSub">Enter your name to vote</div>
  </div>
  <div id="nameBox">
    <input id="nameInput" placeholder="Your name" maxlength="30">
    <button onclick="setName()">Set name</button>
  </div>
</header>
<main>
  <div id="status"></div>
  <div class="locked-msg" id="lockedMsg" style="display:none">Set your name above to vote. You can still see live results below.</div>
  <div id="questions"></div>
</main>
<footer>Votes refresh automatically every few seconds.</footer>

<script>
const QUESTIONS = __QUESTIONS_JSON__;
let myName = localStorage.getItem('quizVoterName') || '';
let myVotes = {}; // questionId -> option, loaded from server responses indirectly (we track locally too)

function setName() {
  const v = document.getElementById('nameInput').value.trim();
  if (!v) { alert('Please enter a name'); return; }
  myName = v;
  localStorage.setItem('quizVoterName', v);
  render();
}

function letterOf(opt) { return opt.toUpperCase(); }

async function vote(qid, option) {
  if (!myName) { alert('Please set your name first'); return; }
  myVotes[qid] = option;
  try {
    const r = await fetch('/api/vote', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question_id: qid, voter: myName, option: option})
    });
    if (!r.ok) throw new Error('vote failed');
    setStatus('Vote saved.');
  } catch(e) {
    setStatus('Could not save vote - check connection.', true);
  }
  refresh();
}

async function addComment(qid) {
  if (!myName) { alert('Please set your name first'); return; }
  const input = document.getElementById('cin-' + qid);
  const text = input.value.trim();
  if (!text) return;
  try {
    await fetch('/api/comment', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question_id: qid, voter: myName, comment: text})
    });
    input.value = '';
  } catch(e) {}
  refresh();
}

function setStatus(msg, isError) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.style.color = isError ? '#ff6b6b' : 'var(--accent2)';
  setTimeout(() => { if (el.textContent === msg) el.textContent = ''; }, 2500);
}

let latestResults = {};

async function refresh() {
  try {
    const r = await fetch('/api/results');
    latestResults = await r.json();
    render();
  } catch(e) { /* server might be briefly unreachable */ }
}

function render() {
  document.getElementById('voterSub').textContent = myName ? ('Voting as: ' + myName) : 'Enter your name to vote';
  document.getElementById('nameInput').value = myName;
  document.getElementById('lockedMsg').style.display = myName ? 'none' : 'block';

  const container = document.getElementById('questions');
  container.innerHTML = '';
  QUESTIONS.forEach(q => {
    const res = latestResults[q.id] || {counts:{}, voters:{}, comments:[]};
    const totalVotes = Object.values(res.counts || {}).reduce((a,b)=>a+b, 0);
    const myPick = myVotes[q.id];

    const div = document.createElement('div');
    div.className = 'q';

    const head = document.createElement('div');
    head.className = 'qhead';
    head.innerHTML = '<span class="qnum">Q' + q.id + '</span><span style="color:var(--muted);font-size:12px;">' + totalVotes + ' vote' + (totalVotes===1?'':'s') + '</span>';
    div.appendChild(head);

    const qtext = document.createElement('div');
    qtext.className = 'qtext';
    qtext.textContent = q.text;
    div.appendChild(qtext);

    Object.keys(q.options).forEach(optKey => {
      const optText = q.options[optKey];
      const count = (res.counts && res.counts[optKey]) || 0;
      const pct = totalVotes ? Math.round((count/totalVotes)*100) : 0;
      const voters = (res.voters && res.voters[optKey]) || [];

      const row = document.createElement('div');
      row.className = 'opt' + (myPick === optKey ? ' selected' : '');
      row.onclick = () => vote(q.id, optKey);

      row.innerHTML =
        '<input type="radio" name="q' + q.id + '" ' + (myPick===optKey?'checked':'') + ' onclick="event.stopPropagation(); vote(' + q.id + ', \\'' + optKey + '\\')">' +
        '<span class="optlabel"><b>' + letterOf(optKey) + '.</b> ' + optText.replace(/</g,'&lt;') + '</span>' +
        '<div class="bar-wrap"><div class="bar" style="width:' + pct + '%"></div></div>' +
        '<span class="count">' + count + ' (' + pct + '%)</span>';
      div.appendChild(row);

      if (voters.length) {
        const vsub = document.createElement('div');
        vsub.className = 'voters';
        vsub.textContent = voters.join(', ');
        div.appendChild(vsub);
      }
    });

    const details = document.createElement('details');
    details.className = 'comments';
    const summary = document.createElement('summary');
    summary.textContent = 'Comments (' + (res.comments ? res.comments.length : 0) + ')';
    details.appendChild(summary);

    const clist = document.createElement('ul');
    clist.className = 'clist';
    (res.comments || []).forEach(c => {
      const li = document.createElement('li');
      li.innerHTML = '<b>' + c.voter.replace(/</g,'&lt;') + ':</b> ' + c.comment.replace(/</g,'&lt;');
      clist.appendChild(li);
    });
    details.appendChild(clist);

    const addrow = document.createElement('div');
    addrow.className = 'caddrow';
    addrow.innerHTML = '<input id="cin-' + q.id + '" placeholder="Add a comment...">' +
      '<button onclick="addComment(' + q.id + ')">Post</button>';
    details.appendChild(addrow);

    div.appendChild(details);
    container.appendChild(div);
  });
}

document.getElementById('nameInput').addEventListener('keydown', e => { if (e.key === 'Enter') setName(); });

refresh();
setInterval(refresh, 4000);
</script>
</body>
</html>
"""

PAGE = PAGE_TEMPLATE.replace("__QUESTIONS_JSON__", QUESTIONS_JSON)
PAGE_BYTES = PAGE.encode("utf-8")


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "QuizVote/1.0"

    def log_message(self, fmt, *args):
        pass  # quieter console

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE_BYTES)))
            self.end_headers()
            self.wfile.write(PAGE_BYTES)
        elif parsed.path == "/api/results":
            with db_lock:
                self._send_json(get_results())
        elif parsed.path == "/api/questions":
            self._send_json(QUESTIONS)
        elif parsed.path == "/export":
            self._send_export_csv()
        else:
            self.send_error(404)

    def _send_export_csv(self):
        """Full history export: every vote and comment ever submitted, with
        timestamps and the voter's IP, oldest first. This is the file to
        download before redeploying (Render wipes the disk on deploy) and
        the place to look for a 'dodgy voter' - e.g. someone flip-flopping
        between answers, or many votes from the same IP under different
        names."""
        import csv
        import io

        conn = get_db()
        rows = conn.execute(
            "SELECT ts, event_type, question_id, voter, value, remote_addr "
            "FROM audit_log ORDER BY ts ASC"
        ).fetchall()
        conn.close()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["timestamp", "event_type", "question_id", "voter", "value", "ip_address"])
        for r in rows:
            writer.writerow([r["ts"], r["event_type"], r["question_id"], r["voter"], r["value"], r["remote_addr"]])
        body = buf.getvalue().encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="quiz_audit_export.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"error": "bad json"}, 400)
            return

        if parsed.path == "/api/vote":
            qid = data.get("question_id")
            voter = (data.get("voter") or "").strip()[:60]
            option = (data.get("option") or "").strip().lower()
            if not qid or not voter or option not in ("a", "b", "c", "d"):
                self._send_json({"error": "invalid vote"}, 400)
                return
            with db_lock:
                conn = get_db()
                conn.execute(
                    "INSERT INTO votes (question_id, voter, option) VALUES (?, ?, ?) "
                    "ON CONFLICT(question_id, voter) DO UPDATE SET option=excluded.option, ts=CURRENT_TIMESTAMP",
                    (qid, voter, option),
                )
                conn.commit()
                conn.close()
            log_event("vote", qid, voter, option, self.client_address[0])
            self._send_json({"ok": True})

        elif parsed.path == "/api/comment":
            qid = data.get("question_id")
            voter = (data.get("voter") or "").strip()[:60]
            comment = (data.get("comment") or "").strip()[:500]
            if not qid or not voter or not comment:
                self._send_json({"error": "invalid comment"}, 400)
                return
            with db_lock:
                conn = get_db()
                conn.execute(
                    "INSERT INTO comments (question_id, voter, comment) VALUES (?, ?, ?)",
                    (qid, voter, comment),
                )
                conn.commit()
                conn.close()
            log_event("comment", qid, voter, comment, self.client_address[0])
            self._send_json({"ok": True})
        else:
            self.send_error(404)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    init_db()
    ip = get_local_ip()
    print("=" * 60)
    print(" A320 ATQ 2026 - Group Vote server is running")
    print("=" * 60)
    print(f" On this computer:      http://localhost:{PORT}")
    print(f" For your friends (same Wi-Fi/network): http://{ip}:{PORT}")
    print("=" * 60)
    print(" Press Ctrl+C to stop the server.")
    with ThreadingHTTPServer(("0.0.0.0", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
