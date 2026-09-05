import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { installLocationInterceptor, setApiLocation, YEREVAN_LOCATION } from "../services/api";

installLocationInterceptor();

const LocationContext = createContext(null);
const FALLBACK_STREET = "Komitas Ave, Yerevan";

function streetFromAddress(address = {}) {
  const street = address.road || address.pedestrian || address.residential || address.neighbourhood || address.suburb;
  const city = address.city || address.town || address.municipality || "Yerevan";
  return street ? `${street}, ${city}` : city;
}

export function LocationProvider({ children }) {
  const [location, setLocation] = useState({ ...YEREVAN_LOCATION, streetName: FALLBACK_STREET, status: "pending", usingFallback: true });
  const latestRequest = useRef(0);
  const lastGeocodeKey = useRef("");
  const lastStreetName = useRef(FALLBACK_STREET);

  const reverseGeocode = useCallback(async (latitude, longitude, requestId) => {
    try {
      const params = new URLSearchParams({ lat: String(latitude), lon: String(longitude), format: "json", addressdetails: "1" });
      const response = await fetch(`https://nominatim.openstreetmap.org/reverse?${params}`, {
        headers: { Accept: "application/json", "Accept-Language": "en" },
      });
      if (!response.ok) throw new Error("Reverse geocoding unavailable");
      const payload = await response.json();
      if (requestId !== latestRequest.current) return;
      const resolved = streetFromAddress(payload.address) || FALLBACK_STREET;
      lastStreetName.current = resolved;
      setLocation((current) => ({ ...current, streetName: resolved }));
    } catch {
      if (requestId === latestRequest.current) setLocation((current) => ({ ...current, streetName: FALLBACK_STREET }));
    }
  }, []);

  const accept = useCallback(({ coords }, forceReverse = false) => {
    const requestId = ++latestRequest.current;
    const key = `${coords.latitude.toFixed(3)},${coords.longitude.toFixed(3)}`;
    const needsReverse = forceReverse || key !== lastGeocodeKey.current;
    if (needsReverse) lastGeocodeKey.current = key;
    const next = { latitude: coords.latitude, longitude: coords.longitude, accuracy: coords.accuracy, streetName: needsReverse ? "Detecting Street..." : lastStreetName.current, status: "live", usingFallback: false };
    setApiLocation(next);
    setLocation(next);
    if (needsReverse) void reverseGeocode(next.latitude, next.longitude, requestId);
  }, [reverseGeocode]);

  const reject = useCallback((status = "denied") => {
    ++latestRequest.current;
    setApiLocation(YEREVAN_LOCATION);
    setLocation({ ...YEREVAN_LOCATION, streetName: FALLBACK_STREET, status, usingFallback: true });
  }, []);

  useEffect(() => {
    if (!navigator.geolocation) {
      reject("unavailable");
      return undefined;
    }
    navigator.geolocation.getCurrentPosition((position) => accept(position), () => reject(), { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 });
    const watchId = navigator.geolocation.watchPosition((position) => accept(position), () => reject(), { enableHighAccuracy: false, maximumAge: 15000, timeout: 20000 });
    return () => navigator.geolocation.clearWatch(watchId);
  }, [accept, reject]);

  const refresh = useCallback(() => {
    if (!navigator.geolocation) {
      reject("unavailable");
      return;
    }
    setLocation((current) => ({ ...current, status: "checking" }));
    navigator.geolocation.getCurrentPosition((position) => accept(position, true), () => reject(), { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 });
  }, [accept, reject]);

  const isYerevan = location.latitude >= 40.0 && location.latitude <= 40.35 && location.longitude >= 44.3 && location.longitude <= 44.75;
  return <LocationContext.Provider value={{ ...location, label: isYerevan ? "Yerevan" : "Current location", refresh }}>{children}</LocationContext.Provider>;
}

export function useLocation() {
  return useContext(LocationContext);
}
