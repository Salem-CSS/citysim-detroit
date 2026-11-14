"""Strands tools for the scenario agent (BUILD.md Step 10). Each returns plain data; none invent numbers."""

def geocode(place: str) -> dict:
    """Amazon Location: place name -> {lat, lon, label}."""
    raise NotImplementedError

def find_parcels(lat: float, lon: float, radius_m: int = 100) -> list[dict]:
    raise NotImplementedError

def lookup_trip_rate(land_use: str) -> dict:
    """Nearest ITE code from data/ite_rates.csv, with a confidence flag."""
    raise NotImplementedError

# Action tools: each validates its piece and appends to the working spec.
def add_building(**kw): raise NotImplementedError
def modify_road(**kw): raise NotImplementedError
def add_drone_route(**kw): raise NotImplementedError
def change_transit(**kw): raise NotImplementedError
def rezone(**kw): raise NotImplementedError
def add_event_surge(**kw): raise NotImplementedError
