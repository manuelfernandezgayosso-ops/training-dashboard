#!/usr/bin/env python3
"""
IRONMAN 70.3 Training System — Strava Data Connector
Pulls 12 months of swim/bike/run data from Strava.
Usage: python3 strava_connector.py
Requires: strava_auth.py to have been run first.
"""

import os, json, time
import requests
from datetime import datetime, timedelta, date
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel

load_dotenv()
console = Console()

OUTPUT_DIR    = Path(os.getenv("OUTPUT_DIR", "~/Documents/training_data")).expanduser()
DATA_DIR      = OUTPUT_DIR / "data"
TOKEN_FILE    = OUTPUT_DIR / ".strava_token.json"
CLIENT_ID     = os.getenv("STRAVA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── 80/20 Zones (% of LTHR) ──────────────────────────────────
ZONES = {
    "Zone 1": (0.00, 0.81),
    "Zone 2": (0.81, 0.89),
    "Zone X": (0.89, 0.94),
    "Zone 3": (0.94, 1.01),
    "Zone 4": (1.01, 1.06),
    "Zone 5": (1.06, 1.15),
}
DEFAULT_LTHR = {"run": 162, "bike": 152, "swim": 148}
SPORT_MAP = {
    "Run": "run", "TrailRun": "run", "VirtualRun": "run", "Treadmill": "run",
    "Ride": "bike", "VirtualRide": "bike", "GravelRide": "bike", "MountainBikeRide": "bike",
    "Swim": "swim", "OpenWaterSwim": "swim",
}
TARGET_KM = {"run": 21.1, "bike": 90.0, "swim": 1.9}


def classify_zone(avg_hr, lthr):
    if not avg_hr or not lthr: return "Unknown"
    pct = avg_hr / lthr
    for name, (lo, hi) in ZONES.items():
        if lo <= pct < hi: return name
    return "Zone 5" if pct >= 1.15 else "Zone 1"

def estimate_tss(dur_sec, avg_hr, lthr):
    if not avg_hr or not lthr or not dur_sec: return 0.0
    return round((dur_sec * (avg_hr / lthr) ** 2) / 3600 * 100, 1)


# ── Token ─────────────────────────────────────────────────────
def get_valid_token():
    if not TOKEN_FILE.exists():
        console.print("\n[red]No Strava token found. Run: python3 strava_auth.py[/red]\n")
        return None
    with open(TOKEN_FILE) as f:
        token = json.load(f)
    if token.get("expires_at", 0) <= time.time() + 60:
        console.print("  Refreshing token...")
        r = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token", "refresh_token": token["refresh_token"],
        })
        r.raise_for_status()
        token = r.json()
        with open(TOKEN_FILE, "w") as f: json.dump(token, f, indent=2)
        console.print("  [green]Token refreshed[/green]")
    return token


# ── Fetch ─────────────────────────────────────────────────────
def fetch_activities(headers, days=365):
    after_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    all_acts, page = [], 1
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TextColumn("{task.completed} activities"), console=console) as p:
        task = p.add_task("Fetching from Strava...", total=None)
        while True:
            r = requests.get("https://www.strava.com/api/v3/athlete/activities",
                             headers=headers,
                             params={"after": after_ts, "per_page": 100, "page": page})
            if r.status_code == 429:
                console.print("  Rate limited — waiting 15s..."); time.sleep(15); continue
            r.raise_for_status()
            batch = r.json()
            if not batch: break
            all_acts.extend(batch)
            p.update(task, completed=len(all_acts))
            if len(batch) < 100: break
            page += 1
            time.sleep(0.5)
    return all_acts

def fetch_athlete(headers):
    try:
        r = requests.get("https://www.strava.com/api/v3/athlete", headers=headers)
        return r.json()
    except: return {}


