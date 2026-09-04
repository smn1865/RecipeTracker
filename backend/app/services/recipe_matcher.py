from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Ingredient, PantryItem, RecipeIngredient

WEIGHT_TO_G = {"g": 1.0, "kg": 1000.0, "oz": 28.3495, "lb": 453.592}
VOLUME_TO_ML = {"ml": 1.0, "l": 1000.0}
COUNT_UNITS = {"each", "item", "piece", "pieces", "unit"}


def convert_quantity(quantity: float, from_unit: str, to_unit: str) -> float | None:
    """Convert compatible pantry units. None means the units cannot be safely compared."""
    source, target = from_unit.strip().lower(), to_unit.strip().lower()
    if source == target:
        return float(quantity)
    if source in WEIGHT_TO_G and target in WEIGHT_TO_G:
        return float(quantity) * WEIGHT_TO_G[source] / WEIGHT_TO_G[target]
    if source in VOLUME_TO_ML and target in VOLUME_TO_ML:
        return float(quantity) * VOLUME_TO_ML[source] / VOLUME_TO_ML[target]
    if source in COUNT_UNITS and target in COUNT_UNITS:
        return float(quantity)
    return None


async def recipe_coverage(
    session: AsyncSession,
    recipe_ingredients: list[RecipeIngredient],
    pantry_items: list[PantryItem],
) -> list[dict]:
    names = {item.ingredient_name.strip().lower() for item in recipe_ingredients}
    ingredients = (
        await session.scalars(select(Ingredient).where(func.lower(Ingredient.name).in_(names)))
    ).all()
    by_name = {item.name.strip().lower(): item for item in ingredients}
    pantry_by_id: dict[int, list[PantryItem]] = defaultdict(list)
    pantry_by_name: dict[str, list[PantryItem]] = defaultdict(list)
    for item in pantry_items:
        if item.ingredient_id:
            pantry_by_id[item.ingredient_id].append(item)
        pantry_by_name[item.ingredient_name.strip().lower()].append(item)

    rows = []
    for required in recipe_ingredients:
        name = required.ingredient_name.strip().lower()
        canonical = by_name.get(name)
        candidates = pantry_by_id.get(canonical.id, []) if canonical else []
        if not candidates:
            candidates = pantry_by_name.get(name, [])
        available = 0.0
        for pantry_item in candidates:
            converted = convert_quantity(pantry_item.quantity, pantry_item.unit, required.unit)
            if converted is not None:
                available += converted
        covered = min(available, required.required_qty)
        missing = max(0.0, required.required_qty - available)
        status = "FULLY_OWNED" if missing <= 1e-9 else ("PARTIALLY_OWNED" if covered > 0 else "MISSING")
        rows.append({
            "ingredient_id": canonical.id if canonical else None,
            "ingredient_name": required.ingredient_name,
            "required_quantity": round(required.required_qty, 3),
            "pantry_quantity": round(covered, 3),
            "missing_quantity": round(missing, 3),
            "coverage_status": status,
            "unit": required.unit,
        })
    return rows
