"""One module per engine action. Each takes (action: dict, ctx) and returns trip deltas + per-block impacts."""
ACTIONS = ["add_building", "modify_road", "add_drone_route", "change_transit", "rezone", "add_event_surge"]
