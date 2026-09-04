from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import Ingredient, PantryItem, Recipe, User, WeeklyMealAssignment
from ..schemas import AutoGenerateRequest, AutoGenerateResponse, ConsolidateRequest, ConsolidateResponse, MealConsumeRequest, MealConsumeResponse
from ..services.recipe_engine import shopping_plan
from ..services.location import get_currency_for_coords, options_for_ingredient
from ..services.recipe_matcher import convert_quantity
from ..services.preferences import id_list, recipe_is_allowed

router = APIRouter(prefix="/api/planner", tags=["planner"])
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SLOTS = ["Breakfast", "Lunch", "Dinner"]

@router.post("/auto-generate", response_model=AutoGenerateResponse)
async def auto_generate(payload: AutoGenerateRequest, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    recipes = (await session.scalars(select(Recipe).options(selectinload(Recipe.ingredients)))).all()
    ingredient_rows = (await session.scalars(select(Ingredient))).all()
    ingredient_ids = {item.name.lower(): item.id for item in ingredient_rows}
    excluded = set(id_list(user.excluded_ingredient_ids))
    recipes = [recipe for recipe in recipes if recipe_is_allowed(recipe, excluded, ingredient_ids)]
    pantry = (await session.scalars(select(PantryItem).where(PantryItem.user_id==user.id))).all()
    if not recipes: raise HTTPException(409, "No recipes remain after applying your excluded ingredients")
    recipe_costs = {}
    for recipe in recipes:
        _, recipe_costs[recipe.id] = await shopping_plan(session, user, recipe, pantry)
    chosen, used_ingredients, repeats = [], set(), {}
    for day in DAYS:
        for slot in SLOTS:
            candidates = [r for r in recipes if r.meal_type.lower() == slot.lower()] or recipes
            def score(recipe):
                names={i.ingredient_name.lower() for i in recipe.ingredients}
                overlap=len(names & used_ingredients)/max(1,len(names))
                return recipe_costs[recipe.id]*(1-.45*overlap)+repeats.get(recipe.id,0)*.35
            recipe=min(candidates,key=score)
            chosen.append((day,slot,recipe)); repeats[recipe.id]=repeats.get(recipe.id,0)+1
            used_ingredients.update(i.ingredient_name.lower() for i in recipe.ingredients)
    required={}
    for _,_,recipe in chosen:
        for ingredient in recipe.ingredients:
            key=(ingredient.ingredient_name.lower(),ingredient.unit)
            required[key]=required.get(key,0)+ingredient.required_qty
    stock={(p.ingredient_name.lower(),p.unit):p.quantity for p in pantry}
    aggregated=[]; total=0.0
    for (name,unit),qty in required.items():
        missing=max(0,qty-stock.get((name,unit),0))
        if missing<=0: continue
        options=await options_for_ingredient(session,name,missing,unit,user.lat,user.lon)
        cost=options[0]["estimated_cost"]; total+=cost
        aggregated.append({"ingredient_name":name,"quantity":round(missing,2),"unit":unit,"estimated_cost_usd":cost})
    naive=sum(recipe_costs[r.id] for _,_,r in chosen)
    currency,symbol,rate=get_currency_for_coords(user.lat,user.lon)
    meals=[]
    for day, slot, recipe in chosen:
        assignment = WeeklyMealAssignment(user_id=user.id, day=day, slot=slot, recipe_id=recipe.id)
        session.add(assignment)
        await session.flush()
        meals.append({"meal_id": assignment.id, "day": day, "slot": slot, "recipe_id": recipe.id,
                      "title": recipe.title, "estimated_cost_usd": recipe_costs[recipe.id],
                      "calories": recipe.calories, "protein_g": recipe.protein_g,
                      "carbs_g": recipe.carbs_g, "fat_g": recipe.fat_g,
                      "eaten": False, "eaten_at": None})
    await session.commit()
    return {"meals":meals,"total_cost_usd":round(total,2),"total_cost_local":round(total*rate,2),"local_currency":currency,"local_currency_symbol":symbol,"usd_to_local_rate":rate,"saved_via_overlap_usd":round(max(0,naive-total),2),"ingredients":aggregated,"total_calories":sum(r.calories for _,_,r in chosen),"total_protein_g":round(sum(r.protein_g for _,_,r in chosen),1),"total_carbs_g":round(sum(r.carbs_g for _,_,r in chosen),1),"total_fat_g":round(sum(r.fat_g for _,_,r in chosen),1),"weekly_budget":payload.weekly_budget,"exceeds_budget":bool(payload.weekly_budget and total>payload.weekly_budget)}

@router.post("/consolidate", response_model=ConsolidateResponse)
async def consolidate(payload: ConsolidateRequest, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if len(payload.assignments) > 21: raise HTTPException(422, "A week has at most 21 meal slots")
    pantry = (await session.scalars(select(PantryItem).where(PantryItem.user_id==user.id))).all()
    total, needs, planned_meals = 0.0, [], []
    for assignment in payload.assignments:
        recipe = await session.get(Recipe, assignment.recipe_id, options=[selectinload(Recipe.ingredients)])
        if not recipe: raise HTTPException(404, f"Recipe {assignment.recipe_id} not found")
        _, cost = await shopping_plan(session, user, recipe, pantry)
        total += cost
        needs.extend(recipe.ingredients)
        meal = WeeklyMealAssignment(user_id=user.id, day=assignment.day, slot=assignment.slot, recipe_id=recipe.id)
        session.add(meal)
        await session.flush()
        planned_meals.append({"meal_id": meal.id, "day": assignment.day, "slot": assignment.slot,
                              "recipe_id": recipe.id, "title": recipe.title, "estimated_cost_usd": cost,
                              "calories": recipe.calories, "protein_g": recipe.protein_g,
                              "carbs_g": recipe.carbs_g, "fat_g": recipe.fat_g,
                              "eaten": False, "eaten_at": None})
    await session.commit()
    return {"total_cost":round(total,2),"weekly_budget":payload.weekly_budget,"exceeds_budget":total>payload.weekly_budget,"missing_ingredients":[{"ingredient_name":i.ingredient_name,"quantity":i.required_qty,"unit":i.unit} for i in needs],"swap_suggestions":["Swap salmon meals for tofu stir fry.","Choose lentil soup or chickpea bowls for budget-friendly lunches."] if total>payload.weekly_budget else [], "meals": planned_meals}


@router.post("/meals/{meal_id}/consume", response_model=MealConsumeResponse)
async def consume_meal(
    meal_id: int,
    payload: MealConsumeRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    meal = await session.scalar(
        select(WeeklyMealAssignment).where(
            WeeklyMealAssignment.id == meal_id, WeeklyMealAssignment.user_id == user.id
        )
    )
    if not meal:
        raise HTTPException(404, "Planned meal not found")
    if meal.eaten:
        raise HTTPException(409, "This meal has already been consumed")
    recipe = await session.get(Recipe, meal.recipe_id, options=[selectinload(Recipe.ingredients)])
    if not recipe:
        raise HTTPException(404, "Recipe not found")

    canonical = {}
    for required in recipe.ingredients:
        ingredient = await session.scalar(
            select(Ingredient).where(func.lower(Ingredient.name) == required.ingredient_name.lower())
        )
        if ingredient:
            canonical[ingredient.id] = (ingredient, required.required_qty, required.unit)

    if payload.used_default_quantities:
        usage = [(ingredient_id, qty, unit) for ingredient_id, (_, qty, unit) in canonical.items()]
    else:
        if not payload.custom_ingredient_usage:
            raise HTTPException(422, "Custom ingredient usage is required")
        usage = []
        for item in payload.custom_ingredient_usage:
            if item.ingredient_id not in canonical:
                raise HTTPException(422, f"Ingredient {item.ingredient_id} is not part of this recipe")
            default_unit = canonical[item.ingredient_id][2]
            usage.append((item.ingredient_id, item.used_amount, item.unit or default_unit))

    pantry_items = (await session.scalars(
        select(PantryItem)
        .where(PantryItem.user_id == user.id)
        .order_by(PantryItem.expiration_date.is_(None), PantryItem.expiration_date, PantryItem.id)
    )).all()
    for ingredient_id, used_amount, used_unit in usage:
        ingredient_name = canonical[ingredient_id][0].name.lower()
        matching = [item for item in pantry_items if item.quantity > 0 and (
            item.ingredient_id == ingredient_id or
            (item.ingredient_id is None and item.ingredient_name.lower() == ingredient_name)
        )]
        remaining = used_amount
        for pantry_item in matching:
            available_in_used_unit = convert_quantity(pantry_item.quantity, pantry_item.unit, used_unit)
            if available_in_used_unit is None:
                continue
            consumed_in_used_unit = min(remaining, available_in_used_unit)
            consumed_in_pantry_unit = convert_quantity(consumed_in_used_unit, used_unit, pantry_item.unit)
            if consumed_in_pantry_unit is None:
                continue
            pantry_item.quantity = max(0.0, pantry_item.quantity - consumed_in_pantry_unit)
            pantry_item.ingredient_id = ingredient_id
            remaining -= consumed_in_used_unit
            if remaining <= 1e-9:
                break

    meal.eaten = True
    meal.eaten_at = datetime.utcnow()
    await session.commit()
    active = [item for item in pantry_items if item.quantity > 0 and item.ingredient_id is not None]
    return {
        "meal_id": meal.id,
        "eaten": True,
        "eaten_at": meal.eaten_at,
        "pantry_items": [{"id": item.id, "ingredient_id": item.ingredient_id,
                          "ingredient_name": item.ingredient_name, "quantity": round(item.quantity, 3),
                          "unit": item.unit, "expiration_date": item.expiration_date} for item in active],
    }
