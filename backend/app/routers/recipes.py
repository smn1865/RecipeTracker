from itertools import combinations
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import LocalStore, PantryItem, Recipe, StoreInventoryItem, StorePrice, User
from ..schemas import RecipeSourcingResponse
from ..services.location import distance_km, fallback_option, get_currency_for_coords, user_coordinates
from ..services.recipe_matcher import recipe_coverage

router=APIRouter(prefix="/api/recipes",tags=["recipes"])

@router.get("/{recipe_id}/sourcing",response_model=RecipeSourcingResponse)
async def recipe_sourcing(recipe_id: int, radius_km: float=Query(10,gt=0,le=50), distance_penalty: float=Query(.15,ge=0,le=5), user: User=Depends(current_user), session: AsyncSession=Depends(get_session)):
    recipe=await session.get(Recipe,recipe_id,options=[selectinload(Recipe.ingredients)])
    if not recipe: raise HTTPException(404,"Recipe not found")
    lat,lon=user_coordinates(user.lat,user.lon); currency,symbol,rate=get_currency_for_coords(lat,lon)
    pantry=(await session.scalars(select(PantryItem).where(PantryItem.user_id==user.id))).all()
    stores=[s for s in (await session.scalars(select(LocalStore))).all() if distance_km(lat,lon,s.lat,s.lon)<=radius_km]
    ingredient_rows=[]
    coverage = await recipe_coverage(session, recipe.ingredients, pantry)
    for needed, coverage_row in zip(recipe.ingredients, coverage):
        missing=coverage_row["missing_quantity"]; options=[]
        if missing>0:
            for store in stores:
                price=await session.scalar(select(StorePrice).where(StorePrice.store_id==store.id,StorePrice.ingredient_name==needed.ingredient_name.lower(),StorePrice.unit==needed.unit))
                if not price: continue
                inventory=await session.scalar(select(StoreInventoryItem).where(StoreInventoryItem.store_id==store.id,StoreInventoryItem.ingredient_name==needed.ingredient_name.lower(),StoreInventoryItem.unit==needed.unit))
                package_size=inventory.package_size if inventory else (500 if needed.unit=="g" else 1)
                package_price=inventory.price_usd if inventory else price.price_per_unit*package_size
                packages=ceil(missing/package_size); extended=round(packages*package_price,2)
                options.append({"store_id":store.id,"store_name":store.name,"address":store.address,"distance_km":distance_km(lat,lon,store.lat,store.lon),"package_size":package_size,"package_unit":needed.unit,"packages_needed":packages,"price_per_package_usd":round(package_price,2),"extended_price_usd":extended,"extended_price_local":round(extended*rate,2),"in_stock":inventory.in_stock if inventory else True,"navigation_url":f"https://www.google.com/maps/dir/?api=1&destination={store.lat},{store.lon}"})
            if not options:
                fallback=fallback_option(needed.ingredient_name,missing,needed.unit)
                options=[{"store_id":-1,"store_name":fallback["store_name"],"address":fallback["address"],"distance_km":1.2,"package_size":missing,"package_unit":needed.unit,"packages_needed":1,"price_per_package_usd":fallback["estimated_cost"],"extended_price_usd":fallback["estimated_cost"],"extended_price_local":round(fallback["estimated_cost"]*rate,2),"in_stock":True,"navigation_url":f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"}]
            options.sort(key=lambda x:(not x["in_stock"],x["extended_price_usd"],x["distance_km"]))
        ingredient_rows.append({**coverage_row, "store_options":options})
    missing_rows=[row for row in ingredient_rows if row["missing_quantity"]>0]
    store_ids={option["store_id"] for row in missing_rows for option in row["store_options"] if option["in_stock"]}
    single_candidates=[]
    for store_id in store_ids:
        picked=[]
        for row in missing_rows:
            option=next((x for x in row["store_options"] if x["store_id"]==store_id and x["in_stock"]),None)
            if not option: break
            picked.append(option)
        if len(picked)==len(missing_rows) and picked:
            item_total=round(sum(x["extended_price_usd"] for x in picked),2); first=picked[0]
            single_candidates.append({"store_id":store_id,"store_name":first["store_name"],"address":first["address"],"distance_km":first["distance_km"],"item_total_usd":item_total,"total_with_travel_usd":round(item_total+first["distance_km"]*distance_penalty,2),"navigation_url":first["navigation_url"]})
    best_single=min(single_candidates,key=lambda x:x["total_with_travel_usd"],default=None)
    best_split=None
    for pair in combinations(store_ids,2):
        chosen=[]
        for row in missing_rows:
            candidates=[x for x in row["store_options"] if x["store_id"] in pair and x["in_stock"]]
            if not candidates: break
            chosen.append((row["ingredient_name"],min(candidates,key=lambda x:x["extended_price_usd"])))
        if len(chosen)!=len(missing_rows): continue
        grouped={}
        for name,option in chosen: grouped.setdefault(option["store_id"],{"option":option,"ingredients":[],"cost":0});grouped[option["store_id"]]["ingredients"].append(name);grouped[option["store_id"]]["cost"]+=option["extended_price_usd"]
        if len(grouped)<2: continue
        item_total=round(sum(g["cost"] for g in grouped.values()),2); travel=round(sum(g["option"]["distance_km"] for g in grouped.values())*distance_penalty,2); total=round(item_total+travel,2)
        if best_single and total>=best_single["total_with_travel_usd"]: continue
        stores_out=[{"store_id":sid,"store_name":g["option"]["store_name"],"address":g["option"]["address"],"distance_km":g["option"]["distance_km"],"item_total_usd":round(g["cost"],2),"navigation_url":g["option"]["navigation_url"],"ingredients":g["ingredients"]} for sid,g in grouped.items()]
        candidate={"stores":stores_out,"item_total_usd":item_total,"travel_penalty_usd":travel,"total_with_travel_usd":total,"savings_vs_single_usd":round(best_single["total_with_travel_usd"]-total,2)}
        if not best_split or total<best_split["total_with_travel_usd"]: best_split=candidate
    total=best_single["item_total_usd"] if best_single else round(sum(row["store_options"][0]["extended_price_usd"] for row in missing_rows),2)
    return {"recipe_id":recipe.id,"recipe_title":recipe.title,"ingredients":ingredient_rows,"total_estimated_cost_usd":total,"total_estimated_cost_local":round(total*rate,2),"local_currency":currency,"local_currency_symbol":symbol,"usd_to_local_rate":rate,"best_single_store":best_single,"multi_store_split":best_split}
