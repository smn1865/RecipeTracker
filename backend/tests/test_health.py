from app.services.health import activity_from_assessment, bmi_status, calculate_bmi, nutrition_targets

def test_bmi_calculation_and_status():
    assert calculate_bmi(70, 175) == 22.9
    assert bmi_status(22.9) == "healthy weight"

def test_deficit_targets_are_lower_than_maintenance():
    deficit = nutrition_targets(70, 175, 30, "male", "moderate", "deficit")
    maintenance = nutrition_targets(70, 175, 30, "male", "moderate", "maintenance")
    assert deficit["daily_calories"] == maintenance["daily_calories"] - 500
    assert deficit["protein_g"] > maintenance["protein_g"]

def test_activity_assessment_changes_tdee_multiplier():
    _, low = activity_from_assessment("desk", "0-1", "light", "under_5000")
    _, high = activity_from_assessment("labor", "6+", "high", "over_10000")
    assert high > low
    assert nutrition_targets(70, 175, 30, "male", "sedentary", "maintenance", daily_routine="labor", exercise_frequency="6+", exercise_intensity="high", daily_movement="over_10000")["daily_calories"] > 2500
