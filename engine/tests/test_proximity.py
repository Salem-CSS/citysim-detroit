from engine import proximity as px

POINT = {"kind": "point", "what": "a strip club", "name": "Michigan Ave & Trumbull St", "lon": -83.06695, "lat": 42.33142}
ROUTE = {"kind": "route", "what": "a bus route", "name": "A to B", "from": [-83.07, 42.33], "to": [-83.05, 42.33]}


def test_point_distance_matches_a_known_length():
    # one thousandth of a degree of latitude is about 111 m
    assert abs(px.distance_m(-83.06695, 42.33242, POINT) - 111.3) < 0.5


def test_route_distance_is_to_the_line_and_clamped_at_its_ends():
    assert abs(px.distance_m(-83.06, 42.331, ROUTE) - 111.3) < 0.5          # beside the middle of the line
    beyond = px.distance_m(-83.04, 42.33, ROUTE)                            # past the end: distance to the end point
    assert 800 < beyond < 840


def test_wording():
    assert px.how_far(100) == "about 350 ft" and px.how_far(1609.344) == "about 1.0 miles"
    lines, d = px.lines_for({"home_lon": -83.06695, "home_lat": 42.33242}, [POINT])
    assert lines == ["The proposed strip club would be about 350 ft from your home"] and round(d) == 111
    assert px.lines_for({"home_lon": None}, [POINT]) == ([], None) and px.lines_for({"home_lon": -83.0, "home_lat": 42.3}, []) == ([], None)


def test_places_come_only_from_verified_constraints():
    spec = {"actions": [{"title": "New building", "constraints": [
        {"id": "what", "value": "a strip club"},
        {"id": "where", "value": "somewhere", "resolved": {"name": "X & Y", "lon": -83.0, "lat": 42.3}}]},
        {"title": "Bus service", "constraints": [{"id": "what", "value": "a bus route"}, {"id": "where", "value": "typed, not verified"}]}]}
    assert px.places_of(spec) == [{"kind": "point", "what": "a strip club", "name": "X & Y", "lon": -83.0, "lat": 42.3}]
