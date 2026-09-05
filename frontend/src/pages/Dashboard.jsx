import { useEffect, useState } from "react";
import { Header } from "../components/Header";
import { GlobalSearch } from "../components/GlobalSearch";
import { RecipeCard } from "../components/RecipeCard";
import { LocationBadge } from "../components/LocationBadge";

const FILTERS = ["All", "Breakfast", "Lunch", "Dinner", "Snacks", "High Protein", "Budget Friendly"];

export function Dashboard({ apiUrl, token, onHome, onNavigate, activePath, onLogout, formatPrice, configureCurrency, currencySwitcher }) {
  const headers = { Authorization: `Bearer ${token}` };
  const [profile, setProfile] = useState(null), [recipes, setRecipes] = useState([]), [filter, setFilter] = useState("All"), [shown, setShown] = useState(9);
  async function loadRecipes(choice = filter) {
    const tag = ["High Protein", "Budget Friendly"].includes(choice) ? choice : null;
    const response = await fetch(`${apiUrl}/recipes/generate-smart`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ category: tag ? "All" : choice, tag, limit: 24 }) });
    setRecipes(response.ok ? await response.json() : []); setShown(9);
  }
  useEffect(() => {
    fetch(`${apiUrl}/nutrition/profile`, { headers }).then(r => r.json()).then(setProfile);
    fetch(`${apiUrl}/auth/profile`, { headers }).then(r => r.json()).then(configureCurrency);
    loadRecipes("All");
  }, []);
  return <main className="min-h-screen bg-slate-100"><Header onHome={onHome} onNavigate={onNavigate} activePath={activePath} onLogout={onLogout} currencySwitcher={currencySwitcher}/><div className="mx-auto max-w-7xl px-6 py-8"><div><p className="text-sm font-extrabold text-slate-800/70">ԲԱՐԻ ԱԽՈՐԺԱԿ</p><div className="flex flex-wrap items-center gap-3"><h1 className="text-4xl font-bold text-zinc-900">Your Armenian smart pantry</h1><LocationBadge/></div></div>
    {profile && <section className="mt-6 grid gap-4 md:grid-cols-4"><article className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm"><p className="text-xs font-bold text-emerald-600">CURRENT BMI</p><b className="text-4xl text-emerald-800">{profile.bmi}</b><p className="text-xs text-slate-600">{profile.weight_status}</p></article><article className="rounded-3xl bg-gradient-to-br from-emerald-600 to-emerald-800 p-5 text-white"><p className="text-xs font-bold text-emerald-100">DAILY ENERGY</p><b className="text-4xl">{profile.daily_calories}</b><p className="text-xs text-white/70">kcal target</p></article>{[["Protein", profile.protein_g, "border-teal-100 bg-teal-100"], ["Carbs · Fats", `${profile.carbs_g}g · ${profile.fat_g}g`, "border-amber-200 bg-amber-50"]].map(([label,value,color]) => <article key={label} className={`rounded-3xl border p-5 ${color}`}><p className="text-xs font-bold text-slate-600">{label.toUpperCase()}</p><b className="text-3xl text-slate-900">{typeof value === "number" ? `${value}g` : value}</b></article>)}</section>}
    <section className="mt-10 rounded-[2rem] border border-slate-800/10 bg-white p-5 sm:p-7"><div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center"><div><p className="text-xs font-bold text-emerald-600">SEARCH & LOCAL SOURCING</p><h2 className="text-2xl font-bold text-emerald-700">Find a dish or ingredient</h2></div><GlobalSearch headers={headers} apiUrl={apiUrl} formatPrice={formatPrice}/></div><div className="mt-6 flex gap-2 overflow-x-auto pb-2">{FILTERS.map(item => <button key={item} onClick={() => { setFilter(item); loadRecipes(item); }} className={filter === item ? "whitespace-nowrap rounded-full bg-emerald-700 px-4 py-2 text-sm font-bold text-white" : "whitespace-nowrap rounded-full bg-white px-4 py-2 text-sm font-bold text-zinc-900/60"}>{item}</button>)}</div><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{recipes.slice(0, shown).map(recipe => <RecipeCard key={recipe.id} recipe={recipe} headers={headers} apiUrl={apiUrl} formatPrice={formatPrice}/>)}</div>{shown < recipes.length && <div className="mt-6 text-center"><button onClick={() => setShown(value => value + 6)} className="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white">Show more</button></div>}</section>
  </div></main>;
}
