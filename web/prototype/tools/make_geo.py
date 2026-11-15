"""Write the small GeoJSON overlays the prototype map uses (web/prototype/geo/).

    python web/prototype/tools/make_geo.py

- detroit.geojson    real city limits (Overture locality, simplified ~80 m; hole = Hamtramck + Highland Park)
- districts.geojson  council districts. With --districts <official file> (the city's 2026 layer,
                     data/raw/detroit/council_districts_2026.geojson, property district_number) these are the
                     OFFICIAL boundaries. Without it they fall back to hand-drawn APPROXIMATE regions.

    python web/prototype/tools/make_geo.py --districts data/raw/detroit/council_districts_2026.geojson
- overlays.geojson   12 road corridors on REAL street geometry (Overture transportation segments, see
                     roads_overture.json) with a DEMO load until the engine supplies real ones,
                     drone route + 400 m noise band, Michigan Central hub
"""
import json, sys
from pathlib import Path
from shapely import wkt
from shapely.geometry import LineString, Point, mapping

sys.path.insert(0, str(Path(__file__).parent))
from detroit_map import REGIONS, ROUTE_LL, MC_LL, DCOL  # noqa: E402

# corridor label, kind, demo load (volume / capacity), Overture names.primary values that make it up
CORRIDORS = [
    ("Michigan Ave", "arterial", 0.32, ["Michigan Avenue"]),
    ("Woodward Ave", "arterial", 0.41, ["Woodward Avenue"]),
    ("Gratiot Ave", "arterial", 0.47, ["Gratiot Avenue"]),
    ("Grand River Ave", "arterial", 0.44, ["Grand River Avenue", "West Grand River Avenue"]),
    ("Jefferson Ave", "arterial", 0.38, ["East Jefferson Avenue", "West Jefferson Avenue"]),
    ("8 Mile Rd", "arterial", 0.52, ["8 Mile Road", "East 8 Mile Road", "West 8 Mile Road"]),
    ("I-94 Edsel Ford Fwy", "freeway", 0.62, ["Edsel Ford Freeway"]),
    ("I-75 Fisher Fwy", "freeway", 0.78, ["Fisher Freeway"]),
    ("I-75 Chrysler Fwy", "freeway", 0.69, ["Walter P. Chrysler Freeway", "North Walter P. Chrysler Freeway", "South Walter P. Chrysler Freeway"]),
    ("M-10 Lodge Fwy", "freeway", 0.66, ["John C Lodge Freeway"]),
    ("I-96 Jeffries Fwy", "freeway", 0.58, ["Jeffries Freeway"]),
    ("M-39 Southfield Fwy", "freeway", 0.55, ["Southfield Freeway"]),
]

OUT = Path(__file__).resolve().parents[1] / "geo"

