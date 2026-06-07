#!/usr/bin/env python3
"""
Race Goals & Pace Calculator
Race 1: Ironman 70.3  — June 28, 2026
Race 2: Full Marathon — October 4, 2026

Science base: Matt Fitzgerald 80/20 pace zones
Usage: python3 race_goals.py
"""

import os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ".")).expanduser()
DATA_DIR   = OUTPUT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Race targets ──────────────────────────────────────────────
# Override via env vars if needed
GOALS = {
        "marathon": {
                    "name":        "Full Marathon",
                    "date":        "2026-10-04",
                    "type":        "B",
                    "distance_km": 42.195,
                    "target_min":  int(os.getenv("MARATHON_TARGET_MIN", 200)),  # 3:20 target
        },
        "im703_swim": {
                    "name":        "Ironman 70.3 — Swim",
                    "date":        "2026-06-28",
                    "type":        "A",
                    "distance_km": 1.9,
                    "target_min":  int(os.getenv("IM703_SWIM_MIN", 32)),
        },
        "im703_bike": {
                    "name":        "Ironman 70.3 — Bike",
                    "date":        "2026-06-28",
                    "type":        "A",
                    "distance_km": 90.0,
                    "target_min":  int(os.getenv("IM703_BIKE_MIN", 180)),
        },
        "im703_run": {
                    "name":        "Ironman 70.3 — Run",
                    "date":        "2026-06-28",
                    "type":        "A",
                    "distance_km": 21.1,
                    "target_min":  int(os.getenv("IM703_RUN_MIN", 110)),
        },
}


def fmt_pace(min_per_km: float) -> str:
        m = int(min_per_km)
        s = int(round((min_per_km - m) * 60))
        if s == 60:
                    m += 1; s = 0
                return f"{m}:{s:02d}/km"

def fmt_pace_100m(min_per_100m: float) -> str:
        m = int(min_per_100m)
    s = int(round((min_per_100m - m) * 60))
    if s == 60:
                m += 1; s = 0
            return f"{m}:{s:02d}/100m"

def fmt_speed(kmh: float) -> str:
        return f"{kmh:.1f} km/h"

def fmt_time(total_min: int) -> str:
        h = total_min // 60
    m = total_min % 60
    return f"{h}:{m:02d}"


RUN_ZONE_MULTIPLIERS = {
        "zone1": 1.30, "zone2": 1.22, "zone3": 1.08, "zone4": 1.02, "zone5": 0.96,
}
SWIM_ZONE_MULTIPLIERS = {
        "zone1": 1.35, "zone2": 1.25, "zone3": 1.10, "zone4": 1.03, "zone5": 0.97,
}
BIKE_ZONE_SPEED_MULTIPLIERS = {
        "zone1": 0.75, "zone2": 0.83, "zone3": 0.92, "zone4": 0.98, "zone5": 1.05,
}


def compute_run_zones(race_pace_min_km: float) -> dict:
        return {
            "race_pace":     fmt_pace(race_pace_min_km),
            "zone1":         fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone1"]),
            "zone2":         fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone2"]),
            "zone3":         fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone3"]),
            "zone4":         fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone4"]),
            "zone5":         fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone5"]),
            "race_pace_raw": round(race_pace_min_km, 3),
}

def compute_swim_zones(race_pace_min_100m: float) -> dict:
        return {
            "race_pace":     fmt_pace_100m(race_pace_min_100m),
            "zone1":         fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone1"]),
            "zone2":         fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone2"]),
            "zone3":         fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone3"]),
            "zone4":         fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone4"]),
            "zone5":         fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone5"]),
            "race_pace_raw": round(race_pace_min_100m, 3),
}

def compute_bike_zones(race_speed_kmh: float) -> dict:
        return {
            "race_speed":     fmt_speed(race_speed_kmh),
            "zone1":          fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone1"]),
            "zone2":          fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone2"]),
            "zone3":          fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone3"]),
            "zone4":          fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone4"]),
            "zone5":          fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone5"]),
            "race_speed_raw": round(race_speed_kmh, 2),
}


