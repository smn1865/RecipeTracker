# Smart Pantry API

Run locally:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The first startup seeds sample recipes, three nearby stores, and localized ingredient prices. API docs are at `/docs`. Use the bearer token returned from registration.

Address lookup uses OpenStreetMap Nominatim through `/location/geocode`; no API key is required. Registration also offers browser location detection and falls back to central Yerevan (`40.1872, 44.5152`) when location resolution is unavailable.

`services/location.py` is a provider boundary: replace its seeded SQL lookup with a Google Places/geocoding adapter without changing the recipe or sourcing API.
