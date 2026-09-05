import { useEffect, useState } from "react";
import { StoreComparison } from "./StoreComparison";
import { useLocation } from "../context/LocationContext";

export function SourcingPanel({ recipeId, formatPrice, headers, apiUrl="" }) {
  const [source,setSource]=useState(null);
  const location=useLocation();
  useEffect(() => {
    if(!recipeId) return undefined;
    const controller=new AbortController();setSource(null);
    fetch(`${apiUrl}/api/recipes/${recipeId}/sourcing`,{headers,signal:controller.signal}).then(response=>response.ok?response.json():null).then(setSource).catch(error=>{if(error.name!=="AbortError")setSource(null)});
    return ()=>controller.abort();
  },[recipeId,location.latitude,location.longitude]);
  const itemized=source?.itemized_sourcing;
  if(!itemized) return <section className="rounded-3xl bg-zinc-900 p-6 text-white"><p className="text-sm font-bold text-slate-100">LOCAL SOURCING</p><div className="mt-3 h-9 w-36 animate-pulse rounded-lg bg-white/10"/><p className="mt-3 text-white/55">Loading item-level store comparisons…</p></section>;
  const coverageByName=new Map(source.ingredients.map(item=>[item.ingredient_name.toLowerCase(),item]));
  return <section className="rounded-3xl bg-zinc-900 p-6 text-white">
    <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-bold text-slate-100">ITEM-BY-ITEM SOURCING</p><h2 className="text-3xl font-bold text-amber-500">{formatPrice(itemized.ingredient_total_usd)}</h2><p className="text-sm text-white/55">{itemized.stores.length} stops · {itemized.travel_distance_km} km</p></div><div className="rounded-xl bg-white/10 px-4 py-3 text-sm"><span className="text-white/55">Savings vs one store</span><b className="ml-2 text-amber-500">{formatPrice(itemized.savings_vs_single_store_usd)}</b></div></header>
    <div className="mt-5 grid gap-3 sm:grid-cols-2">{source.closest_store&&<article className="rounded-2xl bg-white/10 p-4"><span className="rounded-full bg-emerald-600 px-3 py-1 text-xs font-bold">Closest Option</span><b className="mt-3 block text-lg">{source.closest_store.branch_name || source.closest_store.store_name}</b><p className="text-xs text-white/55">{source.closest_store.street_address || source.closest_store.address}</p><p className="text-sm text-white/55">{source.closest_store.distance_km} km · {formatPrice(source.closest_store.item_total_usd)}</p><a href={source.closest_store.navigation_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-bold text-emerald-400">Navigate ↗</a></article>}{source.value_recommended_store&&<article className="rounded-2xl border border-amber-500/50 bg-amber-500/10 p-4"><span className="rounded-full bg-amber-500 px-3 py-1 text-xs font-bold text-zinc-900">Best Value · Worth the Distance</span><b className="mt-3 block text-lg">{source.value_recommended_store.branch_name || source.value_recommended_store.store_name}</b><p className="text-xs text-white/55">{source.value_recommended_store.street_address || source.value_recommended_store.address}</p><p className="text-sm text-amber-200">{source.value_recommended_store.badge_label}</p><a href={source.value_recommended_store.navigation_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-bold text-amber-400">Navigate ↗</a></article>}</div>
    <div className="mt-5 space-y-2">{itemized.assignments.map(item=><StoreComparison key={item.ingredient_name} assignment={item} ingredient={coverageByName.get(item.ingredient_name.toLowerCase())} formatPrice={formatPrice} dark/>)}</div>
    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{itemized.stores.map(store=><article key={store.store_id} className="rounded-2xl bg-white/10 p-4"><div className="flex justify-between"><b>{store.branch_name || store.store_name}</b><b className="text-amber-500">{formatPrice(store.subtotal_usd)}</b></div><p className="text-[11px] text-white/55">{store.street_address || store.address}</p><p className="mt-1 text-xs text-white/55">Buy {store.ingredients.join(", ")}</p><a href={store.navigation_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-bold text-emerald-400">Open route ↗</a></article>)}</div>
  </section>;
}
