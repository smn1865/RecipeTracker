ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
GOAL_ADJUSTMENT = {"deficit": -500, "maintenance": 0, "surplus": 300}

def activity_from_assessment(routine: str, frequency: str, intensity: str, movement: str) -> tuple[str, float]:
    """Blend four lifestyle signals into a transparent TDEE multiplier."""
    routine_score = {"desk": 0, "on_feet": .15, "labor": .35}.get(routine, 0)
    frequency_score = {"0-1": 0, "2-3": .15, "4-5": .28, "6+": .38}.get(frequency, 0)
    intensity_score = {"light": 0, "moderate": .08, "high": .16}.get(intensity, 0)
    movement_score = {"under_5000": 0, "5000_10000": .08, "over_10000": .16}.get(movement, 0)
    multiplier = min(1.9, round(1.2 + routine_score + frequency_score + intensity_score + movement_score, 3))
    level = "sedentary" if multiplier < 1.3 else "light" if multiplier < 1.5 else "moderate" if multiplier < 1.7 else "active" if multiplier < 1.85 else "very_active"
    return level, multiplier

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / (height_cm / 100) ** 2, 1)

def bmi_status(bmi: float) -> str:
    if bmi < 18.5: return "underweight"
    if bmi < 25: return "healthy weight"
    if bmi < 30: return "overweight"
    return "obesity"

def nutrition_targets(weight_kg: float, height_cm: float, age: int, gender: str, activity_level: str, goal: str, *, daily_routine: str | None = None, exercise_frequency: str | None = None, exercise_intensity: str | None = None, daily_movement: str | None = None):
    # Mifflin-St Jeor, with a neutral fallback for non-binary/unspecified entries.
    sex_factor = 5 if gender.lower() == "male" else -161 if gender.lower() == "female" else -78
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + sex_factor
    multiplier = ACTIVITY.get(activity_level, 1.2)
    if all(v is not None for v in (daily_routine, exercise_frequency, exercise_intensity, daily_movement)):
        _, multiplier = activity_from_assessment(daily_routine, exercise_frequency, exercise_intensity, daily_movement)
    calories = max(1200, round(bmr * multiplier + GOAL_ADJUSTMENT.get(goal, 0)))
    protein = round(weight_kg * (2.0 if goal == "deficit" else 1.6))
    fat = round(calories * 0.28 / 9)
    carbs = round((calories - protein * 4 - fat * 9) / 4)
    return {"daily_calories": calories, "protein_g": protein, "carbs_g": max(0, carbs), "fat_g": fat}
