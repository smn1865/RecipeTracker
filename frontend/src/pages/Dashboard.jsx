import { useEffect, useState } from "react";
import { Header } from "../components/Header";
import { GlobalSearch } from "../components/GlobalSearch";
import { RecipeCard } from "../components/RecipeCard";
import { Pantry } from "./Pantry";
import { WeeklyPlanner } from "./WeeklyPlanner";

const FILTERS = ["All", "Breakfast", "Lunch", "Dinner", "Snacks", "High Protein", "Budget Friendly"];

export function Dashboard({ apiUrl, token, onHome, onProfile, onLogout, formatPrice, configureCurrency, currencySwitcher }) {
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
  return <main className="min-h-screen"><Header onHome={onHome} onProfile={onProfile} onLogout={onLogout} currencySwitcher={currencySwitcher}/><div className="mx-auto max-w-7xl px-6 py-8"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><p className="text-sm font-extrabold text-amber-600">ԲԱՐԻ ԱԽՈՐԺԱԿ</p><h1 className="text-4xl font-bold text-forest">Your Armenian smart pantry</h1></div><button onClick={onProfile} className="rounded-xl bg-white px-4 py-3 text-sm font-bold text-forest shadow-sm sm:hidden">Dietary Profile & Goals</button></div>
    {profile && <section className="mt-6 grid gap-4 md:grid-cols-4"><article className="rounded-3xl bg-white p-5 shadow-sm"><p className="text-xs font-bold text-sage">CURRENT BMI</p><b className="text-4xl text-forest">{profile.bmi}</b><p className="text-xs text-ink/45">{profile.weight_status}</p></article><article className="rounded-3xl bg-forest p-5 text-white"><p className="text-xs font-bold text-lime">DAILY ENERGY</p><b className="text-4xl">{profile.daily_calories}</b><p className="text-xs text-white/55">kcal target</p></article>{[["Protein", profile.protein_g, "bg-mint"], ["Carbs · Fats", `${profile.carbs_g}g · ${profile.fat_g}g`, "bg-lime/50"]].map(([label,value,color]) => <article key={label} className={`rounded-3xl p-5 ${color}`}><p className="text-xs font-bold text-sage">{label.toUpperCase()}</p><b className="text-3xl text-forest">{typeof value === "number" ? `${value}g` : value}</b></article>)}</section>}
    <div className="mt-7"><WeeklyPlanner recipes={recipes} formatPrice={formatPrice} headers={headers} apiUrl={apiUrl}/></div>
    <section className="mt-10 rounded-[2rem] bg-white/50 p-5 sm:p-7"><div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center"><div><p className="text-xs font-bold text-sage">SEARCH & LOCAL SOURCING</p><h2 className="text-2xl font-bold text-forest">Find a dish or ingredient</h2></div><GlobalSearch headers={headers} apiUrl={apiUrl} formatPrice={formatPrice}/></div><div className="mt-6 flex gap-2 overflow-x-auto pb-2">{FILTERS.map(item => <button key={item} onClick={() => { setFilter(item); loadRecipes(item); }} className={filter === item ? "whitespace-nowrap rounded-full bg-forest px-4 py-2 text-sm font-bold text-white" : "whitespace-nowrap rounded-full bg-white px-4 py-2 text-sm font-bold text-ink/60"}>{item}</button>)}</div><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{recipes.slice(0, shown).map(recipe => <RecipeCard key={recipe.id} recipe={recipe} headers={headers} apiUrl={apiUrl} formatPrice={formatPrice}/>)}</div>{shown < recipes.length && <div className="mt-6 text-center"><button onClick={() => setShown(value => value + 6)} className="rounded-xl bg-forest px-5 py-3 font-bold text-white">Show more</button></div>}</section>
    <div className="mt-8"><Pantry headers={headers} apiUrl={apiUrl}/></div>
  </div></main>;
}
