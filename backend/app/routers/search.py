from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import Ingredient, Recipe, StorePrice, User
from ..schemas import UnifiedSearchResponse
from ..services.preferences import id_list, recipe_is_allowed
from ..services.catalog import package_quote

router=APIRouter(prefix="/api/search",tags=["search"])

@router.get("",response_model=UnifiedSearchResponse)
async def unified_search(q: str = Query(min_length=1,max_length=80), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    pattern=f"%{q.strip().lower()}%"
    recipes=(await session.scalars(select(Recipe).where(func.lower(Recipe.title).like(pattern)).options(selectinload(Recipe.ingredients)).limit(10))).all()
    ingredients=(await session.scalars(select(Ingredient).where(func.lower(Ingredient.name).like(pattern)).limit(10))).all()
    all_ingredients=(await session.scalars(select(Ingredient))).all()
    ingredient_ids={item.name.lower():item.id for item in all_ingredients}
    excluded=set(id_list(user.excluded_ingredient_ids))
    recipes=[recipe for recipe in recipes if recipe_is_allowed(recipe,excluded,ingredient_ids)]
    ingredients=[ingredient for ingredient in ingredients if ingredient.id not in excluded]
    dishes=[]
    for recipe in recipes:
        cost=0.0
        for item in recipe.ingredients:
            ingredient=next((value for value in all_ingredients if value.name.lower()==item.ingredient_name.lower()),None)
            price=await session.scalar(select(func.min(StorePrice.price_per_unit)).where(StorePrice.ingredient_name==item.ingredient_name.lower(),StorePrice.unit==item.unit,StorePrice.price_per_unit>0))
            quote=package_quote(item.ingredient_name,item.required_qty,item.unit,
                                package_size=ingredient.package_size if ingredient else None,
                                package_unit=ingredient.package_unit if ingredient else item.unit,
                                unit_price_usd=price,category=ingredient.category if ingredient else None)
            cost+=quote["estimated_cost"]
        dishes.append({"id":recipe.id,"title":recipe.title,"meal_type":recipe.meal_type,"estimated_cost_usd":round(max(.01,cost),2),"calories":recipe.calories})
    items=[]
    for ingredient in ingredients:
        price=await session.scalar(select(func.min(StorePrice.price_per_unit)).where(StorePrice.ingredient_name==ingredient.name,StorePrice.price_per_unit>0))
        unit=ingredient.package_unit or "g";quantity=1000 if unit=="g" else 1
        quote=package_quote(ingredient.name,quantity,unit,package_size=ingredient.package_size,package_unit=unit,unit_price_usd=price,category=ingredient.category)
        items.append({"id":ingredient.id,"name":ingredient.name,"estimated_cost_usd":quote["estimated_cost"],"unit":quote["normalized_unit"]})
    return {"dishes":dishes,"ingredients":items}
