import { useMemo, useState } from "react";
import { LocationBadge } from "../components/LocationBadge";

const EMPTY_RECIPE = {
  title: "",
  prep_time: 30,
  serving_count: 2,
  total_weight_grams: 500,
  calories: 600,
  protein_g: 30,
  carbs_g: 75,
  fat_g: 20,
  meal_type: "Dinner",
  instructions: "",
};

function Field({ label, className = "", ...props }) {
  return <label className={`block text-sm font-bold text-slate-800 ${className}`}>{label}<input {...props} className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"/></label>;
}

export function AddRecipe({ headers, apiUrl = "", onCreated }) {
  const [form, setForm] = useState(EMPTY_RECIPE);
  const [ingredients, setIngredients] = useState([{ ingredient_name: "", grams: 100 }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState(null);
  const macroCalories = useMemo(() => Math.round(4 * Number(form.protein_g) + 4 * Number(form.carbs_g) + 9 * Number(form.fat_g)), [form.protein_g, form.carbs_g, form.fat_g]);
  const ingredientWeight = useMemo(() => ingredients.reduce((sum, item) => sum + Number(item.grams || 0), 0), [ingredients]);

  function set(field, value) { setForm(current => ({ ...current, [field]: value })); }
  function updateIngredient(index, field, value) { setIngredients(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item)); }

  async function submit(event) {
    event.preventDefault();
    setBusy(true); setError(""); setCreated(null);
    const payload = {
      ...form,
      prep_time: Number(form.prep_time),
      serving_count: Number(form.serving_count),
      total_weight_grams: Number(form.total_weight_grams),
      calories: Number(form.calories),
      protein_g: Number(form.protein_g),
      carbs_g: Number(form.carbs_g),
      fat_g: Number(form.fat_g),
      instructions: form.instructions.trim() || "Prepare and combine the listed ingredients.",
      ingredients: ingredients.map(item => ({ ingredient_name: item.ingredient_name.trim(), grams: Number(item.grams) })),
    };
    try {
      const response = await fetch(`${apiUrl}/api/recipes/custom`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join(" · ") : data.detail;
        throw new Error(detail || "Recipe moderation rejected this submission.");
      }
      setCreated(data);
      setForm(EMPTY_RECIPE);
      setIngredients([{ ingredient_name: "", grams: 100 }]);
    } catch (submitError) {
      setError(submitError.message || "Could not submit this recipe.");
    } finally {
      setBusy(false);
    }
  }

  return <section className="mx-auto max-w-5xl">
    <div className="rounded-[2rem] bg-gradient-to-br from-emerald-800 via-emerald-700 to-slate-900 p-7 text-white shadow-xl sm:p-10">
      <span className="inline-flex rounded-full bg-amber-400 px-3 py-1 text-xs font-black text-slate-900">COMMUNITY KITCHEN</span>
      <div className="mt-4 flex flex-wrap items-center gap-3"><h1 className="text-4xl font-extrabold">Share a recipe with BariAkhorzhak</h1><LocationBadge/></div>
      <p className="mt-3 max-w-2xl text-emerald-50">Each submission is checked for plausible nutrition, ingredient weights, and dish structure before it joins the shared recipe library.</p>
    </div>

    <form onSubmit={submit} className="mt-6 space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-bold text-slate-900">Dish details</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Field required label="Recipe title" value={form.title} onChange={event => set("title", event.target.value)} className="lg:col-span-2" placeholder="e.g. Apricot chicken pilaf"/>
          <Field required type="number" min="1" max="1440" label="Prep time (minutes)" value={form.prep_time} onChange={event => set("prep_time", event.target.value)}/>
          <Field required type="number" min="1" max="50" label="Servings" value={form.serving_count} onChange={event => set("serving_count", event.target.value)}/>
          <Field required type="number" min="1" max="20000" step="any" label="Total weight (g)" value={form.total_weight_grams} onChange={event => set("total_weight_grams", event.target.value)}/>
          <label className="block text-sm font-bold text-slate-800">Meal type<select value={form.meal_type} onChange={event => set("meal_type", event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-emerald-600">{["Breakfast", "Lunch", "Dinner", "Snack"].map(item => <option key={item}>{item}</option>)}</select></label>
          <label className="block text-sm font-bold text-slate-800 md:col-span-2">Preparation instructions<textarea value={form.instructions} onChange={event => set("instructions", event.target.value)} rows="3" className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-emerald-600" placeholder="Describe the preparation steps…"/></label>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold text-slate-900">Nutrition totals</h2><p className="text-sm text-slate-600">Enter totals for the complete dish.</p></div><span className={`rounded-full px-3 py-2 text-xs font-bold ${Math.abs(Number(form.calories)-macroCalories) <= Math.max(80, macroCalories*.3) ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-700"}`}>Macro estimate: {macroCalories} kcal</span></div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field required type="number" min="1" label="Calories" value={form.calories} onChange={event => set("calories", event.target.value)}/>
          <Field required type="number" min="0" step="any" label="Protein (g)" value={form.protein_g} onChange={event => set("protein_g", event.target.value)}/>
          <Field required type="number" min="0" step="any" label="Carbs (g)" value={form.carbs_g} onChange={event => set("carbs_g", event.target.value)}/>
          <Field required type="number" min="0" step="any" label="Fat (g)" value={form.fat_g} onChange={event => set("fat_g", event.target.value)}/>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold text-slate-900">Ingredients</h2><p className="text-sm text-slate-600">Ingredient sum: {ingredientWeight.toLocaleString()} g</p></div><button type="button" onClick={() => setIngredients(current => [...current, { ingredient_name: "", grams: 100 }])} className="rounded-xl bg-teal-100 px-4 py-2 text-sm font-bold text-teal-800">+ Add ingredient</button></div>
        <div className="mt-5 space-y-3">{ingredients.map((item, index) => <div key={index} className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-[1fr_160px_auto]"><input required value={item.ingredient_name} onChange={event => updateIngredient(index, "ingredient_name", event.target.value)} placeholder="Ingredient name" className="rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-emerald-600"/><input required type="number" min="0.1" max="5000" step="any" value={item.grams} onChange={event => updateIngredient(index, "grams", event.target.value)} aria-label={`Ingredient ${index + 1} grams`} className="rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-emerald-600"/><button type="button" disabled={ingredients.length === 1} onClick={() => setIngredients(current => current.filter((_, itemIndex) => itemIndex !== index))} className="rounded-xl px-4 py-2 font-bold text-slate-500 hover:bg-amber-50 hover:text-amber-700 disabled:opacity-30">Remove</button></div>)}</div>
      </section>

      {error && <p role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 font-semibold text-amber-800">{error}</p>}
      {created && <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-900"><p><b>Recipe approved.</b> {created.title} is now in the community catalog.</p><button type="button" onClick={onCreated} className="rounded-xl bg-emerald-700 px-4 py-2 font-bold text-white">View recipes →</button></div>}
      <button disabled={busy} className="w-full rounded-2xl bg-emerald-600 px-6 py-4 text-lg font-extrabold text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-700 disabled:cursor-wait disabled:opacity-60">{busy ? "AI Moderating Recipe Plausibility..." : "Submit for AI moderation"}</button>
    </form>
  </section>;
}
