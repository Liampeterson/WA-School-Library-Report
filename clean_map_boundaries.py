"""
clean_map_boundaries.py

Prepares the Washington school district boundary map for the dashboard.

Source: OSPI's official district boundary GeoJSON (geo.wa.gov), downloaded
manually and simplified with mapshaper (topology-preserving simplification,
-simplify 8%) to shrink it from ~12MB to a web-friendly size while keeping
all 295 district shapes intact and correctly touching at shared borders.

This script:
1. Loads the simplified GeoJSON
2. Cleans each district's name to match wa_librarians_full.csv's naming
   convention exactly (same alias-table approach used in clean_locale.py
   and clean_achievement.py for the handful of districts that don't
   match automatically)
3. Strips every property down to just what the dashboard actually needs
   (district name + county, for a lighter file -- all the staffing/
   achievement/grade data is joined at runtime from wa_librarians_full.csv,
   not duplicated into the map file)
4. Verifies every district matched before saving

Run with:
    python clean_map_boundaries.py
"""

import json
import pandas as pd

RAW_GEOJSON_PATH = "../simplified_districts.geojson"  # output of the mapshaper simplify step
MAIN_DATA_PATH = "output/wa_librarians_full.csv"
OUT_PATH = "output/wa_district_boundaries.geojson"

NAME_ALIASES = {
    "LACROSSE SCHOOL DISTRICT": "Lacrosse School District (WA)",
    "MCCLEARY SCHOOL DISTRICT": "Mccleary School District (WA)",
    "STEILACOOM HISTORICAL SCHOOL DISTRICT": "Steilacoom Hist. School District (WA)",
}


def clean_name(raw_name: str) -> str:
    raw_name = str(raw_name).strip()
    if raw_name.upper() in NAME_ALIASES:
        return NAME_ALIASES[raw_name.upper()]
    if not raw_name.endswith("(WA)"):
        return f"{raw_name} (WA)"
    return raw_name


def main():
    with open(RAW_GEOJSON_PATH) as f:
        geo = json.load(f)

    main_df = pd.read_csv(MAIN_DATA_PATH)
    our_districts = set(main_df["district"].unique())

    matched = 0
    unmatched = []

    for feature in geo["features"]:
        props = feature["properties"]
        cleaned = clean_name(props["LEAName_1"])
        county = props.get("County", "")

        # Replace properties entirely -- keep the file lean
        feature["properties"] = {
            "district": cleaned,
            "county": county,
        }

        if cleaned in our_districts:
            matched += 1
        else:
            unmatched.append(cleaned)

    total = len(geo["features"])
    print(f"Matched {matched} of {total} district boundaries to wa_librarians_full.csv.")
    if unmatched:
        print(f"{len(unmatched)} unmatched:")
        for u in unmatched:
            print(f"  - {u}")
    else:
        print("All boundaries matched successfully.")

    with open(OUT_PATH, "w") as f:
        json.dump(geo, f)

    import os
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"\nSaved: {OUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
