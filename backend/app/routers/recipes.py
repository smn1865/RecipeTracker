from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..main import current_user
from ..models import Ingredient, LocalStore, PantryItem, Recipe, RecipeIngredient, StoreInventoryItem, StorePrice, User
from ..schemas import CustomRecipeCreate, CustomRecipeResponse, RecipeSourcingResponse
from ..services.ai_validator import validate_custom_recipe
from ..services.location import active_user_coordinates, distance_km, estimated_package_cost, fallback_option, get_currency_for_coords, user_coordinates
from ..services.recipe_matcher import recipe_coverage
from ..services.catalog import STORE_CHAINS, branch_name_for, full_street_address, package_quote, unique_physical_branches
from ..services.optimizer import choose_store_tradeoff

router=APIRouter(prefix="/api/recipes",tags=["recipes"])


@router.post("/custom", response_model=CustomRecipeResponse, status_code=201)
async def create_custom_recipe(
    payload: CustomRecipeCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    recipe_data = payload.model_dump()
    verdict = await validate_custom_recipe(recipe_data)
    if not verdict["is_valid"]:
        raise HTTPException(status_code=422, detail=verdict["rejection_reason"] or "Recipe moderation rejected this submission.")

    clean_ingredients = []
    for submitted in payload.ingredients:
        name = " ".join(submitted.ingredient_name.lower().split())
        clean_ingredients.append((name, submitted.grams))
        existing = await session.scalar(select(Ingredient).where(Ingredient.name == name))
        if not existing:
            session.add(Ingredient(name=name, category="community", package_size=500, package_unit="g"))

    recipe = Recipe(
        title=payload.title.strip(),
        instructions=payload.instructions.strip(),
        prep_time=payload.prep_time,
        calories=payload.calories,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        meal_type=payload.meal_type,
        tags="Community",
        serving_count=payload.serving_count,
        total_weight_grams=payload.total_weight_grams,
        is_community=True,
        submitted_by_user_id=user.id,
    )
    recipe.ingredients = [
        RecipeIngredient(ingredient_name=name, required_qty=grams, unit="g")
        for name, grams in clean_ingredients
    ]
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)
    return {
        "id": recipe.id,
        "title": recipe.title,
        "prep_time": recipe.prep_time,
        "serving_count": recipe.serving_count,
        "total_weight_grams": recipe.total_weight_grams,
        "calories": recipe.calories,
        "protein_g": recipe.protein_g,
        "fat_g": recipe.fat_g,
        "carbs_g": recipe.carbs_g,
        "meal_type": recipe.meal_type,
        "is_community": recipe.is_community,
        "ingredients": [{"ingredient_name": name, "grams": grams} for name, grams in clean_ingredients],
    }

