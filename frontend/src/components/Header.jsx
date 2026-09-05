export function BrandMark({ onClick }) {
  return (
    <button onClick={onClick} className="flex items-center gap-3 text-left text-emerald-700" aria-label="BariAkhorzhak home">
      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-emerald-700 shadow-lg shadow-emerald-700/15">
        <svg viewBox="0 0 48 48" className="h-8 w-8" aria-hidden="true">
          <path d="M16 14c1-5 5-8 8-8 4 0 7 3 8 8" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round"/>
          <path d="M12 17c2-4 7-6 12-6s10 2 12 6c3 7-2 21-12 24C14 38 9 24 12 17Z" fill="#059669"/>
          <circle cx="19" cy="23" r="2" fill="white"/><circle cx="27" cy="22" r="2" fill="white"/><circle cx="23" cy="29" r="2" fill="white"/><circle cx="30" cy="29" r="2" fill="white"/>
          <path d="M35 11c5 1 7 4 8 8-5 0-8-2-10-6" fill="#059669"/>
        </svg>
      </span>
      <span><b className="block text-xl leading-none">BariAkhorzhak</b><small className="mt-1 block font-semibold text-emerald-600">Բարի Ախորժակ</small></span>
    </button>
  );
}

const NAV_ITEMS=[["/dashboard","Dashboard"],["/planner","Weekly Planner"],["/pantry","Pantry"],["/profile","Dietary Profile"],["/recipes/new","Add Recipe"]];

export function Header({ onHome, onNavigate, activePath, onLogout, currencySwitcher }) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/10 bg-white/95 backdrop-blur-xl">
      <nav aria-label="Primary navigation" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-4">
        <BrandMark onClick={onHome} />
        {onNavigate&&<div className="order-3 flex w-full gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1 lg:order-none lg:w-auto">{NAV_ITEMS.map(([path,label])=><button key={path} onClick={()=>onNavigate(path)} aria-current={activePath===path?"page":undefined} className={activePath===path?"whitespace-nowrap rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white":"whitespace-nowrap rounded-lg px-4 py-2 text-sm font-bold text-slate-800/70 hover:text-zinc-900"}>{label}</button>)}</div>}
        <div className="flex items-center gap-2">
          {currencySwitcher}
          {onLogout && <button onClick={onLogout} className="rounded-xl px-3 py-2 text-sm font-bold text-slate-800/70">Log out</button>}
        </div>
      </nav>
    </header>
  );
}
