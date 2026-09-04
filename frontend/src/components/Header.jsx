export function BrandMark({ onClick }) {
  return (
    <button onClick={onClick} className="flex items-center gap-3 text-left text-forest" aria-label="BariAkhorzhak home">
      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-forest shadow-lg shadow-forest/15">
        <svg viewBox="0 0 48 48" className="h-8 w-8" aria-hidden="true">
          <path d="M16 14c1-5 5-8 8-8 4 0 7 3 8 8" fill="none" stroke="#d8ee84" strokeWidth="3" strokeLinecap="round"/>
          <path d="M12 17c2-4 7-6 12-6s10 2 12 6c3 7-2 21-12 24C14 38 9 24 12 17Z" fill="#f59e0b"/>
          <circle cx="19" cy="23" r="2" fill="#f7d78a"/><circle cx="27" cy="22" r="2" fill="#f7d78a"/><circle cx="23" cy="29" r="2" fill="#f7d78a"/><circle cx="30" cy="29" r="2" fill="#f7d78a"/>
          <path d="M35 11c5 1 7 4 8 8-5 0-8-2-10-6" fill="#d8ee84"/>
        </svg>
      </span>
      <span><b className="block text-xl leading-none">BariAkhorzhak</b><small className="mt-1 block font-semibold text-sage">Բարի Ախորժակ</small></span>
    </button>
  );
}

export function Header({ onHome, onProfile, onLogout, currencySwitcher, search }) {
  return (
    <header className="sticky top-0 z-30 border-b border-forest/5 bg-cream/90 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4">
        <BrandMark onClick={onHome} />
        <div className="hidden min-w-0 flex-1 justify-center lg:flex">{search}</div>
        <div className="flex items-center gap-2">
          {currencySwitcher}
          {onProfile && <button onClick={onProfile} className="hidden rounded-xl bg-white px-4 py-2 text-sm font-bold text-forest shadow-sm sm:block">Dietary Profile & Goals</button>}
          {onLogout && <button onClick={onLogout} className="rounded-xl px-3 py-2 text-sm font-bold text-ink/55">Log out</button>}
        </div>
      </nav>
      {search && <div className="mx-auto px-5 pb-3 lg:hidden">{search}</div>}
    </header>
  );
}
