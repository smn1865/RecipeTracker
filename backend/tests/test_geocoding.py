from app.services import geocoding

def test_geocoding_falls_back_when_lookup_fails(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise OSError("offline")
    monkeypatch.setattr(geocoding, "urlopen", unavailable)
    result = geocoding.geocode_address("Unknown place")
    assert result["lat"] == 40.1872
    assert result["lon"] == 44.5152

def test_geocoding_falls_back_for_empty_results(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return b"[]"
    monkeypatch.setattr(geocoding, "urlopen", lambda *_args, **_kwargs: Response())
    assert geocoding.geocode_address("No match")["lat"] == 40.1872
