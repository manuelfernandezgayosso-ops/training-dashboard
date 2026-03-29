#!/usr/bin/env python3
"""
IRONMAN 70.3 Training System — Nutrition Planner
Generates daily nutrition targets and meal plans keyed to training load.
Science base: Matt Fitzgerald 80/20 Triathlon + sports dietitian standards.
Athlete: 75kg, gluten-free
"""

import os, json
from pathlib import Path
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ".")).expanduser()
DATA_DIR   = OUTPUT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Athlete constants ─────────────────────────────────────────
BODY_WEIGHT_KG = 75
DIET = "gluten-free"

# ── Macro targets by day type (g/kg body weight) ─────────────
# Reference: Fitzgerald 80/20 Triathlon + IOC sports nutrition consensus
DAY_TARGETS = {
    "hard": {
        "label": "Hard Training Day",
        "carb_per_kg": 8.0,
        "protein_per_kg": 1.7,
        "fat_per_kg": 1.2,
        "color": "#ff6b35",
    },
    "moderate": {
        "label": "Moderate Training Day",
        "carb_per_kg": 5.5,
        "protein_per_kg": 1.7,
        "fat_per_kg": 1.3,
        "color": "#f59e0b",
    },
    "easy": {
        "label": "Easy Training Day",
        "carb_per_kg": 3.5,
        "protein_per_kg": 1.7,
        "fat_per_kg": 1.4,
        "color": "#22c55e",
    },
    "rest": {
        "label": "Rest / Recovery Day",
        "carb_per_kg": 3.0,
        "protein_per_kg": 1.8,
        "fat_per_kg": 1.5,
        "color": "#64748b",
    },
}

# ── Gluten-free meal templates by day type ───────────────────
MEALS = {
    "hard": {
        "breakfast": {
            "name": "Pre-Training Power Bowl",
            "items": [
                "1.5 cups cooked white rice",
                "2 whole eggs + 2 egg whites (scrambled)",
                "1/2 avocado",
                "1 banana",
                "1 cup orange juice",
            ],
            "notes": "Eat 2–3 hrs before training. High carb, moderate protein.",
        },
        "mid_morning": {
            "name": "Training Fuel",
            "items": [
                "2 medjool dates",
                "1 rice cake with honey",
                "500ml water with electrolytes",
            ],
            "notes": "During or immediately after long session.",
        },
        "lunch": {
            "name": "Recovery Lunch",
            "items": [
                "200g grilled salmon or chicken",
                "1.5 cups brown rice",
                "2 cups roasted sweet potato",
                "Large mixed greens salad with olive oil",
                "1 cup mixed berries",
            ],
            "notes": "Within 45 min of finishing training. Prioritize protein + carbs.",
        },
        "snack": {
            "name": "Afternoon Snack",
            "items": [
                "Greek yogurt (250g)",
                "1 tbsp honey",
                "1/4 cup gluten-free granola",
                "1 apple",
            ],
            "notes": "3–4 hrs after lunch.",
        },
        "dinner": {
            "name": "Evening Recovery",
            "items": [
                "180g lean beef, chicken, or white fish",
                "1 cup quinoa",
                "2 cups steamed broccoli and zucchini",
                "1 tbsp olive oil",
                "1 cup rice pasta (optional if still hungry)",
            ],
            "notes": "Keep dinner light on fat. Protein to support overnight recovery.",
        },
    },
    "moderate": {
        "breakfast": {
            "name": "Balanced Start",
            "items": [
                "3 eggs scrambled",
                "2 corn tortillas",
                "1/2 cup black beans",
                "1/2 avocado",
                "1 cup mixed fruit",
            ],
            "notes": "Balanced macros — good for moderate swim or easy bike days.",
        },
        "lunch": {
            "name": "Power Salad",
            "items": [
                "170g grilled chicken or tuna",
                "1 cup cooked quinoa",
                "Large kale or spinach salad",
                "Cherry tomatoes, cucumber, red onion",
                "Olive oil + lemon dressing",
                "1 orange",
            ],
            "notes": "High nutrient density, moderate carbs.",
        },
        "snack": {
            "name": "Afternoon Fuel",
            "items": [
                "2 rice cakes with almond butter",
                "1 banana",
            ],
            "notes": "Keep energy stable for evening session if planned.",
        },
        "dinner": {
            "name": "Lean Dinner",
            "items": [
                "170g salmon or lean beef",
                "1 cup roasted sweet potato",
                "2 cups sautéed vegetables (zucchini, peppers, spinach)",
                "1 tbsp olive oil",
            ],
            "notes": "Reduce carbs slightly vs hard day. Emphasize vegetables.",
        },
    },
    "easy": {
        "breakfast": {
            "name": "Light Start",
            "items": [
                "2 eggs any style",
                "1/2 cup roasted sweet potato",
                "Large handful spinach (sautéed)",
                "1/2 cup blueberries",
                "Black coffee or green tea",
            ],
            "notes": "Lower carb start — save carbs for around your easy session.",
        },
        "lunch": {
            "name": "Protein Bowl",
            "items": [
                "150g grilled chicken or shrimp",
                "1/2 cup brown rice",
                "Large green salad with avocado",
                "Olive oil + apple cider vinegar dressing",
                "1 apple",
            ],
            "notes": "Moderate protein, lower carb.",
        },
        "snack": {
            "name": "Light Snack",
            "items": [
                "Handful of mixed nuts",
                "1 piece of fruit",
            ],
            "notes": "Keep it light.",
        },
        "dinner": {
            "name": "Recovery Dinner",
            "items": [
                "170g white fish or chicken",
                "2 cups roasted vegetables",
                "Small side salad",
                "1/2 cup quinoa",
            ],
            "notes": "Emphasize protein and vegetables. Limit starchy carbs.",
        },
    },
    "rest": {
        "breakfast": {
            "name": "Rest Day Breakfast",
            "items": [
                "3 eggs + smoked salmon",
                "1/2 avocado",
                "Sliced tomatoes",
                "Black coffee",
            ],
            "notes": "Higher fat, lower carb. No need to load glycogen.",
        },
        "lunch": {
            "name": "Anti-Inflammatory Lunch",
            "items": [
                "Large mixed greens salad",
                "150g grilled salmon",
                "1/4 cup walnuts",
                "Blueberries and sliced beets",
                "Olive oil + lemon dressing",
            ],
            "notes": "Focus on anti-inflammatory foods to support recovery.",
        },
        "snack": {
            "name": "Light Snack",
            "items": [
                "1 tbsp almond butter",
                "Celery sticks or apple slices",
            ],
            "notes": "Keep snacks minimal on rest days.",
        },
        "dinner": {
            "name": "Lean Recovery Dinner",
            "items": [
                "170g lean protein (chicken, turkey, or white fish)",
                "2 cups steamed or roasted vegetables",
                "Small sweet potato (optional)",
                "1 tbsp olive oil",
            ],
            "notes": "Protein-forward dinner. Go easy on starches.",
        },
    },
}


