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
                options.append({"store_id":store.id,"store_name":store.name,"address":store.address,"distance_km":distance_km(lat,lon,store.lat,store.lon),"package_size":package_size,"package_unit":needed.unit,"packages_needed":packages,"price_per_package_usd":round(package_price,2),"unit_price_usd":round(package_price/package_size,4),"extended_price_usd":extended,"extended_price_local":round(extended*rate,2),"in_stock":inventory.in_stock if inventory else True,"navigation_url":f"https://www.google.com/maps/dir/?api=1&destination={store.lat},{store.lon}"})
            if not options:
                fallback=fallback_option(needed.ingredient_name,missing,needed.unit)
                options=[{"store_id":-1,"store_name":fallback["store_name"],"address":fallback["address"],"distance_km":1.2,"package_size":missing,"package_unit":needed.unit,"packages_needed":1,"price_per_package_usd":fallback["estimated_cost"],"unit_price_usd":round(fallback["estimated_cost"]/max(missing,1e-9),4),"extended_price_usd":fallback["estimated_cost"],"extended_price_local":round(fallback["estimated_cost"]*rate,2),"in_stock":True,"navigation_url":f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"}]
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
    assignments=[]; grouped={}
    for row in missing_rows:
        option=next((item for item in row["store_options"] if item["in_stock"]),row["store_options"][0])
        assignments.append({"ingredient_name":row["ingredient_name"],"quantity":row["missing_quantity"],"unit":row["unit"],"store_id":option["store_id"],"store_name":option["store_name"],"address":option["address"],"distance_km":option["distance_km"],"unit_price_usd":option["unit_price_usd"],"package_size":option["package_size"],"package_unit":option["package_unit"],"packages_needed":option["packages_needed"],"estimated_cost_usd":option["extended_price_usd"],"navigation_url":option["navigation_url"]})
        group=grouped.setdefault(option["store_id"],{"option":option,"ingredients":[],"subtotal":0.0})
        group["ingredients"].append(row["ingredient_name"]); group["subtotal"]+=option["extended_price_usd"]
    stores_out=[{"store_id":sid,"store_name":group["option"]["store_name"],"address":group["option"]["address"],"distance_km":group["option"]["distance_km"],"subtotal_usd":round(group["subtotal"],2),"navigation_url":group["option"]["navigation_url"],"ingredients":group["ingredients"]} for sid,group in grouped.items()]
    item_total=round(sum(item["estimated_cost_usd"] for item in assignments),2)
    travel_distance=round(sum(item["distance_km"] for item in stores_out),2); travel_penalty_cost=round(travel_distance*distance_penalty,2)
    total_with_travel=round(item_total+travel_penalty_cost,2); baseline_item_total=best_single["item_total_usd"] if best_single else item_total
    savings=round(max(0,baseline_item_total-item_total),2)
    best_split={"stores":[{"store_id":item["store_id"],"store_name":item["store_name"],"address":item["address"],"distance_km":item["distance_km"],"item_total_usd":item["subtotal_usd"],"navigation_url":item["navigation_url"],"ingredients":item["ingredients"]} for item in stores_out],"item_total_usd":item_total,"travel_penalty_usd":travel_penalty_cost,"total_with_travel_usd":total_with_travel,"savings_vs_single_usd":savings} if len(stores_out)>1 else None
    itemized={"assignments":assignments,"stores":stores_out,"ingredient_total_usd":item_total,"travel_distance_km":travel_distance,"travel_penalty_usd":travel_penalty_cost,"total_with_travel_usd":total_with_travel,"savings_vs_single_store_usd":savings}
    return {"recipe_id":recipe.id,"recipe_title":recipe.title,"ingredients":ingredient_rows,"total_estimated_cost_usd":item_total,"total_estimated_cost_local":round(item_total*rate,2),"local_currency":currency,"local_currency_symbol":symbol,"usd_to_local_rate":rate,"best_single_store":best_single,"multi_store_split":best_split,"itemized_sourcing":itemized}
