from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import Ingredient, LocalStore, Recipe, RecipeIngredient, StoreInventoryItem, StorePrice, User
from ..schemas import IngredientStoresResponse
from ..services.location import distance_km, get_currency_for_coords, generated_neighborhood_options, user_coordinates

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])

@router.get("/{ingredient_id}/stores", response_model=IngredientStoresResponse)
async def ingredient_stores(ingredient_id: int, sort_by: str = Query("price", pattern="^(price|distance)$"), user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    ingredient=await session.get(Ingredient,ingredient_id)
    if not ingredient: raise HTTPException(404,"Ingredient not found")
    lat,lon=user_coordinates(user.lat,user.lon); currency,symbol,rate=get_currency_for_coords(lat,lon)
    rows=[]
    stores=(await session.scalars(select(LocalStore))).all()
    for store in stores:
        price=await session.scalar(select(StorePrice).where(StorePrice.store_id==store.id,StorePrice.ingredient_name==ingredient.name))
        if not price: continue
        inventory=await session.scalar(select(StoreInventoryItem).where(StoreInventoryItem.store_id==store.id,StoreInventoryItem.ingredient_name==ingredient.name))
        usd=round(price.price_per_unit*1000,2) if price.unit=="g" else round(price.price_per_unit,2)
        rows.append({"store_id":store.id,"store_name":store.name,"address":store.address,"distance_km":distance_km(lat,lon,store.lat,store.lon),"price_usd":usd,"price_local":round(usd*rate,2),"unit":"kg" if price.unit=="g" else price.unit,"in_stock":inventory.in_stock if inventory else True,"navigation_url":f"https://www.google.com/maps/dir/?api=1&destination={store.lat},{store.lon}"})
    if not rows:
        for index,option in enumerate(generated_neighborhood_options(ingredient.name,1000,"g"),1):
            rows.append({"store_id":-index,"store_name":option["store_name"],"address":option["address"],"distance_km":option["distance_km"],"price_usd":option["estimated_cost"],"price_local":round(option["estimated_cost"]*rate,2),"unit":"kg","in_stock":True,"navigation_url":f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"})
    rows.sort(key=lambda row: row["price_usd"] if sort_by=="price" else row["distance_km"])
    recipe_row=(await session.execute(select(Recipe.id,Recipe.title).join(RecipeIngredient,RecipeIngredient.recipe_id==Recipe.id).where(RecipeIngredient.ingredient_name==ingredient.name).limit(1))).first()
    return {"ingredient":{"id":ingredient.id,"name":ingredient.name,"calories_per_100g":ingredient.calories_per_100g,"protein_g_per_100g":ingredient.protein_g_per_100g,"fat_g_per_100g":ingredient.fat_g_per_100g,"carbs_g_per_100g":ingredient.carbs_g_per_100g,"fiber_g_per_100g":ingredient.fiber_g_per_100g},"suggested_recipe_id":recipe_row.id if recipe_row else None,"suggested_recipe_title":recipe_row.title if recipe_row else None,"local_currency":currency,"local_currency_symbol":symbol,"usd_to_local_rate":rate,"stores":rows}
