#!/usr/bin/env python3
"""
Training Plan Generator - 18-Week Dual-Race Plan
Race 1: Ironman 70.3  - June 28, 2026
Race 2: Full Marathon - October 4, 2026

Structure:
  Weeks 1-4   : 70.3 Peak -> Taper -> Race (Jun 28)
    Weeks 5-6   : Post-triathlon recovery
      Weeks 7-18  : Marathon build (run focus, bike/gym cross-training) -> Race (Oct 4)

      Science base: Matt Fitzgerald 80/20 method
                    Pfitzinger marathon periodization
                    Volume scale: set via VOLUME_PROFILE env var
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

A_RACE  = date(2026, 6, 28)   # Ironman 70.3
M_RACE  = date(2026, 10, 4)   # Full Marathon
TODAY   = date.today()

VOLUME_PROFILE = os.getenv("VOLUME_PROFILE", "high")
VOLUME_SCALE   = {"moderate": 1.0, "aggressive": 1.25, "high": 1.50}.get(VOLUME_PROFILE, 1.50)

PHASES = [
        (1,  "Peak",      0.85, "Final 70.3 sharpener. Swim + bike at race power. Short race-pace run."),
        (2,  "Taper",     0.55, "Volume drops 45%. Two quality sessions. Get fresh."),
        (3,  "Taper",     0.35, "Race week. Short activations only. Prep gear, sleep, nutrition."),
        (4,  "70.3 Race", 0.20, "RACE WEEK - Ironman 70.3 June 28. Light movement until race day."),
        (5,  "Recovery",  0.25, "Full recovery. Walk, easy swim, gentle spin. Zero intensity."),
        (6,  "Recovery",  0.45, "Easy running returns. HR Zone 1-2 only. Assess and absorb."),
        (7,  "M-Base",    0.55, "Marathon base begins. Running focus. Bike + gym as cross-training."),
        (8,  "M-Base",    0.65, "Build weekly run mileage. Zone 2 long run to 16km."),
        (9,  "M-Base",    0.75, "Long run to 19km. Gym 2x/week for leg strength and injury prevention."),
        (10, "M-Base",    0.55, "Recovery week. Adapt and absorb before building intensity."),
        (11, "M-Build",   0.80, "Tempo runs begin. Long run to 22km. Bike 1x/week cross-training."),
        (12, "M-Build",   0.90, "Marathon pace segments in long run. Weekly mileage peaks."),
        (13, "M-Build",   1.00, "Peak run volume. Long run 26km. Gym + bike maintain aerobic base."),
        (14, "M-Build",   0.65, "Recovery week. Flush the legs before final peak block."),
        (15, "M-Peak",    1.00, "Highest marathon TSS. Long run 28-30km."),
        (16, "M-Peak",    1.05, "Race simulation long run with marathon pace final 10km."),
        (17, "M-Taper",   0.55, "Volume drops 45%. Keep 2 quality runs. Legs freshen."),
        (18, "M-Taper",   0.25, "RACE WEEK - Full Marathon October 4. Shakeouts only."),
]

PEAK_70_3 = {
        "Mon": [{"sport":"swim", "min":50, "zone":"Zone 2-3", "type":"Race Prep Swim",
                              "desc":"2,000m. Include 4x100m at race pace (Z3-4). Get comfortable at 70.3 effort."}],
        "Tue": [{"sport":"run",  "min":55, "zone":"Zone 3-4", "type":"Race Pace Run",
                              "desc":"10 min Z1, 4x10 min at 70.3 run target pace (Z2-3), jog 90 sec between, 5 min cool."}],
        "Wed": [{"sport":"swim", "min":45, "zone":"Zone 2",   "type":"Aerobic Swim",
                              "desc":"1,800m easy. Drill focus + build sets. Keep it fluid, not hard."},
                            {"sport":"bike", "min":75, "zone":"Zone 3",   "type":"Bike Intervals",
                                          "desc":"15 min warm-up, 3x12 min Zone 3 at race power, 3 min easy between, 10 min cool."}],
        "Thu": [{"sport":"run",  "min":35, "zone":"Zone 1",   "type":"Recovery Run",
                              "desc":"Very easy. Flush the legs from Tuesday. HR Zone 1 only."}],
        "Fri": None,
        "Sat": [{"sport":"swim", "min":55, "zone":"Zone 2-3", "type":"Open Water Sim Swim",
                              "desc":"2,500-3,000m. Simulate 70.3 swim. Sighting every 10 strokes. No walls."},
                            {"sport":"bike", "min":150,"zone":"Zone 2-3", "type":"Race Simulation Brick",
                                          "desc":"2h30 at 70.3 target power/HR, T2 transition, 30-min run at race pace. Full nutrition plan."}],
        "Sun": [{"sport":"run",  "min":65, "zone":"Zone 2",   "type":"Long Run",
                              "desc":"Easy aerobic long run. Tired legs from Saturday are intentional. Mental toughness."}],
}

TAPER_70_3 = {
        "Mon": [{"sport":"swim", "min":30, "zone":"Zone 2",   "type":"Easy Swim",
                              "desc":"1,200m easy. Keep the feel for water without taxing the body."}],
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
                              "desc":"Easy 400m. Feel the water. Zero hard efforts."},
                            {"sport":"bike", "min":15, "zone":"Zone 1",   "type":"Bike Check",
                                          "desc":"15 min easy spin. Check bike and transitions. Lay out gear tonight."}],
        "Sun": None,
}

RECOVERY = {
        "Mon": None,
        "Tue": [{"sport":"walk/swim", "min":30, "zone":"Zone 1", "type":"Easy Movement",
                              "desc":"Walk or easy swim. Flush the legs. Zero running or hard effort."}],
        "Wed": [{"sport":"bike", "min":40, "zone":"Zone 1", "type":"Easy Spin",
                              "desc":"Very easy spin. Active recovery only. No power targets."}],
        "Thu": None,
        "Fri": [{"sport":"swim", "min":30, "zone":"Zone 1", "type":"Easy Swim",
                              "desc":"1,000m easy. Loosen the shoulders and enjoy the water."}],
        "Sat": [{"sport":"run", "min":25, "zone":"Zone 1", "type":"Easy Jog",
                              "desc":"First easy jog post-race. If legs feel heavy, walk. HR Zone 1 only."}],
        "Sun": None,
}

MARATHON_BASE = {
        "Mon": [{"sport":"gym", "min":50, "zone":"-", "type":"Strength Session",
                              "desc":"Lower body: squats, lunges, single-leg RDL, calf raises, hip work. 2-3 sets x 10-12 reps. A 3:20 marathon requires injury-free legs."}],
        "Tue": [{"sport":"run", "min":55, "zone":"Zone 2", "type":"Easy Run",
                              "desc":"Conversational pace ~5:45-6:00/km. The 80% of 80/20 - base miles build the engine for 3:20."}],
        "Wed": [{"sport":"bike", "min":60, "zone":"Zone 2", "type":"Cross-Training Ride",
                              "desc":"Easy aerobic spin. Maintains cardiovascular base without leg fatigue. 90+ RPM cadence."}],
        "Thu": [{"sport":"run", "min":50, "zone":"Zone 2", "type":"Easy Run",
                              "desc":"Easy Zone 2 ~5:45-6:00/km. Flush from Tuesday. No intensity - save it for Saturday."}],
        "Fri": None,
        "Sat": [{"sport":"run", "min":90, "zone":"Zone 2", "type":"Long Run",
                              "desc":"Easy long run building to 18-20km. Eat and drink every 20 min - race nutrition is a skill."}],
        "Sun": [{"sport":"run", "min":30, "zone":"Zone 1", "type":"Recovery Run",
                              "desc":"Very easy 30 min. Active recovery after the long run. Walk breaks are fine."}],
}

MARATHON_BUILD = {
        "Mon": [{"sport":"gym", "min":50, "zone":"-", "type":"Strength Session",
                              "desc":"Bulgarian split squats, step-ups, hip thrusts, planks, dead bugs. Protect hip flexors and knees for high mileage weeks."}],
        "Tue": [{"sport":"run", "min":60, "zone":"Zone 3-4", "type":"Tempo Run",
                              "desc":"10 min Z1 warm-up, 3x12 min at 3:20 marathon pace (4:44/km, Zone 3), 90 sec easy between, 10 min cool-down."}],
        "Wed": [{"sport":"bike", "min":75, "zone":"Zone 2-3", "type":"Cross-Training Ride",
                              "desc":"Zone 2 base + 2x10 min at Zone 3. Keeps aerobic base without adding run impact to heavy legs."}],
        "Thu": [{"sport":"run", "min":50, "zone":"Zone 2", "type":"Easy Run",
                              "desc":"Easy recovery run after Tuesday's tempo. HR Zone 2. Quality only lands if recovery is real."}],
        "Fri": None,
        "Sat": [{"sport":"run", "min":110, "zone":"Zone 2-3", "type":"Long Run",
                              "desc":"Build to 22-26km. First 80% easy Zone 2. Final 20% at 3:20 marathon pace (4:44/km)."}],
        "Sun": [{"sport":"run", "min":35, "zone":"Zone 1", "type":"Recovery Run",
                              "desc":"Very easy 35 min. Flush Sunday legs. Walk/run is fine."}],
}

MARATHON_PEAK = {
        "Mon": [{"sport":"gym", "min":40, "zone":"-", "type":"Maintenance Strength",
                              "desc":"Squats, hip work, core only. Keep strength without pre-fatigue before peak long runs."}],
        "Tue": [{"sport":"run", "min":65, "zone":"Zone 3-4", "type":"Marathon Pace Run",
                              "desc":"15 min easy, 4x15 min at 3:20 goal pace (4:44/km), 90 sec easy between, 10 min cool."}],
        "Wed": [{"sport":"bike", "min":60, "zone":"Zone 2", "type":"Easy Cross-Train",
                              "desc":"Easy spin. Maintain aerobic base without accumulating run fatigue before Saturday."}],
        "Thu": [{"sport":"run", "min":45, "zone":"Zone 2", "type":"Easy Run",
                              "desc":"Easy Zone 2 ~5:45/km. Legs should feel good after Wednesday's easy bike."}],
        "Fri": None,
        "Sat": [{"sport":"run", "min":125, "zone":"Zone 2-3", "type":"Long Run - Race Sim",
                              "desc":"Target 30-32km. First 22km easy Zone 2. Final 10km at 3:20 race pace (4:44/km). Full nutrition protocol."}],
        "Sun": [{"sport":"run", "min":35, "zone":"Zone 1", "type":"Recovery Run",
                              "desc":"Very easy 35 min. You earned it."}],
}

MARATHON_TAPER = {
        "Mon": None,
        "Tue": [{"sport":"run", "min":40, "zone":"Zone 2-3", "type":"Sharpener Run",
                              "desc":"20 min easy + 4x1 min at marathon pace, 2 min easy jog. Keep the legs quick."}],
        "Wed": [{"sport":"bike", "min":40, "zone":"Zone 2", "type":"Easy Cross-Train",
                              "desc":"Easy spin. Maintain feel without adding fatigue."}],
        "Thu": [{"sport":"run", "min":30, "zone":"Zone 2", "type":"Easy Run",
                              "desc":"Casual 30 min. Just stay loose."}],
        "Fri": [{"sport":"gym", "min":30, "zone":"-", "type":"Light Activation",
                              "desc":"Bodyweight only: glute bridges, calf raises, lunges. Activation not fatigue."}],
        "Sat": [{"sport":"run", "min":20, "zone":"Zone 1", "type":"Shakeout",
                              "desc":"Easy 20 min with 4x20 sec race-pace strides. That's it."}],
        "Sun": None,
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
                if phase == "70.3 Race" and day == "Sun":
                                rows.append({"week": week_num, "phase": phase, "date": str(day_date), "day": day,
                                                                      "sport": "race", "type": "IRONMAN 70.3 RACE DAY", "duration_min": 270,
                                                                      "zone": "Race", "description": "1.9km swim | 90km bike | 21.1km run. Trust the process.",
                                                                      "week_focus": focus})
                                continue
                            if phase == "M-Taper" and week_num == 18 and day == "Sun":
                                            rows.append({"week": week_num, "phase": phase, "date": str(day_date), "day": day,
                                                                                  "sport": "race", "type": "FULL MARATHON RACE DAY", "duration_min": 240,
                                                                                  "zone": "Race", "description": "42.2km. Start easy. Negative split. First 30km with your legs, last 12km with your heart.",
                                                                                  "week_focus": focus})
                                            continue
                                        sessions = template.get(day)
        if sessions is None:
                        rows.append({"week": week_num, "phase": phase, "date": str(day_date), "day": day,
                                                              "sport": "rest", "type": "Rest / Recovery", "duration_min": 0, "zone": "-",
                                                              "description": "Full rest. Sleep and nutrition are training.", "week_focus": focus})
                        continue
                    for s in sessions:
                                    if phase in ("Taper", "70.3 Race", "Recovery", "M-Taper"):
                                                        adj = round(s["min"] * phase_factor)
else:
                adj = round(s["min"] * phase_factor * VOLUME_SCALE)
            rows.append({"week": week_num, "phase": phase, "date": str(day_date), "day": day,
                                                  "sport": s["sport"], "type": s["type"], "duration_min": adj,
                                                  "zone": s["zone"], "description": s["desc"], "week_focus": focus})
    return rows


def main():
        console.print(Panel.fit(
                    "[bold cyan]18-Week Dual-Race Training Plan[/bold cyan]\n"
                    f"80/20 Triathlon + Pfitzinger Marathon  |  Volume: [yellow]{VOLUME_PROFILE.upper()}[/yellow] ({VOLUME_SCALE}x scale)\n"
                    f"Race 1: [red]Ironman 70.3[/red]  {A_RACE}  ({(A_RACE - TODAY).days} days out)\n"
                    f"Race 2: [green]Full Marathon[/green] {M_RACE}  ({(M_RACE - TODAY).days} days out)",
                    border_style="blue",
        ))
    plan_start = TODAY - timedelta(days=TODAY.weekday())
    all_sessions = []
    for week_num, phase, phase_factor, focus in PHASES:
                week_start = plan_start + timedelta(weeks=week_num - 1)
        all_sessions.extend(build_week(week_num, phase, phase_factor, focus, week_start))
    df = pd.DataFrame(all_sessions)
    with open(DATA_DIR / "training_plan_14weeks.json", "w") as f:
                json.dump(all_sessions, f, indent=2, default=str)
    df.to_csv(DATA_DIR / "training_plan_14weeks.csv", index=False)
    t = Table(title=f"18-Week Plan ({VOLUME_PROFILE} volume)", style="cyan", show_lines=True)
    for col in ["Wk", "Phase", "Dates", "Hours", "Key Focus"]:
                t.add_column(col)
    colors = {"Peak": "red", "Taper": "green", "70.3 Race": "bold red",
                            "Recovery": "blue", "M-Base": "cyan", "M-Build": "yellow",
                            "M-Peak": "red", "M-Taper": "green"}
    for week_num, phase, phase_factor, focus in PHASES:
                wdf = df[df["week"] == week_num]
        hrs = round(wdf["duration_min"].sum() / 60, 1)
        d0 = wdf["date"].min(); d1 = wdf["date"].max()
        c = colors.get(phase, "white")
        t.add_row(str(week_num), f"[{c}]{phase}[/{c}]", f"{d0} -> {d1}", f"[yellow]{hrs}h[/yellow]", focus)
    console.print(t)
    peak_triathlon = df[df["phase"] == "Peak"]["duration_min"].sum()
    peak_marathon  = df[df["phase"].isin(["M-Peak"])]["duration_min"].sum() / 2
    console.print(f"\n  [bold]70.3 sharpener week:[/bold] [yellow]{round(peak_triathlon/60,1)}h[/yellow]")
    console.print(f"  [bold]Marathon peak avg:[/bold]    [yellow]{round(peak_marathon/60,1)}h/week[/yellow]")
    console.print(f"  [green]Plan saved to ~/Documents/training_data/data/[/green]")


if __name__ == "__main__":
        main()
