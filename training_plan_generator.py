#!/usr/bin/env python3
"""
IRONMAN 70.3 Training System — 14-Week Training Plan Generator
Matt Fitzgerald 80/20 Triathlon Method
Volume profiles: moderate (~8h), aggressive (~10h), high (~12h peak)
Usage: python3 training_plan_generator.py
"""

import json, os
from datetime import datetime, timedelta, date
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "~/Documents/training_data")).expanduser()
DATA_DIR   = OUTPUT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

A_RACE = date(2025, 6, 28)
B_RACE = date(2025, 5, 24)
TODAY  = date.today()

# ── Volume profile ────────────────────────────────────────────
# Scales ALL session durations up from the base template
# moderate=~8h peak | aggressive=~10h peak | high=~12h peak
VOLUME_PROFILE = os.getenv("VOLUME_PROFILE", "high")
VOLUME_SCALE = {"moderate": 1.0, "aggressive": 1.25, "high": 1.50}.get(VOLUME_PROFILE, 1.50)

# 14 weeks: week, phase, phase_factor, focus
# Final duration = base_duration * phase_factor * VOLUME_SCALE
PHASES = [
    (1,  "Base",   0.65, "All easy. Build the aerobic engine. Zone 1-2 only."),
    (2,  "Base",   0.75, "Add a long bike. Everything conversational pace."),
    (3,  "Base",   0.85, "Longest base week. Introduce Z2 brick (bike+run)."),
    (4,  "Base",   0.55, "Recovery week. Easy movement, sleep, and nutrition."),
    (5,  "Build",  0.80, "First bike intervals at Zone 3. Run stays easy."),
    (6,  "Build",  0.90, "Add run tempo. Long swim with pace sets."),
    (7,  "Build",  1.00, "Peak build volume. Race simulation brick."),
    (8,  "Build",  0.60, "Recovery week. Flush the legs."),
    (9,  "B-Race", 0.65, "Half Marathon race day May 24. Fitness test, no taper."),
    (10, "Peak",   1.00, "Highest TSS week. Back-to-back long sessions."),
    (11, "Peak",   1.05, "Race-specific brick. Open water swim if possible."),
    (12, "Peak",   0.68, "Mini-taper. Sharpen, do not dig deeper."),
    (13, "Taper",  0.45, "Volume drops 55%. Keep 2 quality sessions."),
    (14, "Taper",  0.28, "Race week. Short activations only. Trust the training."),
]

# ── Base session templates (durations at moderate/1.0 scale) ─
BASE = {
    # Mon - Swim (technique, easy start to week)
    "Mon": [{"sport":"swim", "min":40, "zone":"Zone 2", "type":"Technique Swim",
             "desc":"1,500m. 50% drill sets - catch-up, fingertip drag, bilateral breathing. Build water feel."}],
    # Tue - Easy run
    "Tue": [{"sport":"run",  "min":45, "zone":"Zone 2", "type":"Easy Run",
             "desc":"Conversational pace. HR below LTHR x 0.89. No heroics."}],
    # Wed - Swim + Bike
    "Wed": [{"sport":"swim", "min":40, "zone":"Zone 2", "type":"Aerobic Swim",
             "desc":"1,500-2,000m. 200m warm-up, 4x300m easy, 100m cool-down."},
            {"sport":"bike", "min":60, "zone":"Zone 2", "type":"Easy Spin",
             "desc":"Flat terrain. Zone 2 HR. 90 RPM cadence target."}],
    # Thu - Recovery run
    "Thu": [{"sport":"run",  "min":35, "zone":"Zone 1", "type":"Recovery Run",
             "desc":"Very easy. If legs are heavy, walk/run. HR Zone 1 only."}],
    # Fri - Rest
    "Fri": None,
    # Sat - Swim + Long Ride
    "Sat": [{"sport":"swim", "min":45, "zone":"Zone 2", "type":"Aerobic Swim",
             "desc":"2,000m. Warm-up, main set 8x200m easy, cool-down. Practice open water sighting."},
            {"sport":"bike", "min":90, "zone":"Zone 2", "type":"Long Ride",
             "desc":"Long aerobic ride. Practice race nutrition - eat and drink every 20 min."}],
    # Sun - Long Run
    "Sun": [{"sport":"run",  "min":60, "zone":"Zone 2", "type":"Long Run",
             "desc":"Easy long run. Build time on feet. Keep HR in Zone 2 throughout."}],
}

