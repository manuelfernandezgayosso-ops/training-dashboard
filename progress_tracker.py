#!/usr/bin/env python3
"""
IRONMAN 70.3 Training System — Progress Tracker
Matches your actual Strava workouts to the planned sessions.
Calculates compliance, zone accuracy, and volume deltas.
Unplanned/bonus sessions are tracked separately.
Usage: python3 progress_tracker.py
"""

import json, os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "~/Documents/training_data")).expanduser()
DATA_DIR   = OUTPUT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Zone target compliance tolerance ─────────────────────────
ZONE_ORDER = ["Zone 1", "Zone 2", "Zone X", "Zone 3", "Zone 4", "Zone 5", "Unknown"]

def zone_distance(z1: str, z2: str) -> int:
    try:
        return abs(ZONE_ORDER.index(z1) - ZONE_ORDER.index(z2))
    except ValueError:
        return 99

def zone_compliant(actual_zone: str, target_zone: str) -> bool:
    if not actual_zone or actual_zone == "Unknown": return False
    if "-" in str(target_zone):
        parts = target_zone.split("-")
        targets = [p.strip() for p in parts]
        return any(zone_distance(actual_zone, t) <= 1 for t in targets)
    return zone_distance(actual_zone, target_zone) <= 1

def duration_compliance_pct(actual_min: float, planned_min: float) -> float:
    if not planned_min or planned_min == 0: return 0.0
    return round((actual_min / planned_min) * 100, 1)

def get_week_number(act_date, plan: pd.DataFrame):
    """Find which training week a date falls in."""
    for _, row in plan.iterrows():
        plan_date  = row["date"]
        week_start = plan_date - timedelta(days=plan_date.weekday())
        week_end   = week_start + timedelta(days=6)
        if week_start <= act_date <= week_end:
            return int(row.get("week", 0)), str(row.get("phase", ""))
    return 0, ""


# ── Load data ─────────────────────────────────────────────────

def load_data():
    acts_path = DATA_DIR / "activities_clean.csv"
    plan_path = DATA_DIR / "training_plan_14weeks.csv"

    if not acts_path.exists():
        console.print("[red]No activities found. Run strava_connector.py first.[/red]")
        return None, None
    if not plan_path.exists():
        console.print("[red]No training plan found. Run training_plan_generator.py first.[/red]")
        return None, None

    acts = pd.read_csv(acts_path)
    plan = pd.read_csv(plan_path)

    acts["start_time"] = pd.to_datetime(acts["start_time"], utc=True)
    acts["date_only"]  = acts["start_time"].dt.date
    plan["date"]       = pd.to_datetime(plan["date"]).dt.date

    return acts, plan


# ── Match actuals to plan ─────────────────────────────────────

