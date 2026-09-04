import { useEffect, useMemo, useState } from "react";
import { BrandMark } from "../components/Header";

const FALLBACK = { lat: 40.1872, lon: 44.5152 };
const GOALS = [
  ["weight_loss", "Weight Loss", "Caloric deficit with filling, protein-forward meals"],
  ["muscle_gain", "Muscle Gain", "Hypertrophy support and protein-dense recipes"],
  ["maintenance", "Weight Maintenance", "Balanced energy and sustainable variety"],
  ["budget_first", "Budget-First", "Prioritize pantry overlap and the lowest AMD basket"],
];

function Input({ label, error, ...props }) {
  return <label className="block text-sm font-bold text-ink/75">{label}<input {...props} className={`mt-1 w-full rounded-xl border bg-white px-4 py-3 outline-none focus:ring-4 focus:ring-mint ${error ? "border-amber-500" : "border-forest/10"}`}/>{error && <small className="text-amber-700">{error}</small>}</label>;
}

export function Register({ apiUrl, onSuccess, onHome }) {
  const [step, setStep] = useState(1), [busy, setBusy] = useState(false), [error, setError] = useState(""), [options, setOptions] = useState({ recipes: [], ingredients: [] }), [ingredientQuery, setIngredientQuery] = useState("");
  const [form, setForm] = useState({
    name: "", email: "", password: "", age: 30, gender: "female", height_cm: 165, weight_kg: 65,
    address: "", lat: FALLBACK.lat, lon: FALLBACK.lon, health_goal: "maintenance", weight_goal: "maintenance",
    target_calories: 2000, macro_preference: "balanced", daily_routine: "desk", exercise_frequency: "2-3",
    exercise_intensity: "moderate", daily_movement: "5000_10000", activity_level: "moderate",
    favorite_meal_ids: [], excluded_ingredient_ids: [],
  });
  const set = (key, value) => setForm(current => ({ ...current, [key]: value }));
  useEffect(() => { fetch(`${apiUrl}/auth/onboarding-options`).then(r => r.json()).then(setOptions); }, []);
  const ingredientMatches = useMemo(() => options.ingredients.filter(item => item.name.toLowerCase().includes(ingredientQuery.toLowerCase()) && !form.excluded_ingredient_ids.includes(item.id)).slice(0, 8), [ingredientQuery, options, form.excluded_ingredient_ids]);

  function chooseGoal(goal) {
    setForm(current => ({ ...current, health_goal: goal, weight_goal: goal === "weight_loss" ? "deficit" : goal === "muscle_gain" ? "surplus" : "maintenance" }));
  }
  async function geocode() {
    if (!form.address.trim()) return;
    const response = await fetch(`${apiUrl}/location/geocode`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ address: form.address }) });
    const point = response.ok ? await response.json() : FALLBACK;
    setForm(current => ({ ...current, address: point.formatted_address || current.address, lat: point.lat ?? FALLBACK.lat, lon: point.lon ?? FALLBACK.lon }));
  }
  function locate() {
    if (!navigator.geolocation) return setForm(current => ({ ...current, ...FALLBACK }));
    navigator.geolocation.getCurrentPosition(position => setForm(current => ({ ...current, lat: position.coords.latitude, lon: position.coords.longitude, address: current.address || "Current location" })), () => setForm(current => ({ ...current, ...FALLBACK, address: current.address || "Yerevan, Armenia" })), { timeout: 8000 });
  }
  function next() {
    setError("");
    if (step === 1 && (!form.name.trim() || !form.email.trim() || form.password.length < 8)) return setError("Enter a username, valid email and a password of at least 8 characters.");
    if (step === 2 && (!form.address.trim() || !form.age || !form.height_cm || !form.weight_kg)) return setError("Complete your physical metrics and location.");
    setStep(value => value + 1);
  }
  function toggleFavorite(id) {
    set("favorite_meal_ids", form.favorite_meal_ids.includes(id) ? form.favorite_meal_ids.filter(item => item !== id) : form.favorite_meal_ids.length < 5 ? [...form.favorite_meal_ids, id] : form.favorite_meal_ids);
  }
  async function submit() {
    if (form.favorite_meal_ids.length < 3) return setError("Select at least 3 favorite dishes.");
    setBusy(true); setError("");
    const response = await fetch(`${apiUrl}/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, age: +form.age, height_cm: +form.height_cm, weight_kg: +form.weight_kg, target_calories: +form.target_calories, lat: +form.lat || FALLBACK.lat, lon: +form.lon || FALLBACK.lon }) });
    const data = await response.json(); setBusy(false);
    if (!response.ok) return setError(typeof data.detail === "string" ? data.detail : "Account could not be created.");
    onSuccess(data.access_token);
  }

  return <main className="min-h-screen px-5 py-7"><div className="mx-auto max-w-4xl"><BrandMark onClick={onHome}/><section className="mt-8 overflow-hidden rounded-[2rem] bg-white shadow-xl shadow-forest/10"><div className="h-2 bg-cream"><div className="h-full bg-amber-500 transition-all" style={{ width: `${step / 3 * 100}%` }}/></div><div className="p-6 sm:p-10"><header className="mb-8"><p className="text-sm font-extrabold text-sage">STEP {step} OF 3</p><h1 className="mt-1 text-3xl font-bold text-forest">{step === 1 ? "Create your account" : step === 2 ? "Goals, health & location" : "Shape your recommendations"}</h1></header>
    {step === 1 && <div className="grid gap-5"><Input label="Username" value={form.name} onChange={e => set("name", e.target.value)} placeholder="Ani"/><Input label="Email" type="email" value={form.email} onChange={e => set("email", e.target.value)} placeholder="ani@example.com"/><Input label="Password" type="password" value={form.password} onChange={e => set("password", e.target.value)} placeholder="At least 8 characters"/></div>}
    {step === 2 && <div className="space-y-7"><div><h2 className="font-bold">Primary goal</h2><div className="mt-3 grid gap-3 sm:grid-cols-2">{GOALS.map(([value,title,copy]) => <button type="button" key={value} onClick={() => chooseGoal(value)} className={`rounded-2xl border p-4 text-left ${form.health_goal === value ? "border-forest bg-mint" : "border-forest/10"}`}><b>{title}</b><small className="mt-1 block text-ink/50">{copy}</small></button>)}</div></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Input label="Age" type="number" value={form.age} onChange={e => set("age", e.target.value)}/><label className="text-sm font-bold">Gender<select value={form.gender} onChange={e => set("gender", e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-3 py-3"><option value="female">Female</option><option value="male">Male</option><option value="other">Other / unspecified</option></select></label><Input label="Height (cm)" type="number" value={form.height_cm} onChange={e => set("height_cm", e.target.value)}/><Input label="Weight (kg)" type="number" value={form.weight_kg} onChange={e => set("weight_kg", e.target.value)}/></div><div className="grid gap-4 sm:grid-cols-3"><Input label="Target calories" type="number" value={form.target_calories} onChange={e => set("target_calories", e.target.value)}/><label className="text-sm font-bold">Macro style<select value={form.macro_preference} onChange={e => set("macro_preference", e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-3 py-3"><option value="balanced">Balanced</option><option value="high_protein">High Protein</option><option value="low_carb">Low Carb</option></select></label><label className="text-sm font-bold">Daily routine<select value={form.daily_routine} onChange={e => set("daily_routine", e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-3 py-3"><option value="desk">Mostly sitting</option><option value="on_feet">On feet / walking</option><option value="labor">Physical labor</option></select></label><label className="text-sm font-bold">Exercise frequency<select value={form.exercise_frequency} onChange={e => set("exercise_frequency", e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-3 py-3"><option value="0-1">0–1 days</option><option value="2-3">2–3 days</option><option value="4-5">4–5 days</option><option value="6+">6+ days</option></select></label><label className="text-sm font-bold">Intensity<select value={form.exercise_intensity} onChange={e => set("exercise_intensity", e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-3 py-3"><option value="light">Light</option><option value="moderate">Moderate</option><option value="high">High</option></select></label><label className="text-sm font-bold">Daily movement<select value={form.daily_movement} onChange={e => set("daily_movement", e.target.value)} className="mt-1 w-full rounded-xl border border-forest/10 px-3 py-3"><option value="under_5000">Under 5,000 steps</option><option value="5000_10000">5,000–10,000</option><option value="over_10000">10,000+</option></select></label></div><div><label className="text-sm font-bold">Street address<div className="mt-1 flex gap-2"><input value={form.address} onChange={e => set("address", e.target.value)} onBlur={geocode} className="min-w-0 flex-1 rounded-xl border border-forest/10 px-4 py-3" placeholder="Street, city, Armenia"/><button type="button" onClick={locate} className="rounded-xl bg-mint px-4 py-2 text-sm font-bold text-forest">Use My Current Location</button></div></label><small className="text-ink/45">Coordinates: {Number(form.lat).toFixed(4)}, {Number(form.lon).toFixed(4)} · free Nominatim lookup with Yerevan fallback</small></div></div>}
    {step === 3 && <div><h2 className="font-bold">Pick 3–5 favorite dishes <span className="text-sage">({form.favorite_meal_ids.length}/5)</span></h2><div className="mt-3 grid max-h-72 gap-2 overflow-auto sm:grid-cols-2 lg:grid-cols-3">{options.recipes.map(recipe => <button type="button" key={recipe.id} onClick={() => toggleFavorite(recipe.id)} className={`rounded-xl border p-3 text-left text-sm ${form.favorite_meal_ids.includes(recipe.id) ? "border-forest bg-lime/50" : "border-forest/10"}`}><b>{recipe.title}</b><small className="block text-sage">{recipe.meal_type}</small></button>)}</div><h2 className="mt-7 font-bold">Excluded ingredients, allergens & dislikes</h2><div className="mt-3 rounded-2xl border border-forest/10 p-3"><div className="flex flex-wrap gap-2">{form.excluded_ingredient_ids.map(id => { const item = options.ingredients.find(x => x.id === id); return <button type="button" key={id} onClick={() => set("excluded_ingredient_ids", form.excluded_ingredient_ids.filter(x => x !== id))} className="rounded-full bg-amber-500 px-3 py-1 text-xs font-bold text-zinc-900">{item?.name} ×</button>; })}</div><input value={ingredientQuery} onChange={e => setIngredientQuery(e.target.value)} placeholder="Search ingredient…" className="mt-2 w-full px-2 py-2 outline-none"/>{ingredientQuery && <div className="grid gap-1 border-t pt-2 sm:grid-cols-2">{ingredientMatches.map(item => <button type="button" key={item.id} onClick={() => { set("excluded_ingredient_ids", [...form.excluded_ingredient_ids, item.id]); setIngredientQuery(""); }} className="rounded-lg px-3 py-2 text-left text-sm hover:bg-mint">+ {item.name}</button>)}</div>}</div><p className="mt-3 text-xs font-semibold text-amber-700">Recipes containing selected ingredients will be strictly removed from search, recommendations and auto-generated plans.</p></div>}
    {error && <p className="mt-5 rounded-xl bg-amber-50 p-3 text-sm font-semibold text-amber-800">{error}</p>}<footer className="mt-8 flex justify-between"><button type="button" onClick={() => step === 1 ? onHome() : setStep(step - 1)} className="rounded-xl px-5 py-3 font-bold text-forest">← Back</button>{step < 3 ? <button type="button" onClick={next} className="rounded-xl bg-forest px-6 py-3 font-bold text-white">Continue →</button> : <button type="button" disabled={busy} onClick={submit} className="rounded-xl bg-lime px-6 py-3 font-bold text-forest disabled:opacity-50">{busy ? "Creating…" : "Create my Bari plan →"}</button>}</footer>
  </div></section></div></main>;
}
