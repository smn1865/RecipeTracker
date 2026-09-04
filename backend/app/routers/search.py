from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import Ingredient, Recipe, StorePrice, User
from ..schemas import UnifiedSearchResponse

router=APIRouter(prefix="/api/search",tags=["search"])

@router.get("",response_model=UnifiedSearchResponse)
async def unified_search(q: str = Query(min_length=1,max_length=80), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    pattern=f"%{q.strip().lower()}%"
    recipes=(await session.scalars(select(Recipe).where(func.lower(Recipe.title).like(pattern)).options(selectinload(Recipe.ingredients)).limit(10))).all()
    ingredients=(await session.scalars(select(Ingredient).where(func.lower(Ingredient.name).like(pattern)).limit(10))).all()
    dishes=[]
    for recipe in recipes:
        cost=0.0
        for item in recipe.ingredients:
            price=await session.scalar(select(func.min(StorePrice.price_per_unit)).where(StorePrice.ingredient_name==item.ingredient_name.lower(),StorePrice.unit==item.unit))
            cost+=(price or (.005 if item.unit=="g" else .75))*item.required_qty
        dishes.append({"id":recipe.id,"title":recipe.title,"meal_type":recipe.meal_type,"estimated_cost_usd":round(cost,2),"calories":recipe.calories})
    items=[]
    for ingredient in ingredients:
        price=await session.scalar(select(func.min(StorePrice.price_per_unit)).where(StorePrice.ingredient_name==ingredient.name))
        items.append({"id":ingredient.id,"name":ingredient.name,"estimated_cost_usd":round((price or .005)*1000,2),"unit":"kg"})
    return {"dishes":dishes,"ingredients":items}