def match_sessions(acts: pd.DataFrame, plan: pd.DataFrame) -> pd.DataFrame:
    """
    For each planned session, find the best matching actual activity.
    Match by sport + week — any activity in the same Mon-Sun week counts.
    Each activity can only be matched once.
    Unmatched activities within the plan window are appended as 'bonus' rows.
    """
    planned = plan[plan["sport"].isin(["run","bike","swim","race"])].copy()

    results = []
    used_indices = set()

    for _, p in planned.iterrows():
        plan_date  = p["date"]
        plan_sport = p["sport"]
        plan_min   = p.get("duration_min", 0) or 0
        plan_zone  = p.get("zone", "") or ""
        plan_type  = p.get("type", "") or ""
        week       = p.get("week", 0)
        phase      = p.get("phase", "")
        week_focus = p.get("week_focus", "")

        week_start = plan_date - timedelta(days=plan_date.weekday())
        week_end   = week_start + timedelta(days=6)

        candidates = acts[
            (acts["date_only"] >= week_start) &
            (acts["date_only"] <= week_end) &
            (acts["sport"] == plan_sport) &
            (~acts.index.isin(used_indices))
        ].copy()

        if candidates.empty:
            results.append({
                "week":               week,
                "phase":              phase,
                "plan_date":          str(plan_date),
                "day":                p.get("day", ""),
                "sport":              plan_sport,
                "session_type":       plan_type,
                "planned_min":        plan_min,
                "planned_zone":       plan_zone,
                "week_focus":         week_focus,
                "status":             "missed",
                "is_bonus":           False,
                "actual_date":        None,
                "actual_min":         0,
                "actual_distance_km": 0,
                "actual_hr":          0,
                "actual_zone":        None,
                "actual_tss":         0,
                "duration_pct":       0,
                "zone_compliant":     False,
                "activity_name":      None,
                "activity_id":        None,
            })
        else:
            if len(candidates) > 1:
                candidates = candidates.copy()
                candidates["dur_diff"] = abs(candidates["duration_min"] - plan_min)
                candidates = candidates.sort_values("dur_diff")

            best = candidates.iloc[0]
            used_indices.add(best.name)

            actual_min  = best.get("duration_min", 0) or 0
            actual_zone = best.get("zone_80_20", "Unknown") or "Unknown"
            dur_pct     = duration_compliance_pct(actual_min, plan_min)
            zc          = zone_compliant(actual_zone, plan_zone)

            if dur_pct >= 85:
                status = "completed"
            elif dur_pct >= 50:
                status = "partial"
            else:
                status = "missed"

            results.append({
                "week":               week,
                "phase":              phase,
                "plan_date":          str(plan_date),
                "day":                p.get("day", ""),
                "sport":              plan_sport,
                "session_type":       plan_type,
                "planned_min":        plan_min,
                "planned_zone":       plan_zone,
                "week_focus":         week_focus,
                "status":             status,
                "is_bonus":           False,
                "actual_date":        str(best.get("date_only", "")),
                "actual_min":         round(actual_min, 1),
                "actual_distance_km": round(best.get("distance_km", 0) or 0, 2),
                "actual_hr":          round(best.get("avg_hr", 0) or 0, 0),
                "actual_zone":        actual_zone,
                "actual_tss":         round(best.get("tss_estimated", 0) or 0, 1),
                "duration_pct":       dur_pct,
                "zone_compliant":     zc,
                "activity_name":      best.get("activity_name", ""),
                "activity_id":        best.get("activity_id", ""),
            })

    # ── Bonus sessions — unmatched activities within plan window ──
    plan_start = plan["date"].min()
    plan_end   = plan["date"].max()

    unmatched = acts[
        (~acts.index.isin(used_indices)) &
        (acts["date_only"] >= plan_start) &
        (acts["date_only"] <= plan_end)
    ]

    for _, a in unmatched.iterrows():
        act_date = a["date_only"]
        week_num, phase = get_week_number(act_date, plan)
        if week_num == 0:
            continue

        actual_min  = a.get("duration_min", 0) or 0
        actual_zone = a.get("zone_80_20", "Unknown") or "Unknown"
        sport       = a.get("sport", "unknown")

        results.append({
            "week":               week_num,
            "phase":              phase,
            "plan_date":          str(act_date),
            "day":                act_date.strftime("%A") if hasattr(act_date, "strftime") else "",
            "sport":              sport,
            "session_type":       "Bonus",
            "planned_min":        0,
            "planned_zone":       "—",
            "week_focus":         "Unplanned",
            "status":             "bonus",
            "is_bonus":           True,
            "actual_date":        str(act_date),
            "actual_min":         round(actual_min, 1),
            "actual_distance_km": round(a.get("distance_km", 0) or 0, 2),
            "actual_hr":          round(a.get("avg_hr", 0) or 0, 0),
            "actual_zone":        actual_zone,
            "actual_tss":         round(a.get("tss_estimated", 0) or 0, 1),
            "duration_pct":       100,
            "zone_compliant":     False,
            "activity_name":      a.get("activity_name", ""),
            "activity_id":        a.get("activity_id", ""),
        })

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values(["week", "plan_date", "is_bonus"]).reset_index(drop=True)
    return df


# ── Weekly summary ────────────────────────────────────────────

