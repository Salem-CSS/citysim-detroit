from engine.impact_lines import lines_for

def test_lines():
    l = lines_for({"in_noise_zone": True, "distance_to_flight_path_ft": 204, "cars_per_day_delta": -12, "nearest_street": "Michigan Ave"})
    assert l[0].startswith("A drone route passes about 200 ft") and "12 fewer" in l[1]
    assert lines_for({}) == ["No direct change near your home"]
