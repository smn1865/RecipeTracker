from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import PantryItem, Recipe, User, WeeklyMealAssignment
from ..schemas import AutoGenerateRequest, AutoGenerateResponse, ConsolidateRequest, ConsolidateResponse
from ..services.recipe_engine import shopping_plan
from ..services.location import get_currency_for_coords, options_for_ingredient

router = APIRouter(prefix="/api/planner", tags=["planner"])
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SLOTS = ["Breakfast", "Lunch", "Dinner"]

@router.post("/auto-generate", response_model=AutoGenerateResponse)
async def auto_generate(payload: AutoGenerateRequest, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    recipes = (await session.scalars(select(Recipe).options(selectinload(Recipe.ingredients)))).all()
    pantry = (await session.scalars(select(PantryItem).where(PantryItem.user_id==user.id))).all()
    if not recipes: raise HTTPException(409, "Recipe catalog is empty")
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
    meals=[{"day":d,"slot":s,"recipe_id":r.id,"title":r.title,"estimated_cost_usd":recipe_costs[r.id],"calories":r.calories,"protein_g":r.protein_g,"carbs_g":r.carbs_g,"fat_g":r.fat_g} for d,s,r in chosen]
    for meal in meals: session.add(WeeklyMealAssignment(user_id=user.id,day=meal["day"],slot=meal["slot"],recipe_id=meal["recipe_id"]))
    await session.commit()
    return {"meals":meals,"total_cost_usd":round(total,2),"total_cost_local":round(total*rate,2),"local_currency":currency,"local_currency_symbol":symbol,"usd_to_local_rate":rate,"saved_via_overlap_usd":round(max(0,naive-total),2),"ingredients":aggregated,"total_calories":sum(r.calories for _,_,r in chosen),"total_protein_g":round(sum(r.protein_g for _,_,r in chosen),1),"total_carbs_g":round(sum(r.carbs_g for _,_,r in chosen),1),"total_fat_g":round(sum(r.fat_g for _,_,r in chosen),1),"weekly_budget":payload.weekly_budget,"exceeds_budget":bool(payload.weekly_budget and total>payload.weekly_budget)}

@router.post("/consolidate", response_model=ConsolidateResponse)
async def consolidate(payload: ConsolidateRequest, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    if len(payload.assignments) > 21: raise HTTPException(422, "A week has at most 21 meal slots")
    pantry = (await session.scalars(select(PantryItem).where(PantryItem.user_id==user.id))).all()
    total, needs = 0.0, []
    for assignment in payload.assignments:
        recipe = await session.get(Recipe, assignment.recipe_id, options=[selectinload(Recipe.ingredients)])
        if not recipe: raise HTTPException(404, f"Recipe {assignment.recipe_id} not found")
        _, cost = await shopping_plan(session, user, recipe, pantry)
        total += cost
        needs.extend(recipe.ingredients)
        session.add(WeeklyMealAssignment(user_id=user.id, day=assignment.day, slot=assignment.slot, recipe_id=recipe.id))
    await session.commit()
    return {"total_cost":round(total,2),"weekly_budget":payload.weekly_budget,"exceeds_budget":total>payload.weekly_budget,"missing_ingredients":[{"ingredient_name":i.ingredient_name,"quantity":i.required_qty,"unit":i.unit} for i in needs],"swap_suggestions":["Swap salmon meals for tofu stir fry.","Choose lentil soup or chickpea bowls for budget-friendly lunches."] if total>payload.weekly_budget else []}
