"""Trip generation from ITE rates (BUILD.md Step 5, steps 1-2)."""
import csv
from pathlib import Path

RATES = Path(__file__).resolve().parents[1] / "data" / "ite_rates.csv"

def load_rates() -> dict[int, dict]:
    out = {}
    for r in csv.DictReader(open(RATES)):
        out[int(r["code"])] = {"name": r["name"], "unit": r["unit"],
                               "daily": float(r["daily_rate"]), "pm": float(r["pm_peak_rate"])}  # both required: a blank is an error, never a default
    return out

def generate(code: int, size: float, rates: dict | None = None) -> dict:
    """size = dwelling units, or thousands of sq ft, per the code's unit."""
    rates = rates or load_rates()
    if code not in rates:
        raise KeyError(f"ITE code {code} not in table; agent should pick nearest code and mark confidence low")
    r = rates[code]
    return {"daily_raw": size * r["daily"], "pm_peak": size * r["pm"]}

def detroit_adjust(trips: float, zero_car_share: float) -> float:
    """Scale car trips down by the tract's share of households without a car (ACS B25044)."""
    return trips * (1 - zero_car_share)