def weekly_summary(progress: pd.DataFrame) -> pd.DataFrame:
    summaries = []
    for week in sorted(progress["week"].unique()):
        wdf     = progress[progress["week"] == week]
        planned = wdf[~wdf["is_bonus"]]
        bonus   = wdf[wdf["is_bonus"]]

        planned_sessions  = len(planned[planned["sport"] != "race"])
        completed         = len(planned[planned["status"] == "completed"])
        partial           = len(planned[planned["status"] == "partial"])
        missed            = len(planned[planned["status"] == "missed"])
        bonus_count       = len(bonus)
        planned_min_total = planned["planned_min"].sum()
        actual_min_total  = wdf["actual_min"].sum()  # includes bonus volume
        zone_compliant_n  = planned["zone_compliant"].sum()
        zone_total        = len(planned[planned["status"].isin(["completed","partial"])])
        phase             = wdf["phase"].iloc[0] if not wdf.empty else ""

        summaries.append({
            "week":                week,
            "phase":               phase,
            "planned_sessions":    planned_sessions,
            "completed":           completed,
            "partial":             partial,
            "missed":              missed,
            "bonus_sessions":      bonus_count,
            "completion_pct":      round((completed + partial * 0.5) / max(planned_sessions, 1) * 100, 1),
            "planned_hours":       round(planned_min_total / 60, 1),
            "actual_hours":        round(actual_min_total / 60, 1),
            "volume_pct":          round(actual_min_total / max(planned_min_total, 1) * 100, 1),
            "zone_compliance_pct": round(zone_compliant_n / max(zone_total, 1) * 100, 1),
        })

    return pd.DataFrame(summaries)


# ── Coaching notes (Fitzgerald principles) ───────────────────

def coaching_note(week_df: pd.DataFrame, week_summary: dict) -> str:
    notes = []

    completion  = week_summary.get("completion_pct", 0)
    zone_comp   = week_summary.get("zone_compliance_pct", 0)
    vol_pct     = week_summary.get("volume_pct", 0)
    bonus_count = week_summary.get("bonus_sessions", 0)

    zone_x_count = len(week_df[week_df["actual_zone"] == "Zone X"])
    if zone_x_count > 0:
        notes.append(
            f"⚠ {zone_x_count} workout(s) landed in Zone X (no-man's-land, 89–94% LTHR). "
            "This is the zone Fitzgerald warns most about — too hard to recover from, "
            "too easy to build fitness. Push through to Zone 3 or pull back to Zone 2."
        )

    hard_sessions = len(week_df[week_df["actual_zone"].isin(["Zone 3","Zone 4","Zone 5"])])
    total_done    = len(week_df[week_df["status"].isin(["completed","partial","bonus"])])
    if total_done > 0 and hard_sessions / max(total_done, 1) > 0.3:
        notes.append(
            f"You did {hard_sessions}/{total_done} sessions at Zone 3+. "
            "Fitzgerald's rule: no more than 20% of sessions should be hard. "
            "Your easy days need to be easier."
        )

    if bonus_count > 0:
        notes.append(
            f"You added {bonus_count} unplanned session(s) this week. "
            "Extra easy work is fine — just make sure it doesn't compromise your planned key sessions."
        )

    if vol_pct > 115:
        notes.append(
            f"You trained {vol_pct}% of planned volume — more than prescribed. "
            "More is not always better. Stick to the plan; adaptation happens during recovery."
        )

    if vol_pct < 70 and completion < 70:
        notes.append(
            f"Only {completion}% of sessions completed this week. "
            "If life got in the way, that's fine — don't try to make it up. "
            "Just return to the plan next week."
        )

    if completion >= 90 and zone_comp >= 75 and not notes:
        notes.append(
            f"Strong week — {completion}% of sessions completed and {zone_comp}% zone compliant. "
            "This is exactly what Fitzgerald prescribes. Keep protecting those easy days."
        )

    if not notes and completion >= 75:
        notes.append(
            f"Solid week. {completion}% completion. "
            "Focus for next week: make your easy sessions feel almost too easy."
        )

    if not notes:
        notes.append("Keep going. Consistency over perfection — every week you show up counts.")

    return " ".join(notes)


# ── Print terminal summary ────────────────────────────────────

