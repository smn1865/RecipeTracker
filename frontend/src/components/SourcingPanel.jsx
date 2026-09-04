import { useState } from "react";
import { PriceTag } from "./PriceTag";

export function SourcingPanel({ recipeId, plan, formatPrice, headers, apiUrl = "" }) {
  const [optimized, setOptimized] = useState(null);
  async function optimize() {
    const response = await fetch(`${apiUrl}/api/sourcing/optimize`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ recipe_id: recipeId }) });
    if (response.ok) setOptimized(await response.json());
  }
  return <section className="rounded-3xl bg-forest p-6 text-white"><div className="flex items-center justify-between"><div><p className="text-sm font-bold text-lime">LOCAL SOURCING</p><h2 className="text-2xl font-bold">{formatPrice(plan.total_cost)}</h2></div><button onClick={optimize} className="rounded-xl bg-lime px-4 py-2 text-sm font-bold text-forest">Multi-Store Optimizer</button></div>{optimized && <div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="rounded-xl bg-white/10 p-4"><b>Single Store Total</b><p>{formatPrice(optimized.single_store_total)}</p></div><div className="rounded-xl bg-white/10 p-4"><b>Multi-Store Split Total</b><p>{formatPrice(optimized.optimized_total)} · {optimized.travel_distance_km} km</p><span className="text-lime">Net savings: {formatPrice(optimized.net_savings)}</span></div></div>}<div className="mt-4 grid gap-3">{plan.items.map(item=><article key={item.ingredient_name} className="rounded-xl bg-white/10 p-4"><b>{item.ingredient_name} · {item.quantity}{item.unit}</b><div className="mt-2"><PriceTag totalUsd={item.best_option.estimated_cost} formatPrice={formatPrice}/></div></article>)}</div></section>;
}
