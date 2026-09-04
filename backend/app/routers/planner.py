from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import PantryItem, Recipe, User, WeeklyMealAssignment
from ..schemas import ConsolidateRequest, ConsolidateResponse
from ..services.recipe_engine import shopping_plan

router = APIRouter(prefix="/api/planner", tags=["planner"])

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
