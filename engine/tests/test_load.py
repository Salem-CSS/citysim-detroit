from engine.load import load, band
from engine.trips import generate

def test_road_diet_doubles_load():
    # Michigan Ave: AADT ~10,309. 2 -> 1 through lane per direction doubles load (SCOPE: 0.32 -> 0.64).
    two = load(10309, 2)
    one = load(10309, 1)
    assert abs(one - 2 * two) < 1e-9
    assert band(one) == "busy"

def test_apartments_trip_rate():
    assert generate(221, 400)["daily_raw"] == 400 * 4.54
