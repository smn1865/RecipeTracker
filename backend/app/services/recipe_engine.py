from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Ingredient, PantryItem, Recipe, RecipeIngredient, User
from .location import options_for_ingredient, user_coordinates
from .recipe_matcher import convert_quantity
from .preferences import id_list, recipe_is_allowed

def missing_for_recipe(recipe: Recipe, pantry: list[PantryItem]):
    missing = []
    for ingredient in recipe.ingredients:
        available = 0.0
        for item in pantry:
            if item.ingredient_name.lower() != ingredient.ingredient_name.lower():
                continue
            converted = convert_quantity(item.quantity, item.unit, ingredient.unit)
            if converted is not None:
                available += converted
        shortage = max(0.0, ingredient.required_qty - available)
        if shortage > 1e-9:
            missing.append(RecipeIngredient(
                ingredient_name=ingredient.ingredient_name,
                required_qty=round(shortage, 3),
                unit=ingredient.unit,
            ))
    return missing

async def shopping_plan(session: AsyncSession, user: User, recipe: Recipe, pantry: list[PantryItem], radius_km: float = 5):
    missing = missing_for_recipe(recipe, pantry)
    items, total = [], 0.0
    for ingredient in missing:
        lat, lon = user_coordinates(getattr(user, "lat", None), getattr(user, "lon", None))
        options = await options_for_ingredient(session, ingredient.ingredient_name.lower(), ingredient.required_qty,
                                               ingredient.unit, lat, lon, radius_km)
        best = options[0]
        total += best["estimated_cost"]
        items.append({"ingredient_name": ingredient.ingredient_name, "quantity": ingredient.required_qty,
                      "unit": ingredient.unit, "best_option": best, "alternatives": options[1:3]})
    return items, round(total, 2)

async def smart_suggestions(session: AsyncSession, user: User, calorie_budget: int, category: str = "All", tag: str | None = None, limit: int = 12):
    pantry = (await session.scalars(select(PantryItem).where(PantryItem.user_id == user.id))).all()
    recipes = (await session.scalars(select(Recipe).options(selectinload(Recipe.ingredients)))).all()
    ingredient_rows = (await session.scalars(select(Ingredient))).all()
    ingredient_ids = {item.name.lower(): item.id for item in ingredient_rows}
    excluded = set(id_list(user.excluded_ingredient_ids))
    favorites = set(id_list(user.favorite_meal_ids))
    results = []
    for recipe in recipes:
        if not recipe_is_allowed(recipe, excluded, ingredient_ids): continue
        if category.lower() not in {"all", ""} and recipe.meal_type.lower() != category.rstrip("s").lower(): continue
        recipe_tags = [value.strip() for value in recipe.tags.split(",") if value.strip()]
        if tag and tag.lower() not in {value.lower() for value in recipe_tags}: continue
        # A meal should generally fit one third of daily calories, with leniency for a main meal.
        if recipe.calories > calorie_budget * .55: continue
        missing = missing_for_recipe(recipe, pantry)
        match = round(100 * (len(recipe.ingredients) - len(missing)) / max(len(recipe.ingredients), 1), 1)
        _, cost = await shopping_plan(session, user, recipe, pantry)
        results.append({"id": recipe.id, "title": recipe.title, "calories": recipe.calories, "protein_g": recipe.protein_g, "carbs_g": recipe.carbs_g, "fat_g": recipe.fat_g, "prep_time": recipe.prep_time, "meal_type": recipe.meal_type, "tags": recipe_tags,
                        "pantry_match_percent": match, "missing_ingredients": [{"ingredient_name": x.ingredient_name, "quantity": x.required_qty, "unit": x.unit} for x in missing], "estimated_missing_cost": cost})
    return sorted(results, key=lambda r: (r["id"] not in favorites, -r["pantry_match_percent"], r["estimated_missing_cost"], -r["protein_g"]))[:limit]
