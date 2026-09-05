import { createContext, useContext, useEffect, useState } from "react";
import { BrandMark, Header } from "./components/Header";
import { Dashboard } from "./pages/Dashboard";
import { AddRecipe } from "./pages/AddRecipe";
import { Pantry } from "./pages/Pantry";
import { ProfileSettings } from "./pages/ProfileSettings";
import { Register } from "./pages/Register";
import { WeeklyPlanner } from "./pages/WeeklyPlanner";
import { Welcome } from "./pages/Welcome";
import { LocationProvider } from "./context/LocationContext";

const API=import.meta.env.VITE_API_URL||"http://localhost:8000";
const CurrencyContext=createContext(null);

function navigate(path){history.pushState({},"",path);dispatchEvent(new PopStateEvent("popstate"));}

function CurrencyProvider({children}){
  const[currencyMode,setCurrencyMode]=useState("LOCAL"),[currency,setCurrency]=useState({localCurrency:"AMD",localSymbol:"֏",usdToLocalRate:388});
  const configureCurrency=(data={})=>setCurrency({localCurrency:data.local_currency||"AMD",localSymbol:data.local_currency_symbol||"֏",usdToLocalRate:Number(data.usd_to_local_rate||388)});
  const formatPrice=(usdAmount)=>{const amount=Number(usdAmount||0);return currencyMode==="LOCAL"?`${(amount*currency.usdToLocalRate).toLocaleString(undefined,{maximumFractionDigits:0})} ${currency.localSymbol}`:`$${amount.toFixed(2)}`;};
  return <CurrencyContext.Provider value={{currencyMode,setCurrencyMode,...currency,configureCurrency,formatPrice}}>{children}</CurrencyContext.Provider>;
}

function CurrencySwitcher(){const{currencyMode,setCurrencyMode,localCurrency,localSymbol}=useContext(CurrencyContext);return <div className="inline-flex rounded-full border border-slate-800/10 bg-white p-1 text-xs font-bold"><button onClick={()=>setCurrencyMode("LOCAL")} className={currencyMode==="LOCAL"?"rounded-full bg-emerald-700 px-3 py-2 text-white":"px-3 py-2 text-slate-800/70"}>{localCurrency} {localSymbol}</button><button onClick={()=>setCurrencyMode("USD")} className={currencyMode==="USD"?"rounded-full bg-emerald-700 px-3 py-2 text-white":"px-3 py-2 text-slate-800/70"}>USD $</button></div>;}

