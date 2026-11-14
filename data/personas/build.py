"""Build 500 AI residents per district from PUMS, fitted to tract totals (BUILD.md Step 4).

Steps (TODO):
  1. Load PUMS person + household records for the PUMAs covering Detroit tracts.
  2. For each district, collect its tracts' ACS totals for the 5 controls:
     age band, household income band, tenure, vehicles (0/1/2+), household size.
  3. Fit weights with ipfn; draw PERSONAS_PER_DISTRICT records with PERSONA_SEED.
  4. Assign a home block in proportion to 2020 block population (P1).
  5. Attach a work tract from LODES OD for the home block's tract.
  6. Validate against contracts/persona.schema.json and write processed/personas/district_{n}.parquet.
"""
from data.config import PERSONA_SEED, PERSONAS_PER_DISTRICT

def main():
    raise NotImplementedError("Step 4: see docstring")

if __name__ == "__main__":
    main()