def print_progress(progress: pd.DataFrame, weekly: pd.DataFrame) -> None:
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]TRAINING PROGRESS — ACTUALS VS PLAN[/bold cyan]\n"
        "[dim]Matt Fitzgerald 80/20 · Ironman 70.3 June 28[/dim]",
        border_style="cyan"
    ))

    active_weeks = weekly[weekly["actual_hours"] > 0]

    t = Table(title="Weekly Summary", style="cyan", show_lines=True)
    for col in ["Wk","Phase","Done/Planned","Bonus","Completion","Vol Planned","Vol Actual","Zone Comply"]:
        t.add_column(col, justify="center")

    phase_colors = {"Base":"blue","Build":"yellow","Peak":"red","Taper":"green","B-Race":"magenta"}

    for _, row in active_weeks.iterrows():
        c    = row["completion_pct"]
        zc   = row["zone_compliance_pct"]
        col  = "green" if c >= 85 else "yellow" if c >= 65 else "red"
        zcol = "green" if zc >= 75 else "yellow" if zc >= 50 else "red"
        pc   = phase_colors.get(row["phase"], "white")
        bonus = int(row.get("bonus_sessions", 0))
        t.add_row(
            str(int(row["week"])),
            f"[{pc}]{row['phase']}[/{pc}]",
            f"{int(row['completed'])}/{int(row['planned_sessions'])}",
            f"[cyan]+{bonus}[/cyan]" if bonus > 0 else "—",
            f"[{col}]{c}%[/{col}]",
            f"{row['planned_hours']}h",
            f"{row['actual_hours']}h",
            f"[{zcol}]{zc}%[/{zcol}]",
        )
    console.print(t)

    today_week = progress[
        progress["plan_date"] >= str(date.today() - timedelta(days=7))
    ]
    if not today_week.empty:
        console.print("\n[bold]This week's sessions:[/bold]")
        st = Table(style="dim", show_header=True, show_lines=False)
        for col in ["Date","Sport","Type","Planned","Actual","Status","Zone OK?"]:
            st.add_column(col)
        for _, r in today_week.iterrows():
            if r["is_bonus"]:
                status_color = "cyan"
                status_label = "BONUS"
            else:
                status_color = {"completed":"green","partial":"yellow","missed":"red"}.get(r["status"],"white")
                status_label = r["status"]
            st.add_row(
                str(r["plan_date"]),
                r["sport"].upper(),
                r.get("session_type","") or "",
                f"{int(r['planned_min'])} min / {r['planned_zone']}" if not r["is_bonus"] else "—",
                f"{int(r['actual_min'])} min / {r['actual_zone'] or '—'}" if r["actual_min"] > 0 else "—",
                f"[{status_color}]{status_label}[/{status_color}]",
                "[green]✓[/green]" if r["zone_compliant"] else "[cyan]—[/cyan]" if r["is_bonus"] else "[red]✗[/red]" if r["actual_min"] > 0 else "—",
            )
        console.print(st)

    console.print(f"\n  [green]✓ Progress data saved to ~/Documents/training_data/data/[/green]\n")


# ── Main ──────────────────────────────────────────────────────

def main():
    console.print(Panel.fit(
        "[bold cyan]Progress Tracker[/bold cyan]\n"
        "Matching Strava actuals to your 70.3 plan",
        border_style="blue"
    ))

    acts, plan = load_data()
    if acts is None: return

    console.print(f"\n  Loaded [yellow]{len(acts)}[/yellow] activities and [yellow]{len(plan)}[/yellow] planned sessions")
    console.print("  Matching actuals to plan (by sport + week)...")
    progress = match_sessions(acts, plan)

    planned_count = len(progress[~progress["is_bonus"]])
    bonus_count   = len(progress[progress["is_bonus"]])
    console.print(f"  [green]✓ {planned_count} planned sessions matched, {bonus_count} bonus sessions found[/green]")

    weekly = weekly_summary(progress)

    progress.to_csv(DATA_DIR / "progress_actuals.csv", index=False)
    weekly.to_csv(DATA_DIR / "progress_weekly.csv", index=False)

    weekly_with_notes = []
    for _, row in weekly.iterrows():
        week_sessions = progress[progress["week"] == row["week"]]
        note = coaching_note(week_sessions, row.to_dict())
        d = row.to_dict()
        d["coaching_note"] = note
        weekly_with_notes.append(d)

    with open(DATA_DIR / "progress_weekly_notes.json", "w") as f:
        json.dump(weekly_with_notes, f, indent=2, default=str)

    print_progress(progress, weekly)

    console.print("[bold cyan]Next:[/bold cyan] Run [yellow]python3 dashboard_generator.py[/yellow] to see progress in dashboard\n")


if __name__ == "__main__":
    main()
