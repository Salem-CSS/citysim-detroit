"""Place checks (BACKEND_PLAN.md 11.2): verified against a tiny index; never guessed."""
from agent.handler import check_places
from contracts.spec import new_action, summary_line
from shared import places

SQUARE = [[-83.10, 42.30], [-83.00, 42.30], [-83.00, 42.40], [-83.10, 42.40], [-83.10, 42.30]]
INDEX = {
    "streets": {"michigan": "Michigan Ave", "trumbull": "Trumbull St", "woodward": "Woodward Ave", "5th": "5th St", "temple": "Temple St"},
    "crossings": {"michigan|trumbull": [-83.067, 42.331], "temple|woodward": [-83.055, 42.341], "5th|michigan": [-83.060, 42.330]},
    "ranges": {"michigan": [[2000, 2098, -83.070, 42.331, -83.068, 42.331]]},
    "districts": {"6": [SQUARE]},
}


class Search:
    def __init__(self, *titles):
        self.items = [{"Title": t, "PlaceType": "PointOfInterest", "Position": [-83.05 + 0.01 * i, 42.33]} for i, t in enumerate(titles)]

    def search_text(self, **kw):
        return {"ResultItems": self.items}


def r(text, districts=(6,), client=None):
    return places.resolve(text, list(districts), INDEX, client)


def test_crossing_and_address_are_verified():
    a = r("Trumbull Ave near Michigan Ave")
    assert a["status"] == "ok" and a["method"] == "crossing" and a["district"] == 6 and a["in_selected"]
    b = r("2049 Michigan Ave")
    assert b["status"] == "ok" and b["method"] == "address" and -83.070 < b["lon"] < -83.068


def test_streets_that_do_not_cross_return_real_alternatives():
    x = r("Woodward and 5th")
    assert x["status"] == "no_crossing" and x["alternatives"] == ["Woodward Ave & Temple St"]


def test_misspelled_street_is_not_guessed():
    x = r("Mishigan and Trumbull")
    assert x["status"] == "unknown_street" and "Michigan Ave" in x["alternatives"]


def test_outside_selected_districts_is_reported():
    assert r("Michigan and Trumbull", districts=(5,))["in_selected"] is False


def test_vague_landmark_is_ambiguous_and_unrelated_hit_is_not_accepted():
    assert r("the Hilton hotel", client=Search("Hilton Garden Inn", "DoubleTree by Hilton"))["status"] == "ambiguous"
    assert r("Hilton Garden Inn", client=Search("Hilton Garden Inn", "DoubleTree by Hilton"))["status"] == "ok"
    x = r("Zzyzx Plaza", client=Search("The Plaza"))
    assert x["status"] == "not_found" and x["alternatives"] == ["The Plaza"]


def spec_with(action_type, values):
    s = {"spec_id": "s", "version": 1, "status": "draft", "prompt": "q", "districts": [6], "confidence": "high",
         "actions": [new_action(action_type, values)], "unsupported": []}
    s["summary"] = summary_line(s)
    return s


def test_route_needs_start_and_end():
    resolve = lambda text, districts: places.resolve(text, districts, INDEX)
    s = check_places(spec_with("change_transit", {"what": "a bus route", "from": "Michigan and Trumbull"}), resolve)
    assert s["status"] == "needs_info" and [q["label"] for q in s["questions"]] == ["To"]
    s = check_places(spec_with("change_transit", {"what": "a bus route", "from": "Michigan and Trumbull", "to": "Woodward and Temple"}), resolve)
    assert s["status"] == "draft" and "questions" not in s
    assert s["summary"] == "Proposal: a bus route from Michigan and Trumbull to Woodward and Temple in District 6."
    assert s["actions"][0]["constraints"][2]["resolved"]["name"] == "Michigan Ave & Trumbull St"


def test_building_with_unverified_place_asks_with_alternatives():
    resolve = lambda text, districts: places.resolve(text, districts, INDEX)
    s = check_places(spec_with("add_building", {"what": "a strip club", "where": "Woodward and 5th"}), resolve)
    assert s["status"] == "needs_info" and s["questions"][0]["options"] == ["Woodward Ave & Temple St"]
    s = check_places(spec_with("add_building", {"what": "a strip club"}), resolve)
    assert s["status"] == "needs_info" and "Where should this go" in s["questions"][0]["text"]


def test_map_pick_coordinates_are_exact_and_hidden_from_residents():
    a = r("Michigan Ave & Trumbull St (42.33120, -83.06710)")
    assert a["status"] == "ok" and a["method"] == "coordinates" and a["name"] == "Michigan Ave & Trumbull St" and a["in_selected"]
    b = r("42.35, -83.05")
    assert b["status"] == "ok" and b["district"] == 6 and b["name"].startswith("Point at")
    assert r("-83.05, 42.35")["lat"] == 42.35
    s = spec_with("add_drone_route", {"from": "Michigan Ave & Trumbull St (42.33120, -83.06710)", "to": "42.35, -83.05"})
    line = summary_line(s)
    assert "42.3" not in line and "Michigan Ave & Trumbull St" in line and "a point on the map" in line


def test_a_stretch_of_one_street_between_two_cross_streets():
    x = r("Michigan Ave between Trumbull and 5th St")
    assert x["status"] == "ok" and x["method"] == "midpoint of two crossings" and x["name"] == "Michigan Ave between Trumbull St and 5th St"
    assert x["lon"] == -83.0635 and x["lat"] == 42.3305 and x["in_selected"]
    y = r("Michigan Ave between Trumbull and Woodward")              # Woodward does not cross Michigan in this index
    assert y["status"] == "no_crossing"
    z = r("Michigan Ave between Trumbull and Nowhere Rd")
    assert z["status"] == "unknown_street"
