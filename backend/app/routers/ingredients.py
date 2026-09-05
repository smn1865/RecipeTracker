from urllib.parse import quote
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import Ingredient, LocalStore, Recipe, RecipeIngredient, StoreInventoryItem, StorePrice, User
from ..schemas import IngredientStoresResponse
from ..services.location import active_user_coordinates, distance_km, estimated_package_cost, get_currency_for_coords, generated_neighborhood_options, user_coordinates
from ..services.catalog import STORE_CHAINS, branch_name_for, full_street_address, package_quote, unique_physical_branches

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])

@router.get("/{ingredient_id}/stores", response_model=IngredientStoresResponse)
async def ingredient_stores(ingredient_id: int, sort_by: str = Query("price", pattern="^(price|distance)$"),
                            live_lat: float | None=Header(None,alias="X-User-Latitude"), live_lon: float | None=Header(None,alias="X-User-Longitude"),
                            user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    ingredient=await session.get(Ingredient,ingredient_id)
    if not ingredient: raise HTTPException(404,"Ingredient not found")
    lat,lon=active_user_coordinates(live_lat,live_lon,user.lat,user.lon); currency,symbol,rate=get_currency_for_coords(lat,lon)
    rows=[]
    stores=[store for store in unique_physical_branches((await session.scalars(select(LocalStore))).all()) if store.name in STORE_CHAINS]
    for store in stores:
        price=await session.scalar(select(StorePrice).where(StorePrice.store_id==store.id,StorePrice.ingredient_name==ingredient.name))
        inventory=await session.scalar(select(StoreInventoryItem).where(StoreInventoryItem.store_id==store.id,StoreInventoryItem.ingredient_name==ingredient.name))
        source_unit=price.unit if price else inventory.unit if inventory else ingredient.package_unit or "g"
        display_quantity=1000 if source_unit.lower()=="g" else 1
        estimate=package_quote(ingredient.name,display_quantity,source_unit,
                               package_size=inventory.package_size if inventory else ingredient.package_size,
                               package_unit=inventory.unit if inventory else ingredient.package_unit or source_unit,
                               package_price_usd=inventory.price_usd if inventory else None,
                               unit_price_usd=price.price_per_unit if price else None,
                               category=ingredient.category,store_name=store.name)
        usd=round(max(.01,estimate["estimated_cost"]),2)
        maps_url=f"https://www.google.com/maps/dir/?api=1&destination={store.lat},{store.lon}"
        rows.append({"store_id":store.id,"store_name":store.name,"branch_name":branch_name_for(store.name,store.address),"street_address":full_street_address(store.address),"address":store.address,"distance_km":distance_km(lat,lon,store.lat,store.lon),"price_usd":usd,"price_local":round(usd*rate,2),"unit":estimate["normalized_unit"],"in_stock":inventory.in_stock if inventory else True,"navigation_url":maps_url,"price":round(usd*rate,2),"currency":currency,"maps_url":maps_url})
    if not rows:
        for index,option in enumerate(generated_neighborhood_options(ingredient.name,1000,"g"),1):
            maps_url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
            rows.append({"store_id":-index,"store_name":option["store_name"],"branch_name":f'{option["store_name"]} - Central',"street_address":option["address"],"address":option["address"],"distance_km":option["distance_km"],"price_usd":option["estimated_cost"],"price_local":round(option["estimated_cost"]*rate,2),"unit":"kg","in_stock":True,"navigation_url":maps_url,"price":round(option["estimated_cost"]*rate,2),"currency":currency,"maps_url":maps_url})
    rows.sort(key=lambda row: (not row["in_stock"],row["price_usd"]+row["distance_km"]*.15) if sort_by=="price" else (not row["in_stock"],row["distance_km"],row["price_usd"]))
    distinct=[];seen_chains=set()
    for row in rows:
        if row["store_name"] in seen_chains: continue
        seen_chains.add(row["store_name"]);distinct.append(row)
        if len(distinct)==3: break
    rows=distinct
    recipe_row=(await session.execute(select(Recipe.id,Recipe.title).join(RecipeIngredient,RecipeIngredient.recipe_id==Recipe.id).where(RecipeIngredient.ingredient_name==ingredient.name).limit(1))).first()
    return {"ingredient":{"id":ingredient.id,"name":ingredient.name,"calories_per_100g":ingredient.calories_per_100g,"protein_g_per_100g":ingredient.protein_g_per_100g,"fat_g_per_100g":ingredient.fat_g_per_100g,"carbs_g_per_100g":ingredient.carbs_g_per_100g,"fiber_g_per_100g":ingredient.fiber_g_per_100g},"suggested_recipe_id":recipe_row.id if recipe_row else None,"suggested_recipe_title":recipe_row.title if recipe_row else None,"local_currency":currency,"local_currency_symbol":symbol,"usd_to_local_rate":rate,"stores":rows}
