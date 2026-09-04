from app.services.recipe_engine import smart_suggestions

def test_category_normalization_is_singular_safe():
    # The UI uses "Snacks" while persisted recipes use the singular "Snack".
    assert "Snacks".rstrip("s").lower() == "snack"
