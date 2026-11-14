"""Turn a block's computed impacts into the plain lines a resident sees. Deterministic templates, no AI."""

def lines_for(block: dict) -> list[str]:
    out = []
    ft = block.get("distance_to_flight_path_ft")
    if block.get("in_noise_zone") and ft is not None:
        out.append(f"A drone route passes about {round(ft, -1):.0f} ft from your home")
    d = block.get("cars_per_day_delta")
    if d:
        street = block.get("nearest_street", "your street")
        out.append(f"{'+' if d > 0 else ''}{d:.0f} cars a day on {street}" if d > 0 else f"{abs(d):.0f} fewer cars or vans a day on {street}")
    b0, b1 = block.get("bus_wait_min_before"), block.get("bus_wait_min_after")
    if b0 and b1 and b0 != b1:
        out.append(f"Your bus comes every {b1:.0f} minutes instead of {b0:.0f}")
    m = block.get("distance_to_site_m")
    if m is not None and m < 800:
        out.append(f"The project site is about {m/1609:.1f} miles from your home")
    return out[:4] or ["No direct change near your home"]
