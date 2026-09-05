import { useState } from "react";
import { RecipeDetailModal } from "./RecipeDetailModal";

export function RecipeCard({ recipe, headers, apiUrl = "", formatPrice }) {
  const [open, setOpen] = useState(false);
  return <>
    <article className="flex min-h-64 flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-1 flex-col p-5">
        <div className="flex justify-between gap-2"><span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">{recipe.meal_type}</span><span className="rounded-full bg-teal-100 px-3 py-1 text-xs font-bold text-teal-800">{recipe.pantry_match_percent}% pantry</span></div>
        <h3 className="mt-4 text-2xl font-bold">{recipe.title}</h3>
        <p className="mt-2 text-sm text-zinc-900/60">{recipe.missing_ingredients?.length ? recipe.missing_ingredients.map((item) => item.ingredient_name).join(", ") : "Everything is in your pantry."}</p>
        <div className="mt-auto pt-5"><div className="flex flex-wrap gap-2 text-xs font-semibold"><span className="rounded-lg bg-slate-100 px-2 py-1">◷ {recipe.prep_time} min</span><span className="rounded-lg bg-slate-100 px-2 py-1">P {recipe.protein_g}g · C {recipe.carbs_g}g · F {recipe.fat_g}g</span></div><div className="mt-3 flex items-center justify-between gap-2"><span className="rounded-full bg-amber-500 px-3 py-2 text-sm font-bold text-zinc-900">{recipe.estimated_missing_cost > 0 ? `Dish cost ${formatPrice(recipe.estimated_missing_cost)}` : "Pantry covered"}</span><button onClick={() => setOpen(true)} className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white">View & Source</button></div></div>
      </div>
    </article>
    {open && <RecipeDetailModal recipe={recipe} headers={headers} apiUrl={apiUrl} formatPrice={formatPrice} onClose={() => setOpen(false)} />}
  </>;
}