BUILD_OVERRIDES = {
    "Mon": [{"sport":"swim", "min":45, "zone":"Zone 2", "type":"Technique Swim",
             "desc":"1,800m. Drill focus: catch-up + fingertip drag. Add 4x50m build to Z3 at end."}],
    "Tue": [{"sport":"run",  "min":50, "zone":"Zone 3-4", "type":"Tempo Run",
             "desc":"10 min Z1 warm-up, 3x8 min Zone 3 tempo, 2 min easy between, 10 min cool-down."}],
    "Wed": [{"sport":"swim", "min":50, "zone":"Zone 2-3", "type":"Swim with Pace Sets",
             "desc":"2,000m. Warm-up, 6x200m descending pace (Z2 to Z3), cool-down."},
            {"sport":"bike", "min":75, "zone":"Zone 3",   "type":"Bike Intervals",
             "desc":"15 min warm-up, 4x10 min Zone 3, 3 min easy between, 10 min cool-down."}],
    "Sat": [{"sport":"swim", "min":50, "zone":"Zone 2-3", "type":"Long Swim + Pace",
             "desc":"2,500m. 400m warm-up, 4x400m at Z2-3, 200m cool-down. Simulate race distance."},
            {"sport":"bike", "min":120,"zone":"Zone 2-3", "type":"Long Ride",
             "desc":"First 90 min Z2, last 30 min push to Z3. Practice race nutrition throughout."}],
    "Sun": [{"sport":"run",  "min":65, "zone":"Zone 2",   "type":"Long Run",
             "desc":"Easy long run off yesterdays ride. Brick effect builds race-specific endurance."}],
}

PEAK_OVERRIDES = {
    "Mon": [{"sport":"swim", "min":50, "zone":"Zone 2-3", "type":"Race Prep Swim",
             "desc":"2,000m. Include 4x100m at race pace (Z3-4). Get comfortable at 70.3 effort."}],
    "Tue": [{"sport":"run",  "min":55, "zone":"Zone 3-4", "type":"Race Pace Run",
             "desc":"10 min Z1, 4x10 min at 70.3 run target pace (Z2-3), jog 90 sec between, 5 min cool."}],
    "Sat": [{"sport":"swim", "min":55, "zone":"Zone 2-3", "type":"Open Water Sim Swim",
             "desc":"2,500-3,000m. Simulate 70.3 swim conditions. Sighting every 10 strokes. No walls."},
            {"sport":"bike", "min":150,"zone":"Zone 2-3", "type":"Race Simulation Brick",
             "desc":"2h30 at 70.3 target power/HR, T2 transition, 30-min run at race pace. Full nutrition plan."}],
    "Sun": [{"sport":"run",  "min":70, "zone":"Zone 2",   "type":"Long Run",
             "desc":"Easy aerobic long run. Tired legs from Saturday are intentional. Build mental toughness."}],
}

TAPER = {
    "Mon": [{"sport":"swim", "min":30, "zone":"Zone 2",   "type":"Easy Swim",
             "desc":"1,200m easy. Just move. Keep the feel for water without taxing the body."}],
    "Tue": [{"sport":"run",  "min":30, "zone":"Zone 2",   "type":"Sharpener Run",
             "desc":"20 min easy + 4x30 sec race pace strides. Keep legs sharp."}],
    "Wed": [{"sport":"swim", "min":25, "zone":"Zone 2-3", "type":"Race Prep Swim",
             "desc":"1,000m. 400m easy, 4x100m race pace, 200m easy."},
            {"sport":"bike", "min":40, "zone":"Zone 2",   "type":"Easy Spin",
             "desc":"Easy spin. Feel the bike. No efforts. Just move."}],
    "Thu": None,
    "Fri": [{"sport":"run",  "min":20, "zone":"Zone 1",   "type":"Shakeout Run",
             "desc":"Very easy 20 min. Loosen up. Stop if anything feels off."}],
    "Sat": [{"sport":"swim", "min":15, "zone":"Zone 1",   "type":"Pre-Race Swim",
             "desc":"Easy 400-500m. Feel the water. Zero hard efforts."},
            {"sport":"bike", "min":15, "zone":"Zone 1",   "type":"Bike Check",
             "desc":"15 min easy spin. Check bike and transitions. Lay out gear tonight."}],
    "Sun": "RACE",
}

