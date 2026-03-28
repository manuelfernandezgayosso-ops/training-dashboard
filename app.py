"""
IRONMAN 70.3 Training Dashboard — Web Application
Flask app served on Render.com
"""

import os, json
from pathlib import Path
from datetime import datetime, date
from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd

app = Flask(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)

# ── Race config — add future races here ──────────────────────
RACES = [
    {
        "id":       "hm_2025",
        "name":     "Half Marathon",
        "date":     "2026-05-24",
        "type":     "B",
        "distance": "21.1km run",
        "emoji":    "🏃",
    },
    {
        "id":       "im703_2025",
        "name":     "Ironman 70.3",
        "date":     "2026-06-28",
        "type":     "A",
        "distance": "1.9km / 90km / 21.1km",
        "emoji":    "🏁",
    },
]


def load_json(fname, default):
    p = DATA_DIR / fname
    if p.exists():
        try:
            return json.load(open(p))
        except Exception:
            pass
    return default


def load_csv(fname):
    p = DATA_DIR / fname
    if p.exists():
        try:
            return pd.read_csv(p).to_dict(orient="records")
        except Exception:
            pass
    return []


def sync_data():
    import subprocess, sys, traceback
    scripts = [
        "strava_connector.py",
        "training_plan_generator.py",
        "progress_tracker.py",
    ]
    for script in scripts:
        if Path(script).exists():
            print(f"[sync] Running {script}...", flush=True)
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True, text=True
            )
            if result.stdout: print(result.stdout, flush=True)
            if result.stderr: print(f"[ERROR] {script}:\n{result.stderr}", flush=True)
            if result.returncode != 0:
                print(f"[sync] {script} failed with code {result.returncode}", flush=True)
        else:
            print(f"[sync] WARNING: {script} not found", flush=True)
    print(f"[{datetime.now().strftime('%H:%M')}] Sync complete", flush=True)


# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    profile  = load_json("athlete_profile.json", {})
    notes    = load_json("progress_weekly_notes.json", [])
    now      = datetime.now()

    race_cards = []
    for r in RACES:
        rd = date.fromisoformat(r["date"])
        days_left = (rd - date.today()).days
        race_cards.append({**r, "days_left": max(0, days_left),
                           "past": days_left < 0})

    return render_template("index.html",
        athlete=profile.get("athlete_name", "Athlete"),
        races=race_cards,
        profile=profile,
        generated=now.strftime("%B %d, %Y at %I:%M %p"),
        weekly_volume=profile.get("weekly_volume_hours", 0),
        compliance=profile.get("80_20_compliance_pct", 0),
        ctl=round(profile.get("estimated_ctl", 0), 1),
        tsb=round(profile.get("estimated_tsb", 0), 1),
    )


@app.route("/api/activities")
def api_activities():
    return jsonify(load_csv("activities_clean.csv"))


@app.route("/api/fitness")
def api_fitness():
    return jsonify(load_csv("fitness_trend.csv"))


@app.route("/api/plan")
def api_plan():
    return jsonify(load_csv("training_plan_14weeks.csv"))


@app.route("/api/progress")
def api_progress():
    return jsonify(load_csv("progress_actuals.csv"))


@app.route("/api/weekly")
def api_weekly():
    return jsonify(load_csv("progress_weekly.csv"))


@app.route("/api/profile")
def api_profile():
    return jsonify(load_json("athlete_profile.json", {}))


@app.route("/api/notes")
def api_notes():
    return jsonify(load_json("progress_weekly_notes.json", []))


@app.route("/api/sync", methods=["POST"])
def api_sync():
    import threading
    thread = threading.Thread(target=sync_data)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

@app.route("/api/debug")
def api_debug():
    files = {}
    if DATA_DIR.exists():
        for f in DATA_DIR.iterdir():
            files[f.name] = f.stat().st_size
    return jsonify({"data_dir": str(DATA_DIR.resolve()), "files": files})

# ── Scheduler — daily sync at 9 PM ───────────────────────────
scheduler = BackgroundScheduler()
scheduler.add_job(sync_data, "cron", hour=21, minute=0)
scheduler.start()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

@app.route("/api/sync-log")
def api_sync_log():
    p = DATA_DIR / "sync.log"
    if p.exists():
        return p.read_text(), 200, {"Content-Type": "text/plain"}
    return "No sync log yet - hit Sync Now first.", 200