def build_goals() -> dict:
        marathon = GOALS["marathon"]
    swim     = GOALS["im703_swim"]
    bike     = GOALS["im703_bike"]
    run      = GOALS["im703_run"]

    marathon_pace_km  = marathon["target_min"] / marathon["distance_km"]
    swim_pace_100m    = swim["target_min"]  / (swim["distance_km"] * 10)
    bike_speed_kmh    = bike["distance_km"] / (bike["target_min"] / 60)
    run_pace_km       = run["target_min"]   / run["distance_km"]

    im703_total = swim["target_min"] + bike["target_min"] + run["target_min"] + 10

    goals = {
                "marathon": {
                                "name":        marathon["name"],
                                "date":        marathon["date"],
                                "type":        marathon["type"],
                                "target_time": fmt_time(marathon["target_min"]),
                                "target_min":  marathon["target_min"],
                                "distance":    f"{marathon['distance_km']}km",
                                "race_pace":   fmt_pace(marathon_pace_km),
                                "zones":       compute_run_zones(marathon_pace_km),
                                "key_sessions": {
                                                    "easy_run":      f"Zone 2 — {fmt_pace(marathon_pace_km * 1.22)} (conversational)",
                                                    "tempo_run":     f"Zone 3 — {fmt_pace(marathon_pace_km * 1.08)} (comfortably hard)",
                                                    "marathon_pace": f"Zone 3-4 — {fmt_pace(marathon_pace_km)} (race effort)",
                                                    "long_run":      f"Zone 2 — {fmt_pace(marathon_pace_km * 1.25)} (never breathless)",
                                },
                                "cross_training": {
                                                    "bike_easy":   "Zone 2 spin — aerobic base without run impact",
                                                    "gym_focus":   "Lower body strength: squats, lunges, hip work, calf raises",
                                                    "swim_option": "Optional easy swim — active recovery between run days",
                                },
                },
                "im703": {
                                "name":             "Ironman 70.3",
                                "date":             bike["date"],
                                "type":             bike["type"],
                                "projected_total":  fmt_time(im703_total),
                                "swim": {
                                                    "target_time": fmt_time(swim["target_min"]),
                                                    "target_min":  swim["target_min"],
                                                    "distance":    "1.9km",
                                                    "race_pace":   fmt_pace_100m(swim_pace_100m),
                                                    "zones":       compute_swim_zones(swim_pace_100m),
                                                    "key_sessions": {
                                                                            "easy_swim":  f"Zone 2 — {fmt_pace_100m(swim_pace_100m * 1.25)}",
                                                                            "tempo_swim": f"Zone 3 — {fmt_pace_100m(swim_pace_100m * 1.10)}",
                                                                            "race_pace":  f"Zone 4 — {fmt_pace_100m(swim_pace_100m * 1.03)}",
                                                    },
                                },
                                "bike": {
                                                    "target_time":  fmt_time(bike["target_min"]),
                                                    "target_min":   bike["target_min"],
                                                    "distance":     "90km",
                                                    "race_speed":   fmt_speed(bike_speed_kmh),
                                                    "zones":        compute_bike_zones(bike_speed_kmh),
                                                    "key_sessions": {
                                                                            "easy_ride":  f"Zone 2 — {fmt_speed(bike_speed_kmh * 0.83)}",
                                                                            "tempo_ride": f"Zone 3 — {fmt_speed(bike_speed_kmh * 0.92)}",
                                                                            "race_pace":  f"Zone 4 — {fmt_speed(bike_speed_kmh * 0.98)}",
                                                    },
                                },
                                "run": {
                                                    "target_time": fmt_time(run["target_min"]),
                                                    "target_min":  run["target_min"],
                                                    "distance":    "21.1km",
                                                    "race_pace":   fmt_pace(run_pace_km),
                                                    "zones":       compute_run_zones(run_pace_km),
                                                    "key_sessions": {
                                                                            "easy_run":  f"Zone 2 — {fmt_pace(run_pace_km * 1.22)} (off-bike legs)",
                                                                            "tempo_run": f"Zone 3 — {fmt_pace(run_pace_km * 1.08)}",
                                                                            "race_pace": f"Zone 4 — {fmt_pace(run_pace_km * 1.02)}",
                                                                            "brick_run": f"Zone 2-3 — {fmt_pace(run_pace_km * 1.15)} (post-bike)",
                                                    },
                                },
                },
    }
    return goals


def main():
        print("\n🎯 Computing race goals and training paces...")
    goals = build_goals()
    out = DATA_DIR / "race_goals.json"
    with open(out, "w") as f:
                json.dump(goals, f, indent=2)
            m  = goals["marathon"]
    im = goals["im703"]
    print(f"\n  Ironman 70.3 — {im['date']} (projected {im['projected_total']})")
    print(f"    Swim {im['swim']['target_time']} @ {im['swim']['race_pace']}")
    print(f"    Bike {im['bike']['target_time']} @ {im['bike']['race_speed']}")
    print(f"    Run  {im['run']['target_time']}  @ {im['run']['race_pace']}")
    print(f"\n  Full Marathon — {m['date']}")
    print(f"    Target:          {m['target_time']}")
    print(f"    Race pace:       {m['race_pace']}")
    print(f"    Zone 2 easy run: {m['zones']['zone2']}")
    print(f"    Tempo (Zone 3):  {m['zones']['zone3']}")
    print(f"    (Override target: MARATHON_TARGET_MIN env var)")
    print(f"\n  ✓ Race goals saved to {out}")


if __name__ == "__main__":
        main()
