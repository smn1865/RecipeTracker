export const YEREVAN_LOCATION = { latitude: 40.1872, longitude: 44.5152 };

let activeLocation = YEREVAN_LOCATION;
let installed = false;

export function setApiLocation(location) {
  const latitude = Number(location?.latitude), longitude = Number(location?.longitude);
  activeLocation = Number.isFinite(latitude) && Number.isFinite(longitude)
    ? { latitude, longitude }
    : YEREVAN_LOCATION;
}

export function installLocationInterceptor() {
  if (installed || typeof window === "undefined") return;
  installed = true;
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const rawUrl = input instanceof Request ? input.url : String(input);
    let attachLocation = !/^https?:\/\//i.test(rawUrl);
    if (!attachLocation) {
      const requestOrigin = new URL(rawUrl).origin;
      const configuredOrigin = import.meta.env.VITE_API_URL
        ? new URL(import.meta.env.VITE_API_URL, window.location.origin).origin
        : null;
      attachLocation = requestOrigin === configuredOrigin || /^(localhost|127\.0\.0\.1):8000$/.test(new URL(rawUrl).host);
    }
    if (!attachLocation) return nativeFetch(input, init);
    const inherited = input instanceof Request ? input.headers : undefined;
    const headers = new Headers(inherited);
    new Headers(init.headers || {}).forEach((value, key) => headers.set(key, value));
    headers.set("X-User-Latitude", String(activeLocation.latitude));
    headers.set("X-User-Longitude", String(activeLocation.longitude));
    return nativeFetch(input, { ...init, headers });
  };
}

export function apiFetch(input, init) {
  installLocationInterceptor();
  return window.fetch(input, init);
}
