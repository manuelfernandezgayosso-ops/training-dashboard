#!/usr/bin/env python3
"""
18-Week Dual-Race Training Plan Generator
Race 1 (A): Ironman 70.3 — June 28, 2026  (Weeks 1-4)
Race 2 (B): Full Marathon — October 4, 2026 (Weeks 7-18)

Method: Matt Fitzgerald 80/20 + Pfitzinger marathon periodization
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
DATA_DIR = OUTPUT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

A_RACE = date(2026, 6, 28)   # Ironman 70.3
M_RACE = date(2026, 10, 4)   # Full Marathon
TODAY = date.today()

VOLUME_PROFILE = os.getenv("VOLUME_PROFILE", "high")
VOLUME_SCALE = {"moderate": 1.0, "aggressive": 1.25, "high": 1.50}.get(VOLUME_PROFILE, 1.50)

PHASES = [
    (1,  "Peak",      0.85, "Final 70.3 sharpener — maintain fitness, reduce volume 15%. Key: swim/bike/run quality sessions."),
    (2,  "Taper",     0.55, "Volume drops 45%. Protect race fitness. Short sharp intervals, no new stress."),
    (3,  "Taper",     0.35, "Race week — minimal volume, stay sharp. Trust your training."),
    (4,  "70.3 Race", 0.20, "RACE WEEK — Ironman 70.3 June 28. Minimal training, race Sunday."),
    (5,  "Recovery",  0.25, "Full recovery. Walk/easy swim only. No running stress. Listen to body."),
    (6,  "Recovery",  0.45, "Easy running returns — Zone 1-2 only. Begin marathon base transition."),
    (7,  "M-Base",    0.55, "Marathon base begins — 80% easy Zone 2. Aerobic foundation build."),
    (8,  "M-Base",    0.65, "Build weekly run mileage — long run to 16km. Stay in Zone 2."),
    (9,  "M-Base",    0.75, "Long run to 19km. Strength work. No intensity above Zone 2."),
    (10, "M-Base",    0.55, "Recovery week — drop 25-30% volume. Body absorbs adaptation."),
    (11, "M-Build",   0.80, "Tempo runs begin — 20 min Zone 3. Lactate threshold development."),
    (12, "M-Build",   0.90, "Marathon pace segments — 3x10 min at 4:44/km. Weekly mileage up."),
    (13, "M-Build",   1.00, "Peak run volume — long run 26km. Race pace confidence building."),
    (14, "M-Build",   0.65, "Recovery week — consolidate fitness gains before peak block."),
    (15, "M-Peak",    1.00, "Highest marathon TSS — long run 29km with race pace miles."),
    (16, "M-Peak",    1.05, "Race simulation long run — 32km at progressive effort. Peak fitness."),
    (17, "M-Taper",   0.55, "Volume drops 45% — keep intensity. Fresh legs, sharp fitness."),
    (18, "M-Taper",   0.25, "RACE WEEK — Full Marathon October 4. Trust the process."),
]

# ── WEEKLY TEMPLATES ──────────────────────────────────────────────────────────

PEAK_70_3 = {
    "Mon": None,  # Rest
    "Tue": [
        {"sport": "Swim", "min": 45, "zone": "Z2-Z4", "type": "Quality",
         "desc": "1,800m — 400m easy, 6x100m Z4, 400m Z2 cooldown"},
        {"sport": "Run",  "min": 35, "zone": "Z2-Z3", "type": "Tempo",
         "desc": "Easy 10 min warm-up, 15 min tempo Z3 (4:44/km target), 10 min cool-down"},
    ],
    "Wed": [
        {"sport": "Bike", "min": 75, "zone": "Z2-Z4", "type": "Intervals",
         "desc": "20 min Z2 warm-up, 4x8 min Z4 @ race pace, 2 min recovery, 10 min Z2 cool-down"},
    ],
    "Thu": [
        {"sport": "Swim", "min": 40, "zone": "Z2",    "type": "Easy",
         "desc": "1,500m steady Z2 — focus on form, bilateral breathing"},
        {"sport": "Run",  "min": 30, "zone": "Z2",    "type": "Easy",
         "desc": "Easy Zone 2 run — keep HR conversational"},
    ],
    "Fri": [
        {"sport": "Bike", "min": 40, "zone": "Z2",    "type": "Easy",
         "desc": "Easy spin — flush legs, stay aerobic Z2"},
    ],
    "Sat": [
        {"sport": "Bike", "min": 90, "zone": "Z2-Z3", "type": "Long",
         "desc": "70km moderate ride — 75% Z2, 25% Z3 race effort. Brick optional."},
        {"sport": "Run",  "min": 20, "zone": "Z2",    "type": "Brick",
         "desc": "Transition run — 4km easy off the bike to practice T2 legs"},
    ],
    "Sun": [
        {"sport": "Run",  "min": 60, "zone": "Z2",    "type": "Long",
         "desc": "12-14km long run — comfortable Z2 pace, never breathless"},
    ],
}

TAPER_70_3 = {
    "Mon": None,
    "Tue": [
        {"sport": "Swim", "min": 30, "zone": "Z2-Z4", "type": "Sharp",
         "desc": "1,000m — 200m easy, 4x100m Z4, 200m cool-down. Stay sharp, cut volume."},
        {"sport": "Run",  "min": 20, "zone": "Z2-Z3", "type": "Easy",
         "desc": "Easy jog with 4x30s strides at race pace. Keep legs fresh."},
    ],
    "Wed": [
        {"sport": "Bike", "min": 45, "zone": "Z2-Z3", "type": "Race Prep",
         "desc": "Comfortable Z2 spin with 3x5 min at race effort. Shake out the legs."},
    ],
    "Thu": [
        {"sport": "Swim", "min": 25, "zone": "Z2",    "type": "Easy",
         "desc": "800m easy — form focus only. No intensity."},
    ],
    "Fri": [
        {"sport": "Run",  "min": 15, "zone": "Z2",    "type": "Shakeout",
         "desc": "Short easy 3km shakeout — keep legs loose, no effort"},
        {"sport": "Bike", "min": 20, "zone": "Z1-Z2", "type": "Shakeout",
         "desc": "10 min easy spin — just to move. Check equipment."},
    ],
    "Sat": None,  # Pre-race rest
    "Sun": [
        {"sport": "Race", "min": 322, "zone": "Race",  "type": "A-Race",
         "desc": "IRONMAN 70.3 — Race Day! Swim 1.9km / Bike 90km / Run 21.1km"},
    ],
}

RECOVERY = {
    "Mon": None,
    "Tue": [
        {"sport": "Walk/Swim", "min": 30, "zone": "Z1", "type": "Active Recovery",
         "desc": "Easy walk or gentle swim — no running stress, flush the legs"},
    ],
    "Wed": [
        {"sport": "Bike",  "min": 40, "zone": "Z1-Z2", "type": "Easy Spin",
         "desc": "Very easy spin — cadence 90+, HR under 130. Active recovery only."},
    ],
    "Thu": [
        {"sport": "Swim",  "min": 30, "zone": "Z1-Z2", "type": "Easy",
         "desc": "1,000m easy swim — no intensity. Full body recovery."},
    ],
    "Fri": None,
    "Sat": [
        {"sport": "Run",   "min": 35, "zone": "Z1-Z2", "type": "Easy Return",
         "desc": "First easy run back — stop if anything hurts. 5-6km maximum."},
    ],
    "Sun": [
        {"sport": "Bike",  "min": 60, "zone": "Z2",    "type": "Aerobic",
         "desc": "Moderate aerobic ride — rebuild base, enjoy the miles"},
    ],
}

MARATHON_BASE = {
    "Mon": None,
    "Tue": [
        {"sport": "Run",  "min": 50, "zone": "Z2",    "type": "Easy",
         "desc": "Easy Zone 2 — conversational pace, build aerobic base"},
        {"sport": "Gym",  "min": 30, "zone": "N/A",   "type": "Strength",
         "desc": "Lower body: squats 3x10, lunges 3x12, hip bridges 3x15, calf raises 3x20"},
    ],
    "Wed": [
        {"sport": "Bike", "min": 60, "zone": "Z2",    "type": "Cross-Train",
         "desc": "Easy aerobic ride — maintain bike fitness without run impact"},
    ],
    "Thu": [
        {"sport": "Run",  "min": 45, "zone": "Z2",    "type": "Easy",
         "desc": "Zone 2 easy run — HR under 145, no pressure"},
    ],
    "Fri": [
        {"sport": "Swim", "min": 40, "zone": "Z1-Z2", "type": "Active Recovery",
         "desc": "Easy swim — loosen up for Saturday long run"},
    ],
    "Sat": [
        {"sport": "Run",  "min": 90, "zone": "Z2",    "type": "Long",
         "desc": "Long run — Zone 2 throughout, walk breaks fine, finish strong not fast"},
    ],
    "Sun": [
        {"sport": "Bike", "min": 75, "zone": "Z2",    "type": "Easy",
         "desc": "Easy Sunday ride — aerobic cross-training, active recovery from long run"},
    ],
}

MARATHON_BUILD = {
    "Mon": None,
    "Tue": [
        {"sport": "Run",  "min": 55, "zone": "Z2-Z3", "type": "Tempo",
         "desc": "Warm-up 15 min Z2, 3x12 min at 3:20 marathon pace (4:44/km, Zone 3), cool-down 10 min"},
        {"sport": "Gym",  "min": 30, "zone": "N/A",   "type": "Strength",
         "desc": "Power work: single-leg squats 3x8, deadlifts 3x8, box jumps 3x8, hip flexor work"},
    ],
    "Wed": [
        {"sport": "Bike", "min": 60, "zone": "Z2",    "type": "Cross-Train",
         "desc": "Aerobic bike — active recovery, maintain cardio without run stress"},
    ],
    "Thu": [
        {"sport": "Run",  "min": 50, "zone": "Z2-Z3", "type": "Medium-Long",
         "desc": "Medium long run — 12-14km, 80% Z2 with last 4km at marathon pace (4:44/km)"},
    ],
    "Fri": [
        {"sport": "Swim", "min": 35, "zone": "Z1-Z2", "type": "Recovery",
         "desc": "Easy swim — shake out pre-long run, no intensity"},
    ],
    "Sat": [
        {"sport": "Run",  "min": 110, "zone": "Z2-Z3", "type": "Long",
         "desc": "Long run — first 18km Zone 2 easy, final 6km progressive to marathon pace"},
    ],
    "Sun": [
        {"sport": "Bike", "min": 75, "zone": "Z2",    "type": "Recovery Ride",
         "desc": "Easy recovery spin — flush legs post long run, stay aerobic"},
    ],
}

MARATHON_PEAK = {
    "Mon": None,
    "Tue": [
        {"sport": "Run",  "min": 65, "zone": "Z2-Z4", "type": "Workout",
         "desc": "Warm-up 15 min, 2x20 min at marathon pace (4:44/km), 3 min jog recovery, cool-down 10 min"},
        {"sport": "Gym",  "min": 25, "zone": "N/A",   "type": "Maintenance",
         "desc": "Maintenance strength — lighter loads, focus on activation: glutes, hips, single-leg work"},
    ],
    "Wed": [
        {"sport": "Bike", "min": 60, "zone": "Z2",    "type": "Cross-Train",
         "desc": "Easy bike — active recovery, protect legs for long run"},
    ],
    "Thu": [
        {"sport": "Run",  "min": 60, "zone": "Z2-Z3", "type": "Medium-Long",
         "desc": "Medium-long run — 14-16km, progressive last 5km approaching marathon pace"},
    ],
    "Fri": [
        {"sport": "Swim", "min": 35, "zone": "Z1-Z2", "type": "Easy",
         "desc": "Very easy swim — recovery before peak long run day"},
    ],
    "Sat": [
        {"sport": "Run",  "min": 150, "zone": "Z2-Z3", "type": "Peak Long",
         "desc": "Target 30-32km. First 22km easy Zone 2. Final 10km at 3:20 race pace (4:44/km)."},
    ],
    "Sun": [
        {"sport": "Bike", "min": 60, "zone": "Z1-Z2", "type": "Easy Recovery",
         "desc": "Gentle spin — flush legs after peak long run. Low cadence OK."},
    ],
}

MARATHON_TAPER = {
    "Mon": None,
    "Tue": [
        {"sport": "Run",  "min": 45, "zone": "Z2-Z3", "type": "Tempo",
         "desc": "Warm-up 10 min, 2x10 min at marathon pace (4:44/km), cool-down 10 min. Maintain sharpness."},
    ],
    "Wed": [
        {"sport": "Bike", "min": 40, "zone": "Z2",    "type": "Easy",
         "desc": "Easy spin — keep legs fresh, nothing hard"},
    ],
    "Thu": [
        {"sport": "Run",  "min": 35, "zone": "Z2",    "type": "Easy",
         "desc": "Easy run — feel light, relaxed. Trust your fitness."},
    ],
    "Fri": [
        {"sport": "Swim", "min": 25, "zone": "Z1-Z2", "type": "Easy",
         "desc": "Short easy swim — just to move, nothing taxing"},
    ],
    "Sat": [
        {"sport": "Run",  "min": 30, "zone": "Z1-Z2", "type": "Shakeout",
         "desc": "Pre-race shakeout — easy 5-6km, 4x20s strides, stay loose"},
    ],
    "Sun": [
        {"sport": "Race", "min": 200, "zone": "Race",  "type": "B-Race",
         "desc": "FULL MARATHON — Race Day! 42.2km target 3:20. Trust the training."},
    ],
}


def build_week(week_num, phase, phase_factor, focus, week_start):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    rows = []

    if phase == "Peak":
        template = PEAK_70_3
    elif phase in ("Taper", "70.3 Race"):
        template = TAPER_70_3
    elif phase == "Recovery":
        template = RECOVERY
    elif phase == "M-Base":
        template = MARATHON_BASE
    elif phase == "M-Build":
        template = MARATHON_BUILD
    elif phase == "M-Peak":
        template = MARATHON_PEAK
    elif phase in ("M-Taper",):
        template = MARATHON_TAPER
    else:
        template = MARATHON_BASE

    for i, day in enumerate(days):
        day_date = week_start + timedelta(days=i)

        # Special case: actual race days override template
        if phase == "70.3 Race" and day == "Sun":
            rows.append({
                "week": week_num, "phase": phase, "focus": focus,
                "day": day, "date": day_date.strftime("%Y-%m-%d"),
                "sport": "Race", "duration_min": 322, "zone": "Race",
                "session_type": "A-Race",
                "description": "🏁 IRONMAN 70.3 — Race Day! Swim 1.9km / Bike 90km / Run 21.1km",
            })
            continue

        if phase == "M-Taper" and week_num == 18 and day == "Sun":
            rows.append({
                "week": week_num, "phase": phase, "focus": focus,
                "day": day, "date": day_date.strftime("%Y-%m-%d"),
                "sport": "Race", "duration_min": 200, "zone": "Race",
                "session_type": "B-Race",
                "description": "🏃 FULL MARATHON — Race Day! 42.2km target 3:20. You've got this!",
            })
            continue

        sessions = template.get(day)
        if sessions is None:
            rows.append({
                "week": week_num, "phase": phase, "focus": focus,
                "day": day, "date": day_date.strftime("%Y-%m-%d"),
                "sport": "Rest", "duration_min": 0, "zone": "N/A",
                "session_type": "Rest",
                "description": "Complete rest — recovery is where adaptation happens",
            })
            continue

        for s in sessions:
            # Taper/recovery/race weeks: no volume scaling
            if phase in ("Taper", "70.3 Race", "Recovery", "M-Taper"):
                adj = round(s["min"] * phase_factor)
            else:
                adj = round(s["min"] * phase_factor * VOLUME_SCALE)

            rows.append({
                "week": week_num, "phase": phase, "focus": focus,
                "day": day, "date": day_date.strftime("%Y-%m-%d"),
                "sport": s["sport"], "duration_min": adj, "zone": s["zone"],
                "session_type": s["type"],
                "description": s["desc"],
            })

    return rows


def main():
    plan_start = TODAY - timedelta(days=TODAY.weekday())  # Monday of current week
    console.print(Panel(
        f"[bold cyan]18-Week Dual-Race Training Plan[/bold cyan]\n"
        f"Plan start: [yellow]{plan_start}[/yellow] (this Monday)\n"
        f"A-Race: [green]Ironman 70.3 — {A_RACE}[/green]\n"
        f"B-Race: [blue]Full Marathon — {M_RACE}[/blue]\n"
        f"Volume profile: [magenta]{VOLUME_PROFILE}[/magenta] ({VOLUME_SCALE}x scale)",
        title="Training Plan Generator",
    ))

    all_rows = []
    for week_num, phase, factor, focus in PHASES:
        week_start = plan_start + timedelta(weeks=week_num - 1)
        rows = build_week(week_num, phase, factor, focus, week_start)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    total_sessions = len(df[df["sport"] != "Rest"])
    total_hours = df["duration_min"].sum() / 60

    console.print(f"\n[green]✓ Generated {len(PHASES)} weeks, {total_sessions} sessions, "
                  f"{total_hours:.1f} total training hours[/green]")

    csv_path = DATA_DIR / "training_plan_14weeks.csv"
    json_path = DATA_DIR / "training_plan_14weeks.json"
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)
    console.print(f"[green]✓ Saved to {csv_path}[/green]")
    console.print(f"[green]✓ Saved to {json_path}[/green]")

    # Summary table
    table = Table(title="Weekly Summary")
    table.add_column("Wk", style="cyan")
    table.add_column("Phase", style="magenta")
    table.add_column("Sessions")
    table.add_column("Hours", style="green")
    table.add_column("Focus")

    for week_num, phase, factor, focus in PHASES:
        week_rows = [r for r in all_rows if r["week"] == week_num]
        sessions = len([r for r in week_rows if r["sport"] != "Rest"])
        hours = sum(r["duration_min"] for r in week_rows) / 60
        table.add_row(str(week_num), phase, str(sessions), f"{hours:.1f}h", focus[:60])

    console.print(table)


if __name__ == "__main__":
    main()