B_RACE_OVERRIDE = {
    "Fri": None,
    "Sat": [{"sport":"run",  "min":0,  "zone":"Race",    "type":"B-RACE: Half Marathon",
             "desc":"Race day! First 10km at Zone 2. Push the final 11km. This is your fitness test."}],
    "Sun": [{"sport":"run",  "min":30, "zone":"Zone 1",  "type":"Recovery Jog",
             "desc":"Very easy 20-30 min post-race jog. Flush the legs."}],
}


def build_week(week_num, phase, phase_factor, focus, week_start):
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    rows = []

    if week_num == 14:
        template = TAPER
    elif phase == "Peak":
        template = {**BASE, **PEAK_OVERRIDES}
    elif phase == "Build":
        template = {**BASE, **BUILD_OVERRIDES}
    elif phase == "B-Race":
        template = {**BASE, **B_RACE_OVERRIDE}
    else:
        template = BASE

    for i, day in enumerate(days):
        day_date = week_start + timedelta(days=i)
        sessions = template.get(day)

        if sessions == "RACE":
            rows.append({"week":week_num,"phase":phase,"date":str(day_date),"day":day,
                         "sport":"race","type":"IRONMAN 70.3 RACE DAY",
                         "duration_min":270,"zone":"Race",
                         "description":"1.9km swim | 90km bike | 21.1km run. Trust the process.",
                         "week_focus":focus})
            continue

        if sessions is None:
            rows.append({"week":week_num,"phase":phase,"date":str(day_date),"day":day,
                         "sport":"rest","type":"Rest / Recovery","duration_min":0,"zone":"-",
                         "description":"Full rest or gentle walk. Sleep and nutrition are training.",
                         "week_focus":focus})
            continue

        for s in sessions:
            # Apply both phase factor and volume scale
            # Taper weeks are NOT scaled up by volume (keep taper light)
            if phase in ("Taper", "B-Race"):
                adj = round(s["min"] * phase_factor)
            else:
                adj = round(s["min"] * phase_factor * VOLUME_SCALE)

            rows.append({"week":week_num,"phase":phase,"date":str(day_date),"day":day,
                         "sport":s["sport"],"type":s["type"],"duration_min":adj,
                         "zone":s["zone"],"description":s["desc"],"week_focus":focus})
    return rows


def main():
    console.print(Panel.fit(
        "[bold cyan]14-Week Ironman 70.3 Training Plan[/bold cyan]\n"
        f"Matt Fitzgerald 80/20 Method  |  Volume: [yellow]{VOLUME_PROFILE.upper()}[/yellow] ({VOLUME_SCALE}x scale)\n"
        f"B-Race: Half Marathon {B_RACE}  |  A-Race: 70.3 {A_RACE}",
        border_style="blue"
    ))

    plan_start = TODAY - timedelta(days=TODAY.weekday())
    all_sessions = []

    for week_num, phase, phase_factor, focus in PHASES:
        week_start = plan_start + timedelta(weeks=week_num - 1)
        all_sessions.extend(build_week(week_num, phase, phase_factor, focus, week_start))

    df = pd.DataFrame(all_sessions)

    # Save
    with open(DATA_DIR / "training_plan_14weeks.json", "w") as f:
        json.dump(all_sessions, f, indent=2, default=str)
    df.to_csv(DATA_DIR / "training_plan_14weeks.csv", index=False)

    # Summary table
    t = Table(title=f"14-Week Plan ({VOLUME_PROFILE} volume profile)", style="cyan", show_lines=True)
    for col in ["Wk","Phase","Dates","Hours","Key Focus"]:
        t.add_column(col)

    colors = {"Base":"blue","Build":"yellow","Peak":"red","Taper":"green","B-Race":"magenta"}
    for week_num, phase, phase_factor, focus in PHASES:
        wdf = df[df["week"] == week_num]
        hrs  = round(wdf["duration_min"].sum() / 60, 1)
        d0   = wdf["date"].min(); d1 = wdf["date"].max()
        c    = colors.get(phase, "white")
        t.add_row(str(week_num), f"[{c}]{phase}[/{c}]",
                  f"{d0} to {d1}", f"[yellow]{hrs}h[/yellow]", focus)

    console.print(t)

    peak_week = df[df["week"].isin([10,11])].groupby("week")["duration_min"].sum().max()
    console.print(f"\n  [bold]Peak week volume:[/bold] [yellow]{round(peak_week/60,1)}h[/yellow]")
    console.print(f"  [green]Plan saved to ~/Documents/training_data/data/[/green]")
    console.print(f"\n[bold cyan]Next:[/bold cyan] Run [yellow]python3 dashboard_generator.py[/yellow]\n")


if __name__ == "__main__":
    main()
