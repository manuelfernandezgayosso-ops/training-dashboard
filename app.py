"""
IRONMAN 70.3 Training Dashboard — Web Application
Flask app served on Render.com
"""

import os, json, threading
from pathlib import Path
from datetime import datetime, date
from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd

app = Flask(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)

_cache = {}
_last_rebaseline = {"date": None}

RACES = [
    {"id":"hm_2026","name":"Half Marathon","date":"2026-05-24","type":"B","distance":"21.1km run","emoji":"🏃"},
    {"id":"im703_2026","name":"Ironman 70.3","date":"2026-06-28","type":"A","distance":"1.9km / 90km / 21.1km","emoji":"🏁"},
]


def load_json(fname, default):
    if fname in _cache: return _cache[fname]
    p = DATA_DIR / fname
    if p.exists():
        try:
            data = json.load(open(p)); _cache[fname] = data; return data
        except Exception: pass
    return default


def load_csv(fname):
    if fname in _cache: return _cache[fname]
    p = DATA_DIR / fname
    if p.exists():
        try:
            df = pd.read_csv(p)
            data = json.loads(df.to_json(orient="records"))
            _cache[fname] = data; return data
        except Exception: pass
    return []


def run_script(script: str) -> bool:
    import subprocess, sys
    if Path(script).exists():
        print(f"[sync] Running {script}...", flush=True)
        r = subprocess.run([sys.executable, script], capture_output=True, text=True)
        if r.stdout: print(r.stdout, flush=True)
        if r.stderr: print(f"[ERROR] {script}:\n{r.stderr}", flush=True)
        return r.returncode == 0
    print(f"[sync] WARNING: {script} not found", flush=True)
    return False


def sync_data():
    for s in ["strava_connector.py","intervals_connector.py","race_goals.py",
              "training_plan_generator.py","progress_tracker.py","nutrition_planner.py"]:
        run_script(s)
    _cache.clear()
    print(f"[{datetime.now().strftime('%H:%M')}] Sync complete", flush=True)


def rebaseline():
    """Re-run goals + plan + progress + nutrition."""
    print("[rebaseline] Starting...", flush=True)
    for s in ["race_goals.py","training_plan_generator.py","progress_tracker.py","nutrition_planner.py"]:
        run_script(s)
    _cache.clear()
    _last_rebaseline["date"] = datetime.now().isoformat()
    print(f"[rebaseline] Done at {_last_rebaseline['date']}", flush=True)


def maybe_weekly_rebaseline():
    from datetime import timedelta
    last = _last_rebaseline.get("date")
    if last:
        if (date.today() - datetime.fromisoformat(last).date()).days < 7:
            return
    print("[scheduler] Weekly auto-rebaseline triggered", flush=True)
    rebaseline()


def nightly():
    sync_data()
    maybe_weekly_rebaseline()


# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    profile   = load_json("athlete_profile.json", {})
    readiness = load_json("today_readiness.json", {})
    goals     = load_json("race_goals.json", {})
    now = datetime.now()
    race_cards = []
    for r in RACES:
        rd = date.fromisoformat(r["date"])
        days_left = (rd - date.today()).days
        race_cards.append({**r, "days_left": max(0, days_left), "past": days_left < 0})
    return render_template("index.html",
        athlete=profile.get("athlete_name","Athlete"),
        races=race_cards, profile=profile, readiness=readiness, goals=goals,
        generated=now.strftime("%B %d, %Y at %I:%M %p"),
        weekly_volume=profile.get("weekly_volume_hours",0),
        compliance=profile.get("80_20_compliance_pct",0),
        ctl=round(profile.get("estimated_ctl",0),1),
        tsb=round(profile.get("estimated_tsb",0),1),
        readiness_score=readiness.get("readiness_score",0),
        readiness_label=readiness.get("readiness_label","No data yet"),
        readiness_color=readiness.get("readiness_color","#64748b"),
        hrv=readiness.get("hrv"), hrv_baseline=readiness.get("hrv_baseline"),
        sleep_hrs=readiness.get("sleep_hrs"), sleep_score=readiness.get("sleep_score"),
        resting_hr=readiness.get("resting_hr"),
        last_rebaseline=_last_rebaseline["date"],
    )

@app.route("/api/activities")
def api_activities(): return jsonify(load_csv("activities_clean.csv"))

@app.route("/api/fitness")
def api_fitness(): return jsonify(load_csv("fitness_trend.csv"))

@app.route("/api/plan")
def api_plan(): return jsonify(load_csv("training_plan_14weeks.csv"))

@app.route("/api/progress")
def api_progress(): return jsonify(load_csv("progress_actuals.csv"))

@app.route("/api/weekly")
def api_weekly(): return jsonify(load_csv("progress_weekly.csv"))

@app.route("/api/profile")
def api_profile(): return jsonify(load_json("athlete_profile.json",{}))

@app.route("/api/notes")
def api_notes(): return jsonify(load_json("progress_weekly_notes.json",[]))

@app.route("/api/wellness")
def api_wellness(): return jsonify(load_csv("wellness.csv"))

@app.route("/api/readiness")
def api_readiness(): return jsonify(load_json("readiness.json",[]))

@app.route("/api/today-readiness")
def api_today_readiness(): return jsonify(load_json("today_readiness.json",{}))

@app.route("/api/nutrition")
def api_nutrition(): return jsonify(load_json("nutrition_plan.json",[]))

@app.route("/api/nutrition-targets")
def api_nutrition_targets(): return jsonify(load_csv("nutrition_targets.csv"))

@app.route("/api/goals")
def api_goals(): return jsonify(load_json("race_goals.json",{}))

@app.route("/api/sync", methods=["POST"])
def api_sync():
    threading.Thread(target=sync_data, daemon=True).start()
    return jsonify({"status":"ok","time":datetime.now().isoformat()})

@app.route("/api/rebaseline", methods=["POST"])
def api_rebaseline():
    threading.Thread(target=rebaseline, daemon=True).start()
    return jsonify({
        "status":"ok",
        "message":"Rebaseline started — plan updates in ~60 seconds",
        "time":datetime.now().isoformat()
    })

@app.route("/api/rebaseline-status")
def api_rebaseline_status():
    return jsonify({"last_rebaseline": _last_rebaseline["date"]})

@app.route("/api/debug")
def api_debug():
    files = {f.name:f.stat().st_size for f in DATA_DIR.iterdir()} if DATA_DIR.exists() else {}
    return jsonify({"data_dir":str(DATA_DIR.resolve()),"files":files,"cache_keys":list(_cache.keys())})

@app.route("/api/sync-log")
def api_sync_log():
    p = DATA_DIR/"sync.log"
    return (p.read_text(),200,{"Content-Type":"text/plain"}) if p.exists() else ("No sync log yet.",200)


# ── Scheduler + startup ───────────────────────────────────────
scheduler = BackgroundScheduler()
scheduler.add_job(nightly, "cron", hour=21, minute=0)
scheduler.start()
threading.Thread(target=sync_data, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",5000)), debug=False)
