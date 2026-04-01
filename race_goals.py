#!/usr/bin/env python3
"""
IRONMAN 70.3 Training System — Race Goals & Pace Calculator
Stores target race times and derives training zone paces for each sport.
Science base: Matt Fitzgerald 80/20 Triathlon pace zones.
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
    "half_marathon": {
        "name":         "Half Marathon",
        "date":         "2026-05-24",
        "type":         "B",
        "distance_km":  21.1,
        "target_min":   int(os.getenv("HM_TARGET_MIN", 110)),   # 1:50
    },
    "im703_swim": {
        "name":         "Ironman 70.3 — Swim",
        "date":         "2026-06-28",
        "type":         "A",
        "distance_km":  1.9,
        "target_min":   int(os.getenv("IM703_SWIM_MIN", 32)),   # 32 min
    },
    "im703_bike": {
        "name":         "Ironman 70.3 — Bike",
        "date":         "2026-06-28",
        "type":         "A",
        "distance_km":  90.0,
        "target_min":   int(os.getenv("IM703_BIKE_MIN", 180)),  # 3:00
    },
    "im703_run": {
        "name":         "Ironman 70.3 — Run",
        "date":         "2026-06-28",
        "type":         "A",
        "distance_km":  21.1,
        "target_min":   int(os.getenv("IM703_RUN_MIN", 110)),   # 1:50
    },
}


# ── Pace formatting helpers ───────────────────────────────────

def fmt_pace(min_per_km: float) -> str:
    """Format decimal min/km as M:SS/km"""
    m = int(min_per_km)
    s = int(round((min_per_km - m) * 60))
    if s == 60:
        m += 1; s = 0
    return f"{m}:{s:02d}/km"

def fmt_pace_100m(min_per_100m: float) -> str:
    """Format decimal min/100m as M:SS/100m"""
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


# ── Zone pace calculator ──────────────────────────────────────
# Fitzgerald 80/20 zone multipliers (pace: higher = slower)
# Zone 1: very easy recovery
# Zone 2: easy aerobic (the 80%)
# Zone 3: tempo / race pace feel
# Zone 4: threshold / race pace
# Zone 5: VO2max

RUN_ZONE_MULTIPLIERS = {
    "zone1": 1.30,   # 30% slower than race pace
    "zone2": 1.22,   # 22% slower
    "zone3": 1.08,   # 8% slower (tempo)
    "zone4": 1.02,   # 2% slower (near race pace)
    "zone5": 0.96,   # faster than race pace (VO2max)
}

SWIM_ZONE_MULTIPLIERS = {
    "zone1": 1.35,
    "zone2": 1.25,
    "zone3": 1.10,
    "zone4": 1.03,
    "zone5": 0.97,
}

# For bike: inverse (speed, not pace — higher = faster)
BIKE_ZONE_SPEED_MULTIPLIERS = {
    "zone1": 0.75,
    "zone2": 0.83,
    "zone3": 0.92,
    "zone4": 0.98,
    "zone5": 1.05,
}


def compute_run_zones(race_pace_min_km: float) -> dict:
    return {
        "race_pace":    fmt_pace(race_pace_min_km),
        "zone1":        fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone1"]),
        "zone2":        fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone2"]),
        "zone3":        fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone3"]),
        "zone4":        fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone4"]),
        "zone5":        fmt_pace(race_pace_min_km * RUN_ZONE_MULTIPLIERS["zone5"]),
        "race_pace_raw": round(race_pace_min_km, 3),
    }

def compute_swim_zones(race_pace_min_100m: float) -> dict:
    return {
        "race_pace":    fmt_pace_100m(race_pace_min_100m),
        "zone1":        fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone1"]),
        "zone2":        fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone2"]),
        "zone3":        fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone3"]),
        "zone4":        fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone4"]),
        "zone5":        fmt_pace_100m(race_pace_min_100m * SWIM_ZONE_MULTIPLIERS["zone5"]),
        "race_pace_raw": round(race_pace_min_100m, 3),
    }

def compute_bike_zones(race_speed_kmh: float) -> dict:
    return {
        "race_speed":   fmt_speed(race_speed_kmh),
        "zone1":        fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone1"]),
        "zone2":        fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone2"]),
        "zone3":        fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone3"]),
        "zone4":        fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone4"]),
        "zone5":        fmt_speed(race_speed_kmh * BIKE_ZONE_SPEED_MULTIPLIERS["zone5"]),
        "race_speed_raw": round(race_speed_kmh, 2),
    }


def build_goals() -> dict:
    hm   = GOALS["half_marathon"]
    swim = GOALS["im703_swim"]
    bike = GOALS["im703_bike"]
    run  = GOALS["im703_run"]

    # Race paces
    hm_pace_km       = hm["target_min"]   / hm["distance_km"]
    swim_pace_100m   = swim["target_min"] / (swim["distance_km"] * 10)  # /100m
    bike_speed_kmh   = bike["distance_km"] / (bike["target_min"] / 60)
    run_pace_km      = run["target_min"]  / run["distance_km"]

    # Projected 70.3 total time (swim + bike + run + ~10min transitions)
    im703_total = swim["target_min"] + bike["target_min"] + run["target_min"] + 10

    goals = {
        "half_marathon": {
            "name":        hm["name"],
            "date":        hm["date"],
            "type":        hm["type"],
            "target_time": fmt_time(hm["target_min"]),
            "target_min":  hm["target_min"],
            "distance":    f"{hm['distance_km']}km",
            "race_pace":   fmt_pace(hm_pace_km),
            "zones":       compute_run_zones(hm_pace_km),
            "key_sessions": {
                "easy_run":   f"Zone 2 — {fmt_pace(hm_pace_km * 1.22)} (conversational)",
                "tempo_run":  f"Zone 3 — {fmt_pace(hm_pace_km * 1.08)} (comfortably hard)",
                "race_pace":  f"Zone 4 — {fmt_pace(hm_pace_km * 1.02)} (race effort)",
                "long_run":   f"Zone 2 — {fmt_pace(hm_pace_km * 1.25)} (never breathless)",
            }
        },
        "im703": {
            "name":          "Ironman 70.3",
            "date":          bike["date"],
            "type":          bike["type"],
            "projected_total": fmt_time(im703_total),
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
                }
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
                }
            },
            "run": {
                "target_time": fmt_time(run["target_min"]),
                "target_min":  run["target_min"],
                "distance":    "21.1km",
                "race_pace":   fmt_pace(run_pace_km),
                "zones":       compute_run_zones(run_pace_km),
                "key_sessions": {
                    "easy_run":   f"Zone 2 — {fmt_pace(run_pace_km * 1.22)} (off-bike legs)",
                    "tempo_run":  f"Zone 3 — {fmt_pace(run_pace_km * 1.08)}",
                    "race_pace":  f"Zone 4 — {fmt_pace(run_pace_km * 1.02)}",
                    "brick_run":  f"Zone 2-3 — {fmt_pace(run_pace_km * 1.15)} (post-bike)",
                }
            }
        }
    }

    return goals


def main():
    print("\n🎯 Computing race goals and training paces...")

    goals = build_goals()

    out = DATA_DIR / "race_goals.json"
    with open(out, "w") as f:
        json.dump(goals, f, indent=2)

    hm   = goals["half_marathon"]
    im   = goals["im703"]

    print(f"\n  Half Marathon — {hm['date']}")
    print(f"    Target:     {hm['target_time']}")
    print(f"    Race pace:  {hm['race_pace']}")
    print(f"    Zone 2:     {hm['zones']['zone2']}")
    print(f"    Zone 3:     {hm['zones']['zone3']}")

    print(f"\n  Ironman 70.3 — {im['date']} (projected {im['projected_total']})")
    print(f"    Swim {im['swim']['target_time']} @ {im['swim']['race_pace']}")
    print(f"    Bike {im['bike']['target_time']} @ {im['bike']['race_speed']}")
    print(f"    Run  {im['run']['target_time']}  @ {im['run']['race_pace']}")

    print(f"\n  ✓ Race goals saved to {out}")


if __name__ == "__main__":
    main()