# From Athena: ST_AsText(simplify_geometry(geometry, 0.0008)) for the Overture 'Detroit' locality (release 2026-10-21.0)
DETROIT_WKT = """POLYGON ((-83.164353 42.291032, -83.167074 42.289571, -83.1580123 42.2786535, -83.169907 42.264577, -83.167882 42.263944, -83.166301 42.259925, -83.160859 42.255192, -83.13753 42.282791, -83.118852 42.279134, -83.117719 42.280412, -83.119954 42.287554, -83.118264 42.289727, -83.114705 42.290177, -83.0983805 42.2867493, -83.0967741 42.2899753, -83.0794903 42.3087142, -83.0633375 42.3178215, -83.0190202 42.3293886, -82.9887708 42.3324477, -82.9591464 42.3394373, -82.9467345 42.3455724, -82.9240754 42.3517643, -82.946876 42.38699, -82.935503 42.389782, -82.921718 42.395299, -82.915926 42.405171, -82.9104391 42.4190066, -82.951354 42.4358109, -82.9408781 42.4503893, -83.287959 42.44268, -83.286463 42.407, -83.275941 42.407281, -83.274999 42.378433, -83.266659 42.378604, -83.265987 42.357046, -83.2640232 42.3416859, -83.237846 42.343086, -83.237568 42.335736, -83.2351023 42.3358285, -83.2349792 42.3298338, -83.2277277 42.3323835, -83.2251846 42.3289403, -83.215355 42.328945, -83.215415 42.336135, -83.19591 42.336439, -83.196609 42.35089, -83.147736 42.351916, -83.149743 42.340019, -83.152967 42.337566, -83.1569736 42.336959, -83.1567083 42.3278187, -83.153209 42.328087, -83.1403386 42.3106746, -83.139775 42.308491, -83.142499 42.305686, -83.1407 42.297036, -83.142478 42.294555, -83.147318 42.292569, -83.151382 42.29624, -83.156156 42.29512, -83.157801 42.292673, -83.164353 42.291032), (-83.1198146 42.4143685, -83.1219208 42.41748, -83.0895437 42.418091, -83.0763922 42.4018409, -83.0570624 42.4089797, -83.0540129 42.4044378, -83.0425248 42.4044418, -83.042302 42.390214, -83.044356 42.390181, -83.0405217 42.3847611, -83.0547413 42.3795995, -83.0625144 42.3912612, -83.0664199 42.3897576, -83.0738328 42.398719, -83.1023896 42.3881032, -83.1198146 42.4143685))"""


def fc(features):
    return {"type": "FeatureCollection", "features": features}


def feat(geom, **props):
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


def r6(obj):
    return json.loads(json.dumps(obj), parse_float=lambda x: round(float(x), 6))


def main():
    from shapely.geometry import Polygon
    OUT.mkdir(exist_ok=True)
    city = wkt.loads(DETROIT_WKT)
    (OUT / "detroit.geojson").write_text(json.dumps(r6(fc([feat(city, name="Detroit")]))))

    from shapely.geometry import shape
    official = sys.argv[sys.argv.index("--districts") + 1] if "--districts" in sys.argv else None
    if official:
        region = {int(f["properties"]["district_number"]): shape(f["geometry"]).buffer(0)
                  for f in json.loads(Path(official).read_text())["features"]}
        if sorted(region) != [1, 2, 3, 4, 5, 6, 7]:
            raise SystemExit(f"expected districts 1-7 in {official}, found {sorted(region)}")
        region = {d: region[d].simplify(0.00005) for d in sorted(region)}   # ~5 m, keeps the file small
    else:
        region = {d: Polygon(ring).intersection(city) for d, ring in REGIONS.items()}
    dists = []
    for d, g in region.items():
        p = g.representative_point()
        dists.append(feat(g, district=f"District {d}", n=d, color=DCOL[d], label=[round(p.x, 5), round(p.y, 5)],
                          source="official_2026" if official else "approximate"))
    (OUT / "districts.geojson").write_text(json.dumps(r6(fc(dists))))

    route = LineString(ROUTE_LL)
    band = route.buffer(0.0045, cap_style=1)          # ~400 m each side
    from shapely.ops import linemerge, unary_union
    raw = json.loads((Path(__file__).parent / "roads_overture.json").read_text())
    over = []
    for name, road, load, parts in CORRIDORS:
        g = linemerge(unary_union([wkt.loads(raw[p]) for p in parts if p in raw]))
        for df in dists:                      # split per district so the map can show only selected ones
            piece = g.intersection(region[df["properties"]["n"]])
            if not piece.is_empty and piece.length > 0:
                over.append(feat(piece, kind="artery", road=road, name=name, load=load, d=df["properties"]["n"]))
    over += [feat(route, kind="drone_route"), feat(band, kind="noise_band"),
             feat(Point(MC_LL), kind="hub", name="Michigan Central · Newlab")]
    (OUT / "overlays.geojson").write_text(json.dumps(r6(fc(over))))
    print("wrote", *[p.name for p in OUT.glob("*.geojson")])


if __name__ == "__main__":
    main()