function Login({onClose,onSuccess}){
  const[email,setEmail]=useState(""),[password,setPassword]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  async function submit(event){event.preventDefault();setBusy(true);setError("");const response=await fetch(`${API}/auth/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});const data=await response.json();setBusy(false);if(!response.ok)return setError(data.detail||"Could not log in.");onSuccess(data.access_token);}
  return <div className="fixed inset-0 z-50 grid place-items-center bg-zinc-900/60 p-4 backdrop-blur-sm"><form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-slate-800/10 bg-white p-7 shadow-2xl"><div className="flex items-start justify-between"><BrandMark onClick={()=>{}}/><button type="button" onClick={onClose} className="text-2xl text-slate-800/70">×</button></div><h2 className="mt-7 text-3xl font-bold text-zinc-900">Welcome back</h2><p className="mt-1 text-sm text-slate-800/70">Continue your pantry and weekly diet plan.</p><label className="mt-6 block text-sm font-bold text-slate-800">Email<input required type="email" value={email} onChange={event=>setEmail(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-800/10 px-4 py-3 outline-none focus:border-emerald-600"/></label><label className="mt-4 block text-sm font-bold text-slate-800">Password<input required type="password" value={password} onChange={event=>setPassword(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-800/10 px-4 py-3 outline-none focus:border-emerald-600"/></label>{error&&<p className="mt-3 text-sm font-semibold text-slate-800">{error}</p>}<button disabled={busy} className="mt-6 w-full rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white disabled:opacity-50">{busy?"Logging in…":"Login"}</button></form></div>;
}

function useSmartRecipes(headers){const[recipes,setRecipes]=useState([]);useEffect(()=>{fetch(`${API}/recipes/generate-smart`,{method:"POST",headers:{...headers,"Content-Type":"application/json"},body:JSON.stringify({category:"All",limit:24})}).then(response=>response.ok?response.json():[]).then(setRecipes);},[]);return recipes;}

function PlannerRoute({headers,formatPrice,configureCurrency,onLogout,currencySwitcher}){
  const recipes=useSmartRecipes(headers);
  useEffect(()=>{fetch(`${API}/auth/profile`,{headers}).then(response=>response.json()).then(configureCurrency);},[]);
  return <PageFrame activePath="/planner" onLogout={onLogout} currencySwitcher={currencySwitcher}><WeeklyPlanner recipes={recipes} formatPrice={formatPrice} headers={headers} apiUrl={API}/></PageFrame>;
}

function PantryRoute({headers,onLogout,currencySwitcher}){return <PageFrame activePath="/pantry" onLogout={onLogout} currencySwitcher={currencySwitcher}><Pantry headers={headers} apiUrl={API}/></PageFrame>;}

function AddRecipeRoute({headers,onLogout,currencySwitcher}){return <PageFrame activePath="/recipes/new" onLogout={onLogout} currencySwitcher={currencySwitcher}><AddRecipe headers={headers} apiUrl={API} onCreated={()=>navigate("/dashboard")}/></PageFrame>;}

function PageFrame({activePath,onLogout,currencySwitcher,children}){return <main className="min-h-screen bg-slate-100"><Header activePath={activePath} onNavigate={navigate} onHome={()=>navigate("/dashboard")} onLogout={onLogout} currencySwitcher={currencySwitcher}/><div className="mx-auto max-w-7xl px-5 py-8 sm:px-6">{children}</div></main>;}

function AppRoutes(){
  const[path,setPath]=useState(location.pathname),[token,setToken]=useState(localStorage.token||""),[loginOpen,setLoginOpen]=useState(false),currency=useContext(CurrencyContext);
  useEffect(()=>{const listener=()=>setPath(location.pathname);addEventListener("popstate",listener);return()=>removeEventListener("popstate",listener);},[]);
  function authenticate(value){localStorage.token=value;setToken(value);setLoginOpen(false);navigate("/dashboard");}
  function logout(){localStorage.removeItem("token");setToken("");navigate("/");}
  const switcher=<CurrencySwitcher/>,headers={Authorization:`Bearer ${token}`};let page;
  if(path==="/register")page=<Register apiUrl={API} onHome={()=>navigate("/")} onSuccess={authenticate}/>;
  else if(token&&path==="/profile")page=<ProfileSettings apiUrl={API} headers={headers} onBack={()=>navigate("/dashboard")} onLogout={logout} currencySwitcher={switcher} activePath="/profile" onNavigate={navigate}/>;
  else if(token&&path==="/planner")page=<PlannerRoute headers={headers} formatPrice={currency.formatPrice} configureCurrency={currency.configureCurrency} onLogout={logout} currencySwitcher={switcher}/>;
  else if(token&&path==="/pantry")page=<PantryRoute headers={headers} onLogout={logout} currencySwitcher={switcher}/>;
  else if(token&&path==="/recipes/new")page=<AddRecipeRoute headers={headers} onLogout={logout} currencySwitcher={switcher}/>;
  else if(token&&path==="/dashboard")page=<Dashboard apiUrl={API} token={token} onHome={()=>navigate("/dashboard")} onNavigate={navigate} onLogout={logout} formatPrice={currency.formatPrice} configureCurrency={currency.configureCurrency} currencySwitcher={switcher} activePath="/dashboard"/>;
  else page=<Welcome onLogin={()=>setLoginOpen(true)} onRegister={()=>navigate("/register")} currencySwitcher={switcher}/>;
  return <>{page}{loginOpen&&<Login onClose={()=>setLoginOpen(false)} onSuccess={authenticate}/>}</>;
}

export function App(){return <LocationProvider><CurrencyProvider><AppRoutes/></CurrencyProvider></LocationProvider>;}