@router.get("/{recipe_id}/sourcing",response_model=RecipeSourcingResponse)
async def recipe_sourcing(recipe_id: int, radius_km: float=Query(10,gt=0,le=50), distance_penalty: float=Query(.15,ge=0,le=5),
                          live_lat: float | None=Header(None,alias="X-User-Latitude"), live_lon: float | None=Header(None,alias="X-User-Longitude"),
                          user: User=Depends(current_user), session: AsyncSession=Depends(get_session)):
    recipe=await session.get(Recipe,recipe_id,options=[selectinload(Recipe.ingredients)])
    if not recipe: raise HTTPException(404,"Recipe not found")
    lat,lon=active_user_coordinates(live_lat,live_lon,user.lat,user.lon); currency,symbol,rate=get_currency_for_coords(lat,lon)
    pantry=(await session.scalars(select(PantryItem).where(PantryItem.user_id==user.id))).all()
    stores=[s for s in unique_physical_branches((await session.scalars(select(LocalStore))).all()) if s.name in STORE_CHAINS and distance_km(lat,lon,s.lat,s.lon)<=radius_km]
    ingredient_rows=[]
    coverage = await recipe_coverage(session, recipe.ingredients, pantry)
    for needed, coverage_row in zip(recipe.ingredients, coverage):
        missing=coverage_row["missing_quantity"]; options=[]
        if missing>0:
            for store in stores:
                price=await session.scalar(select(StorePrice).where(StorePrice.store_id==store.id,StorePrice.ingredient_name==needed.ingredient_name.lower(),StorePrice.unit==needed.unit))
                inventory=await session.scalar(select(StoreInventoryItem).where(StoreInventoryItem.store_id==store.id,StoreInventoryItem.ingredient_name==needed.ingredient_name.lower(),StoreInventoryItem.unit==needed.unit))
                canonical=await session.get(Ingredient,coverage_row["ingredient_id"]) if coverage_row["ingredient_id"] else None
                estimate=package_quote(needed.ingredient_name,missing,needed.unit,
                                       package_size=inventory.package_size if inventory else canonical.package_size if canonical else None,
                                       package_unit=inventory.unit if inventory else canonical.package_unit if canonical else needed.unit,
                                       package_price_usd=inventory.price_usd if inventory else None,
                                       unit_price_usd=price.price_per_unit if price else None,
                                       category=canonical.category if canonical else None,store_name=store.name)
                package_size=estimate["package_size"]
                package_price=estimate["price_per_package_usd"]
                packages=estimate["packages_needed"]; extended=round(max(.01,packages*package_price),2)
                maps_url=f"https://www.google.com/maps/dir/?api=1&destination={store.lat},{store.lon}"
                options.append({"store_id":store.id,"store_name":store.name,"branch_name":branch_name_for(store.name,store.address),"street_address":full_street_address(store.address),"address":store.address,"distance_km":distance_km(lat,lon,store.lat,store.lon),"package_size":package_size,"package_unit":estimate["package_unit"],"packages_needed":packages,"price_per_package_usd":round(package_price,2),"unit_price_usd":estimate["unit_price_usd"],"normalized_unit":estimate["normalized_unit"],"extended_price_usd":extended,"extended_price_local":round(extended*rate,2),"in_stock":inventory.in_stock if inventory else True,"navigation_url":maps_url,"price":round(extended*rate,2),"currency":currency,"maps_url":maps_url})
            if not options:
                fallback=fallback_option(needed.ingredient_name,missing,needed.unit)
                maps_url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
                options=[{"store_id":-1,"store_name":fallback["store_name"],"branch_name":"Local Supermarket - Central","street_address":fallback["address"],"address":fallback["address"],"distance_km":1.2,"package_size":fallback["package_size"],"package_unit":fallback["package_unit"],"packages_needed":fallback["packages_needed"],"price_per_package_usd":fallback["price_per_package_usd"],"unit_price_usd":fallback["unit_price_usd"],"normalized_unit":fallback["normalized_unit"],"extended_price_usd":fallback["estimated_cost"],"extended_price_local":round(fallback["estimated_cost"]*rate,2),"in_stock":True,"navigation_url":maps_url,"price":round(fallback["estimated_cost"]*rate,2),"currency":currency,"maps_url":maps_url}]
            options.sort(key=lambda x:(not x["in_stock"],x["extended_price_usd"]+x["distance_km"]*distance_penalty,x["distance_km"]))
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
            single_candidates.append({"store_id":store_id,"store_name":first["store_name"],"branch_name":first["branch_name"],"street_address":first["street_address"],"address":first["address"],"distance_km":first["distance_km"],"item_total_usd":item_total,"total_with_travel_usd":round(item_total+first["distance_km"]*distance_penalty,2),"navigation_url":first["navigation_url"]})
    best_single=min(single_candidates,key=lambda x:x["total_with_travel_usd"],default=None)
    closest_store,value_store=choose_store_tradeoff(single_candidates,currency,symbol,rate,distance_penalty_usd_per_km=distance_penalty)
    assignments=[]; grouped={}
    for row in missing_rows:
        option=next((item for item in row["store_options"] if item["in_stock"]),row["store_options"][0])
        assignments.append({"ingredient_name":row["ingredient_name"],"quantity":row["missing_quantity"],"unit":row["unit"],"store_id":option["store_id"],"store_name":option["store_name"],"branch_name":option["branch_name"],"street_address":option["street_address"],"address":option["address"],"distance_km":option["distance_km"],"unit_price_usd":option["unit_price_usd"],"normalized_unit":option["normalized_unit"],"package_size":option["package_size"],"package_unit":option["package_unit"],"packages_needed":option["packages_needed"],"estimated_cost_usd":option["extended_price_usd"],"navigation_url":option["navigation_url"]})
        group=grouped.setdefault(option["store_id"],{"option":option,"ingredients":[],"subtotal":0.0})
        group["ingredients"].append(row["ingredient_name"]); group["subtotal"]+=option["extended_price_usd"]
    stores_out=[{"store_id":sid,"store_name":group["option"]["store_name"],"branch_name":group["option"]["branch_name"],"street_address":group["option"]["street_address"],"address":group["option"]["address"],"distance_km":group["option"]["distance_km"],"subtotal_usd":round(group["subtotal"],2),"navigation_url":group["option"]["navigation_url"],"ingredients":group["ingredients"]} for sid,group in grouped.items()]
    item_total=round(sum(item["estimated_cost_usd"] for item in assignments),2)
    travel_distance=round(sum(item["distance_km"] for item in stores_out),2); travel_penalty_cost=round(travel_distance*distance_penalty,2)
    total_with_travel=round(item_total+travel_penalty_cost,2); baseline_item_total=best_single["item_total_usd"] if best_single else item_total
    savings=round(max(0,baseline_item_total-item_total),2)
    best_split={"stores":[{"store_id":item["store_id"],"store_name":item["store_name"],"branch_name":item["branch_name"],"street_address":item["street_address"],"address":item["address"],"distance_km":item["distance_km"],"item_total_usd":item["subtotal_usd"],"navigation_url":item["navigation_url"],"ingredients":item["ingredients"]} for item in stores_out],"item_total_usd":item_total,"travel_penalty_usd":travel_penalty_cost,"total_with_travel_usd":total_with_travel,"savings_vs_single_usd":savings} if len(stores_out)>1 else None
    itemized={"assignments":assignments,"stores":stores_out,"ingredient_total_usd":item_total,"travel_distance_km":travel_distance,"travel_penalty_usd":travel_penalty_cost,"total_with_travel_usd":total_with_travel,"savings_vs_single_store_usd":savings}
    public_ingredients=[]
    for row in ingredient_rows:
        distinct=[];seen_chains=set()
        for option in row["store_options"]:
            if option["store_name"] in seen_chains: continue
            seen_chains.add(option["store_name"]);distinct.append(option)
            if len(distinct)==3: break
        public_ingredients.append({**row,"store_options":distinct})
    return {"recipe_id":recipe.id,"recipe_title":recipe.title,"ingredients":public_ingredients,"total_estimated_cost_usd":item_total,"total_estimated_cost_local":round(item_total*rate,2),"local_currency":currency,"local_currency_symbol":symbol,"usd_to_local_rate":rate,"best_single_store":best_single,"multi_store_split":best_split,"itemized_sourcing":itemized,"closest_store":closest_store,"value_recommended_store":value_store}
