#!/usr/bin/env python3
"""
IRONMAN 70.3 Training System — Intervals.icu Connector
Pulls HRV, sleep, resting HR, CTL/ATL, and wellness data.
Usage: python3 intervals_connector.py
"""

import os, json, requests
from pathlib import Path
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR   = Path(os.getenv("OUTPUT_DIR", ".")).expanduser()
DATA_DIR     = OUTPUT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ATHLETE_ID   = os.getenv("INTERVALS_ATHLETE_ID", "")
API_KEY      = os.getenv("INTERVALS_API_KEY", "")
BASE_URL     = "https://intervals.icu/api/v1"


def get(endpoint: str, params: dict = None) -> dict | list:
    if not ATHLETE_ID or not API_KEY:
        raise RuntimeError("INTERVALS_ATHLETE_ID and INTERVALS_API_KEY must be set.")
    r = requests.get(
        f"{BASE_URL}/{endpoint}",
        auth=("API_KEY", API_KEY),
        params=params or {},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fetch_wellness(days: int = 90) -> list:
    """Fetch wellness data (HRV, sleep, resting HR) for last N days."""
    oldest = (date.today() - timedelta(days=days)).isoformat()
    newest = date.today().isoformat()
    data = get(
        f"athlete/{ATHLETE_ID}/wellness",
        params={"oldest": oldest, "newest": newest},
    )
    return data if isinstance(data, list) else []


def fetch_activities(days: int = 90) -> list:
    """Fetch recent activities from Intervals.icu."""
    oldest = (date.today() - timedelta(days=days)).isoformat()
    newest = date.today().isoformat()
    data = get(
        f"athlete/{ATHLETE_ID}/activities",
        params={"oldest": oldest, "newest": newest},
    )
    return data if isinstance(data, list) else []


def process_wellness(raw: list) -> list:
    """Clean and normalize wellness records."""
    out = []
    for r in raw:
        sleep_hrs = round(r.get("sleepSecs", 0) / 3600, 1) if r.get("sleepSecs") else None
        out.append({
            "date":          r.get("id"),
            "hrv":           r.get("hrv"),
            "hrv_sdnn":      r.get("hrvSDNN"),
            "resting_hr":    r.get("restingHR"),
            "sleep_hrs":     sleep_hrs,
            "sleep_score":   r.get("sleepScore"),
            "sleep_quality": r.get("sleepQuality"),
            "ctl":           round(r.get("ctl", 0) or 0, 1),
            "atl":           round(r.get("atl", 0) or 0, 1),
            "tsb":           round((r.get("ctl", 0) or 0) - (r.get("atl", 0) or 0), 1),
            "ramp_rate":     round(r.get("rampRate", 0) or 0, 2),
            "weight_kg":     r.get("weight"),
            "soreness":      r.get("soreness"),
            "fatigue":       r.get("fatigue"),
            "stress":        r.get("stress"),
            "mood":          r.get("mood"),
            "motivation":    r.get("motivation"),
        })
    return sorted(out, key=lambda x: x["date"])


def compute_readiness(wellness: list) -> dict:
    """
    Compute a daily readiness score (0-100) from HRV + sleep + resting HR.
    Science base: HRV4Training methodology + Fitzgerald recovery principles.
    """
    if not wellness:
        return {}

    # Get recent baselines (last 14 days)
    recent = [w for w in wellness if w.get("hrv")][-14:]
    if not recent:
        return {}

    hrv_values  = [w["hrv"] for w in recent if w["hrv"]]
    hr_values   = [w["resting_hr"] for w in recent if w["resting_hr"]]
    sleep_vals  = [w["sleep_hrs"] for w in recent if w["sleep_hrs"]]

    hrv_baseline  = sum(hrv_values) / len(hrv_values)   if hrv_values  else None
    hr_baseline   = sum(hr_values)  / len(hr_values)    if hr_values   else None
    sleep_baseline= sum(sleep_vals) / len(sleep_vals)   if sleep_vals  else None

    readiness = []
    for w in wellness:
        score = 70  # neutral baseline
        flags = []

        # HRV contribution (40 pts)
        if w["hrv"] and hrv_baseline:
            hrv_pct = (w["hrv"] - hrv_baseline) / hrv_baseline * 100
            if hrv_pct >= 5:
                score += 20
                flags.append("HRV elevated — green light")
            elif hrv_pct >= 0:
                score += 10
            elif hrv_pct >= -5:
                score -= 5
                flags.append("HRV slightly suppressed")
            else:
                score -= 20
                flags.append("HRV suppressed — consider easy day")

        # Sleep contribution (30 pts)
        if w["sleep_hrs"]:
            if w["sleep_hrs"] >= 8:
                score += 15
            elif w["sleep_hrs"] >= 7:
                score += 8
            elif w["sleep_hrs"] >= 6:
                score -= 5
                flags.append("Short sleep")
            else:
                score -= 15
                flags.append("Very short sleep — recovery priority")

        # Resting HR contribution (20 pts)
        if w["resting_hr"] and hr_baseline:
            hr_diff = w["resting_hr"] - hr_baseline
            if hr_diff <= -2:
                score += 10
            elif hr_diff <= 2:
                score += 5
            elif hr_diff <= 5:
                score -= 5
                flags.append("Resting HR elevated")
            else:
                score -= 15
                flags.append("Resting HR significantly elevated — possible fatigue or illness")

        # TSB contribution (10 pts)
        tsb = w["tsb"]
        if tsb >= 5:
            score += 5
        elif tsb <= -20:
            score -= 10
            flags.append("High fatigue load (TSB low)")

        score = max(0, min(100, score))

        # Readiness label
        if score >= 80:
            label = "Ready to Train Hard"
            color = "#22c55e"
        elif score >= 65:
            label = "Good to Train"
            color = "#00d4ff"
        elif score >= 50:
            label = "Moderate — Consider Easy Session"
            color = "#f59e0b"
        else:
            label = "Recovery Priority"
            color = "#ef4444"

        readiness.append({
            **w,
            "readiness_score": score,
            "readiness_label": label,
            "readiness_color": color,
            "readiness_flags": flags,
            "hrv_baseline":    round(hrv_baseline, 1) if hrv_baseline else None,
            "hr_baseline":     round(hr_baseline, 1)  if hr_baseline  else None,
            "sleep_baseline":  round(sleep_baseline,1) if sleep_baseline else None,
        })

    return readiness


def get_today_readiness(readiness: list) -> dict:
    """Get today's readiness summary."""
    today = date.today().isoformat()
    for r in reversed(readiness):
        if r["date"] == today:
            return r
    # Return most recent if today not available
    return readiness[-1] if readiness else {}


def main():
    print("\n📡 Fetching Intervals.icu data...")

    if not ATHLETE_ID or not API_KEY:
        print("  ⚠ INTERVALS_ATHLETE_ID or INTERVALS_API_KEY not set — skipping")
        return

    # Fetch wellness
    print("  Fetching wellness data (HRV, sleep, resting HR)...")
    try:
        raw = fetch_wellness(days=90)
        print(f"  ✓ {len(raw)} wellness records fetched")
    except Exception as e:
        print(f"  ✗ Failed to fetch wellness: {e}")
        return

    # Process
    wellness = process_wellness(raw)
    readiness = compute_readiness(wellness)
    today = get_today_readiness(readiness)

    # Save wellness CSV
    import pandas as pd
    df = pd.DataFrame(wellness)
    df.to_csv(DATA_DIR / "wellness.csv", index=False)

    # Save readiness JSON
    with open(DATA_DIR / "readiness.json", "w") as f:
        json.dump(readiness, f, indent=2, default=str)

    # Save today's summary
    with open(DATA_DIR / "today_readiness.json", "w") as f:
        json.dump(today, f, indent=2, default=str)

    # Print summary
    if today:
        print(f"\n  Today's Readiness: {today.get('readiness_score', '—')}/100")
        print(f"  Status: {today.get('readiness_label', '—')}")
        print(f"  HRV: {today.get('hrv', '—')} (baseline: {today.get('hrv_baseline', '—')})")
        print(f"  Sleep: {today.get('sleep_hrs', '—')}h (score: {today.get('sleep_score', '—')})")
        print(f"  Resting HR: {today.get('resting_hr', '—')} bpm")
        if today.get("readiness_flags"):
            for flag in today["readiness_flags"]:
                print(f"  ⚠ {flag}")

    print(f"\n  ✓ Wellness data saved to {DATA_DIR}")


if __name__ == "__main__":
    main()
