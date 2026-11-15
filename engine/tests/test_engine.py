"""Traffic engine against a tiny data file. Numbers follow BACKEND_PLAN.md 8.3."""
from engine import handler as h

DATA = {
    "blocks": [[-83.0760, 42.3311, 120, 0], [-83.0700, 42.3311, 80, 0], [-83.0400, 42.3600, 500, 1]],
    "tracts": [{"geoid": "26163521500", "zero_car_share": 0.25}, {"geoid": "26163500100", "zero_car_share": 0.10}],
    "segments": [
        {"id": "mich", "street": "Michigan Ave", "from": "JCT I-75", "to": "ROSA PARKS", "aadt": 8347, "lanes": 5, "two_way": True, "speed": "30",
         "coords": [[[-83.0800, 42.3310], [-83.0700, 42.3310]]]},
        {"id": "14th", "street": "14th St", "from": "Bagley St", "to": "Michigan Ave", "aadt": 793, "lanes": 2, "two_way": True, "speed": "25",
         "coords": [[[-83.0760, 42.3280], [-83.0760, 42.3310]]]}],
    "stops": [[-83.0750, 42.3312, "2", "Michigan"], [-83.0400, 42.3600, "4", "Woodward"]],
}
SITE = {"name": "Michigan Ave & 14th St", "method": "crossing", "lon": -83.0760, "lat": 42.3310, "district": 6}


def building(**c):
    cons = [{"id": "what", "value": c.get("what", "an apartment building"), "source": "from_question"},
            {"id": "where", "value": "Michigan and 14th", "source": "from_question", **({"resolved": SITE} if c.get("site", True) else {})},
            {"id": "homes", "value": c.get("homes", 400), "source": c.get("homes_source", "from_question")},
            {"id": "ground_floor", "value": c.get("ground", "homes"), "source": c.get("ground_source", "assumed")},
            {"id": "retail_sqft", "value": c.get("sqft", 0), "source": c.get("sqft_source", "assumed")}]
    return {"spec_id": "s", "version": 1, "status": "confirmed", "actions": [{"type": "add_building", "title": "New building", "constraints": cons}]}


def test_load_matches_the_plan_example():
    assert h.load_ratio(8347, 2) == 0.26 and h.load_ratio(8347, 1) == 0.52


def test_400_homes_on_michigan_at_14th():
    out = h.handler(building(), data=DATA)
    assert out["trips"] == {"daily_raw": 1816, "daily_adjusted": 1362, "pm_peak": 156}        # 400 x 4.54; x (1 - 0.25); 400 x 0.39
    seg = out["segments"][0]
    assert seg["segment_id"] == "mich"                                                         # the busier street at the corner
    assert (seg["aadt_before"], seg["aadt_after"], seg["load_before"], seg["load_after"]) == (8347, 9709, 0.26, 0.30)
    assert out["status"] == "computed" and out["street_effects"][0]["added_daily"] == 1362
    assert any("upper bound" in n for n in out["notes"]) and any("planning assumptions" in n for n in out["notes"])


def test_use_without_a_published_rate_computes_nothing():
    out = h.handler(building(what="a strip club", homes_source="assumed"), data=DATA)
    assert out["status"] == "nothing_computed" and out["segments"] == [] and "trips" not in out
    assert "no published trip rate" in out["notes"][0]


def test_unverified_site_computes_nothing():
    out = h.handler(building(site=False), data=DATA)
    assert out["segments"] == [] and "not been verified" in out["notes"][0]


def test_bus_route_counts_adults_near_the_line():
    spec = {"spec_id": "s", "version": 1, "status": "confirmed", "actions": [{"type": "change_transit", "title": "Bus service", "constraints": [
        {"id": "from", "value": "a", "resolved": {"name": "A", "lon": -83.0800, "lat": 42.3310}},
        {"id": "to", "value": "b", "resolved": {"name": "B", "lon": -83.0700, "lat": 42.3310}}]}]}
    out = h.handler(spec, data=DATA)
    assert out["transit"]["adults_within_quarter_mile"] == 200 and out["transit"]["existing_stops_within_quarter_mile"] == 1
    assert out["transit"]["existing_routes_within_quarter_mile"] == ["2 Michigan"] and "trips" not in out


def test_other_types_say_they_are_not_computed():
    out = h.handler({"spec_id": "s", "version": 1, "status": "confirmed", "actions": [{"type": "rezone", "title": "Rezoning", "constraints": []}]}, data=DATA)
    assert out["status"] == "nothing_computed" and "not built in the engine yet" in out["notes"][0]
