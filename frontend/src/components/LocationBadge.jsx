import { useLocation } from "../context/LocationContext";

export function LocationBadge() {
  const location = useLocation();
  const coordinates = `${Number(location?.latitude || 40.1872).toFixed(3)}, ${Number(location?.longitude || 44.5152).toFixed(3)}`;
  return <button
    type="button"
    onClick={location?.refresh}
    disabled={location?.status === "checking"}
    className="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 transition-colors hover:bg-emerald-100 disabled:opacity-60"
    title={`Click to refresh location · Active coordinates: ${coordinates}`}
  >
    <span aria-hidden="true">📍</span>
    <span>{location?.status === "checking" ? "Checking location..." : location?.streetName || "Detecting Street..."}</span>
  </button>;
}