# ── Process ───────────────────────────────────────────────────
def process(raw):
    records = []
    for act in raw:
        sport = SPORT_MAP.get(act.get("sport_type") or act.get("type", ""))
        if not sport: continue
        lthr     = DEFAULT_LTHR[sport]
        dur_sec  = act.get("moving_time", 0) or 0
        dist_m   = act.get("distance", 0) or 0
        avg_hr   = act.get("average_heartrate", 0) or 0
        speed    = act.get("average_speed", 0) or 0
        dist_km  = round(dist_m / 1000, 2)
        zone     = classify_zone(avg_hr, lthr)
        records.append({
            "activity_id":       act.get("id"),
            "activity_name":     act.get("name", ""),
            "sport":             sport,
            "sport_type":        act.get("sport_type") or act.get("type", ""),
            "start_time":        act.get("start_date_local", ""),
            "duration_sec":      dur_sec,
            "duration_min":      round(dur_sec / 60, 1),
            "distance_km":       dist_km,
            "avg_hr":            avg_hr,
            "max_hr":            act.get("max_heartrate", 0) or 0,
            "lthr":              lthr,
            "zone_80_20":        zone,
            "is_low_intensity":  zone in ("Zone 1", "Zone 2"),
            "tss_estimated":     estimate_tss(dur_sec, avg_hr, lthr),
            "avg_power_watts":   act.get("average_watts", 0) or 0,
            "elevation_gain_m":  act.get("total_elevation_gain", 0) or 0,
            "avg_speed_ms":      speed,
            "pace_min_per_km":   round(1000 / speed / 60, 2) if sport == "run" and speed > 0 else 0,
            "pace_min_per_100m": round(100 / speed / 60, 2) if sport == "swim" and speed > 0 else 0,
            "pct_of_race_dist":  round((dist_km / TARGET_KM[sport]) * 100, 1),
            "suffer_score":      act.get("suffer_score", 0) or 0,
        })
    df = pd.DataFrame(records)
    if not df.empty:
        df["start_time"] = pd.to_datetime(df["start_time"])
        df = df.sort_values("start_time", ascending=False).reset_index(drop=True)
    return df


# ── Fitness Trend ─────────────────────────────────────────────
def fitness_trend(df):
    if df.empty: return df
    df2 = df.copy()
    df2["date"] = pd.to_datetime(df2["start_time"], utc=True).dt.date
    daily = df2.groupby("date")["tss_estimated"].sum().reset_index()
    daily.columns = ["date", "daily_tss"]
    rng = pd.date_range(start=daily["date"].min(), end=date.today(), freq="D")
    daily = daily.set_index("date").reindex(rng.date, fill_value=0).reset_index()
    daily.columns = ["date", "daily_tss"]
    daily["CTL"] = daily["daily_tss"].ewm(span=42).mean().round(1)
    daily["ATL"] = daily["daily_tss"].ewm(span=7).mean().round(1)
    daily["TSB"] = (daily["CTL"] - daily["ATL"]).round(1)
    return daily


# ── Profile ───────────────────────────────────────────────────
def build_profile(df, athlete):
    p = {
        "generated_at": datetime.now().isoformat(),
        "athlete_name": os.getenv("ATHLETE_NAME", "Athlete"),
        "data_source":  "Strava",
        "strava_id":    athlete.get("id"),
        "b_race": {"date": os.getenv("B_RACE_DATE"), "name": os.getenv("B_RACE_NAME")},
        "a_race": {"date": os.getenv("A_RACE_DATE"), "name": os.getenv("A_RACE_NAME")},
        "weekly_volume_hours": 0,
        "sport_breakdown_pct": {},
        "zone_distribution_pct": {},
        "80_20_compliance_pct": 0,
        "estimated_ctl": 0, "estimated_atl": 0, "estimated_tsb": 0,
        "sports": {},
    }
    if df.empty: return p

    four_weeks_ago = pd.Timestamp.now(tz="UTC") - timedelta(weeks=4)
    recent = df[df["start_time"] >= four_weeks_ago]
    if not recent.empty:
        p["weekly_volume_hours"] = round(recent["duration_sec"].sum() / 3600 / 4, 1)

    sport_time = df.groupby("sport")["duration_sec"].sum()
    total_time = sport_time.sum()
    if total_time > 0:
        p["sport_breakdown_pct"] = {s: round(t/total_time*100,1) for s,t in sport_time.items()}

    zone_counts = df["zone_80_20"].value_counts()
    if len(df) > 0:
        p["zone_distribution_pct"] = {z: round(c/len(df)*100,1) for z,c in zone_counts.items()}

    p["80_20_compliance_pct"] = round(df["is_low_intensity"].mean() * 100, 1)

    for sport in ["run", "bike", "swim"]:
        sdf = df[df["sport"] == sport]
        if sdf.empty: continue
        rs = sdf[sdf["start_time"] >= pd.Timestamp.now(tz="UTC") - timedelta(weeks=4)]
        hr_vals = sdf[sdf["avg_hr"] > 0]["avg_hr"]
        p["sports"][sport] = {
            "total_activities":        len(sdf),
            "total_hours":             round(sdf["duration_sec"].sum() / 3600, 1),
            "avg_weekly_hours_recent": round(rs["duration_sec"].sum() / 3600 / 4, 1) if not rs.empty else 0,
            "avg_hr":                  round(hr_vals.mean(), 0) if not hr_vals.empty else 0,
            "estimated_lthr":          DEFAULT_LTHR[sport],
            "longest_km":              round(sdf["distance_km"].max(), 1),
            "avg_tss":                 round(sdf["tss_estimated"].mean(), 1),
        }

    ft = fitness_trend(df)
    if not ft.empty:
        p["estimated_ctl"] = float(ft["CTL"].iloc[-1])
        p["estimated_atl"] = float(ft["ATL"].iloc[-1])
        p["estimated_tsb"] = float(ft["TSB"].iloc[-1])
    return p


