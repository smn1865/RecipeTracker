"""Small exhaustive basket optimizer for the local (<=3 store) catalog."""
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import LocalStore, StoreInventoryItem, StorePrice
from .location import distance_km, fallback_option, user_coordinates

async def optimize_basket(session: AsyncSession, ingredients: list, lat: float | None, lon: float | None, distance_penalty: float = .15, max_stores: int = 3):
    lat, lon = user_coordinates(lat, lon)
    stores = (await session.scalars(select(LocalStore))).all()
    by_store = defaultdict(list)
    for ingredient in ingredients:
        found = False
        for store in stores:
            inventory = await session.scalar(select(StoreInventoryItem).where(StoreInventoryItem.store_id == store.id, StoreInventoryItem.ingredient_name == ingredient.ingredient_name.lower()))
            if inventory and not inventory.in_stock:
                continue
            price = await session.scalar(select(StorePrice).where(StorePrice.store_id == store.id, StorePrice.ingredient_name == ingredient.ingredient_name.lower(), StorePrice.unit == ingredient.unit))
            if price:
                found = True
                by_store[store.id].append((ingredient, store, round(price.price_per_unit * ingredient.required_qty, 2)))
        if not found:
            fallback = fallback_option(ingredient.ingredient_name, ingredient.required_qty, ingredient.unit)
            synthetic = LocalStore(id=-1, name=fallback["store_name"], address=fallback["address"], lat=lat, lon=lon)
            by_store[-1].append((ingredient, synthetic, fallback["estimated_cost"]))
    def score(groups):
        item_cost = sum(cost for entries in groups.values() for _, _, cost in entries)
        travel = sum(distance_km(lat, lon, entries[0][1].lat, entries[0][1].lon) for entries in groups.values())
        return round(item_cost + travel * distance_penalty, 2), round(travel, 2), round(item_cost, 2)
    # Single baseline: choose the lowest feasible store per entire basket, otherwise local fallback pricing.
    all_ids = set(by_store)
    baseline_groups = {}
    if all_ids:
        candidates = [(sid, entries) for sid, entries in by_store.items() if len(entries) == len(ingredients)]
        if candidates:
            sid, entries = min(candidates, key=lambda p: sum(x[2] for x in p[1]) + distance_km(lat, lon, p[1][0][1].lat, p[1][0][1].lon) * distance_penalty)
            baseline_groups = {sid: entries}
    if not baseline_groups:
        for ingredient in ingredients:
            option = fallback_option(ingredient.ingredient_name, ingredient.required_qty, ingredient.unit)
            store = LocalStore(id=-1, name=option["store_name"], address=option["address"], lat=lat, lon=lon)
            baseline_groups.setdefault(-1, []).append((ingredient, store, option["estimated_cost"]))
    baseline_total, _, _ = score(baseline_groups)
    # Cheapest option for each ingredient, then reject if it would need too many stops.
    split = defaultdict(list)
    for ingredient in ingredients:
        candidates = [entry for entries in by_store.values() for entry in entries if entry[0] is ingredient]
        split[min(candidates, key=lambda entry: entry[2])[1].id].append(min(candidates, key=lambda entry: entry[2]))
    if len(split) > max_stores:
        split = baseline_groups
    split_total, travel, _ = score(split)
    use_split = len(split) > 1 and split_total < baseline_total
    selected = split if use_split else baseline_groups
    selected_total, selected_distance, _ = score(selected)
    assignments = []
    for entries in selected.values():
        store = entries[0][1]
        assignments.append({"store_name": store.name, "address": store.address, "distance_km": distance_km(lat, lon, store.lat, store.lon), "item_cost": round(sum(x[2] for x in entries), 2), "items": [{"ingredient_name": x[0].ingredient_name, "quantity": x[0].required_qty, "unit": x[0].unit} for x in entries]})
    return {"single_store_total": baseline_total, "optimized_total": selected_total, "travel_distance_km": selected_distance, "net_savings": round(max(0, baseline_total - selected_total), 2), "uses_multi_store": use_split, "assignments": assignments}