def calc_macros(day_type: str) -> dict:
    t = DAY_TARGETS[day_type]
    carbs = round(t["carb_per_kg"] * BODY_WEIGHT_KG)
    protein = round(t["protein_per_kg"] * BODY_WEIGHT_KG)
    fat = round(t["fat_per_kg"] * BODY_WEIGHT_KG)
    calories = round(carbs * 4 + protein * 4 + fat * 9)
    return {
        "day_type": day_type,
        "label": t["label"],
        "color": t["color"],
        "calories": calories,
        "carbs_g": carbs,
        "protein_g": protein,
        "fat_g": fat,
    }


def classify_day(plan_row: dict) -> str:
    """Map training plan session to nutrition day type."""
    if not plan_row or plan_row.get("sport") == "rest":
        return "rest"
    zone = str(plan_row.get("zone", "")).lower()
    duration = plan_row.get("duration_min", 0) or 0
    session_type = str(plan_row.get("type", "")).lower()

    if "race" in session_type:
        return "hard"
    if "3" in zone or "4" in zone or "5" in zone:
        return "hard"
    if duration >= 90:
        return "hard"
    if duration >= 45:
        return "moderate"
    if duration > 0:
        return "easy"
    return "rest"


def generate_nutrition_plan(plan_data: list) -> list:
    """Generate a daily nutrition plan for the full 14-week program."""
    nutrition = []

    # Build a date→session lookup
    session_by_date = {}
    for row in plan_data:
        d = row.get("date")
        if d:
            session_by_date.setdefault(d, []).append(row)

    # Generate for next 98 days (14 weeks)
    today = date.today()
    for i in range(98):
        day = today + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        weekday = day.strftime("%A")

        sessions = session_by_date.get(day_str, [])
        # Pick highest-demand session if multiple
        day_type = "rest"
        if sessions:
            types = [classify_day(s) for s in sessions]
            for t in ["hard", "moderate", "easy", "rest"]:
                if t in types:
                    day_type = t
                    break

        macros = calc_macros(day_type)
        meals = MEALS[day_type]

        nutrition.append({
            "date": day_str,
            "weekday": weekday,
            "day_type": day_type,
            "label": macros["label"],
            "color": macros["color"],
            "calories": macros["calories"],
            "carbs_g": macros["carbs_g"],
            "protein_g": macros["protein_g"],
            "fat_g": macros["fat_g"],
            "sessions": [s.get("sport","") + " " + str(s.get("duration_min","")) + "min"
                         for s in sessions if s.get("sport") != "rest"],
            "meals": meals,
        })

    return nutrition


def main():
    print("\n🥗 Generating Nutrition Plan...")

    # Load training plan
    plan_path = DATA_DIR / "training_plan_14weeks.json"
    if plan_path.exists():
        with open(plan_path) as f:
            plan_data = json.load(f)
        print(f"  ✓ Loaded {len(plan_data)} planned sessions")
    else:
        print("  ⚠ No training plan found — using empty plan")
        plan_data = []

    # Generate
    nutrition = generate_nutrition_plan(plan_data)

    # Save full plan
    out = DATA_DIR / "nutrition_plan.json"
    with open(out, "w") as f:
        json.dump(nutrition, f, indent=2, default=str)

    # Save weekly summary CSV
    import pandas as pd
    df = pd.DataFrame([{
        "date": n["date"],
        "weekday": n["weekday"],
        "day_type": n["day_type"],
        "calories": n["calories"],
        "carbs_g": n["carbs_g"],
        "protein_g": n["protein_g"],
        "fat_g": n["fat_g"],
    } for n in nutrition])
    df.to_csv(DATA_DIR / "nutrition_targets.csv", index=False)

    print(f"  ✓ Nutrition plan saved ({len(nutrition)} days)")
    print(f"  Body weight: {BODY_WEIGHT_KG}kg | Diet: {DIET}")
    print(f"  Hard day: {calc_macros('hard')['calories']} kcal")
    print(f"  Rest day: {calc_macros('rest')['calories']} kcal")


if __name__ == "__main__":
    main()