# ── Summary ───────────────────────────────────────────────────
def print_summary(df, profile):
    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]STRAVA SYNC COMPLETE[/bold cyan]\n"
        f"Athlete: [yellow]{profile['athlete_name']}[/yellow]  |  "
        f"A-Race: [yellow]{profile['a_race']['name']} — {profile['a_race']['date']}[/yellow]",
        border_style="cyan"
    ))
    t = Table(title="Activities (Last 12 Months)", style="cyan")
    for col in ["Sport","Activities","Total Hours","Avg HR","Avg TSS","LTHR (default)"]:
        t.add_column(col, justify="center")
    for sport in ["run","bike","swim"]:
        s = profile["sports"].get(sport, {})
        if s:
            t.add_row(sport.upper(), str(s["total_activities"]), f"{s['total_hours']}h",
                      str(int(s["avg_hr"])) if s["avg_hr"] else "—",
                      str(s["avg_tss"]), str(s["estimated_lthr"]))
    console.print(t)

    c = profile.get("80_20_compliance_pct", 0)
    color = "green" if c >= 75 else "yellow" if c >= 60 else "red"
    console.print(f"\n  [bold]80/20 Compliance:[/bold] [{color}]{c}%[/{color}] (target: 80%+)")
    console.print(f"  [bold]Fitness (CTL):[/bold] {round(profile.get('estimated_ctl',0),1)}  "
                  f"[bold]Form (TSB):[/bold] {round(profile.get('estimated_tsb',0),1)}")
    console.print(f"  [bold]Weekly Volume:[/bold] [yellow]{profile['weekly_volume_hours']}h/week[/yellow] (last 4 weeks)")
    console.print(f"\n  [green]Data saved to ~/Documents/training_data/[/green]\n")


# ── Main ──────────────────────────────────────────────────────
def main():
    console.print(Panel.fit(
        "[bold cyan]IRONMAN 70.3 Training System[/bold cyan]\n"
        "Strava Data Connector · 80/20 Method", border_style="blue"
    ))

    console.print("\n[bold]Step 1/4:[/bold] Authenticating...")
    token = get_valid_token()
    if not token: return
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    console.print("  [green]✓ Authenticated[/green]")

    console.print("\n[bold]Step 2/4:[/bold] Fetching athlete profile...")
    athlete = fetch_athlete(headers)
    console.print(f"  [green]✓ Hello {athlete.get('firstname', '')} {athlete.get('lastname', '')}[/green]")

    console.print("\n[bold]Step 3/4:[/bold] Fetching activities (last 12 months)...")
    raw = fetch_activities(headers, int(os.getenv("HISTORY_DAYS", 365)))
    console.print(f"  [green]✓ {len(raw)} total activities found[/green]")

    with open(DATA_DIR / "activities_raw.json", "w") as f:
        json.dump(raw, f, indent=2, default=str)

    console.print("\n[bold]Step 4/4:[/bold] Processing & classifying workouts...")
    df = process(raw)
    console.print(f"  [green]✓ {len(df)} triathlon activities (swim/bike/run) processed[/green]")

    df.to_csv(DATA_DIR / "activities_clean.csv", index=False)

    profile = build_profile(df, athlete)
    with open(DATA_DIR / "athlete_profile.json", "w") as f:
        json.dump(profile, f, indent=2, default=str)

    ft = fitness_trend(df)
    if not ft.empty:
        ft.to_csv(DATA_DIR / "fitness_trend.csv", index=False)

    print_summary(df, profile)
    console.print("[bold cyan]Next:[/bold cyan] Run [yellow]python3 training_plan_generator.py[/yellow]\n")

if __name__ == "__main__":
    main()
