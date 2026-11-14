"""Street load = peak-hour volume / capacity (SCOPE.md, Traffic load model)."""
K = 0.09          # share of daily traffic in the peak hour
D = 0.55          # share in the busier direction
LANE_CAP = 800    # cars per hour per through lane, signalized street

def load(aadt: float, through_lanes_per_direction: int, k: float = K, d: float = D, cap: float = LANE_CAP) -> float:
    if through_lanes_per_direction <= 0:
        raise ValueError("lanes must be positive")
    return (aadt * k * d) / (through_lanes_per_direction * cap)

def band(x: float) -> str:
    """Plain-language band used by the UI."""
    return "light" if x < 0.5 else "busy" if x < 0.75 else "heavy" if x < 0.9 else "jammed"
