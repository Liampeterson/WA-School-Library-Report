"""
clean_locale.py

Cleans the NCES ELSI "Locale" export and merges a 6-tier urban/rural
classification onto the main district-year dataset.

Background:
NCES assigns every school district a 12-category "urban-centric locale
code" each year, based on Census geography (distance to urbanized areas,
population size). This script collapses those 12 codes into a simpler
6-tier scale:

    NCES locale code                          -> Our 6-tier category
    ------------------------------------------------------------------
    11 - City: Large                          -> Large Urban
    12 - City: Mid-size, 13 - City: Small      -> Urban
    21/22/23 - Suburb: Large/Mid-size/Small    -> Suburban
    31/32/33 - Town: Fringe/Distant/Remote     -> Mid-size
    41 - Rural: Fringe                        -> Rural
    42/43 - Rural: Distant/Remote              -> Distant Rural

Note: a district's locale can change from year to year (Census
periodically redraws urbanized area boundaries), so this is treated as
a real year-by-year variable rather than one fixed label per district.

What this script does:
1. Reads the raw ELSI export (skipping its header/footer rows)
2. Reshapes from wide (one column per year) to long format
3. Converts NCES's missing-data symbols (†, –, ‡) to nulls
4. Parses the numeric locale code and maps it to our 6-tier scale
5. Standardizes district names to match wa_librarians_long.csv
6. Merges onto the existing long-format dataset and reports match stats
7. Saves the merged file to output/

Run with:
    python clean_locale.py
"""

import pandas as pd
import re

RAW_LOCALE_PATH = "Raw_data/elsi_locale.csv"
MAIN_DATA_PATH = "output/wa_librarians_long.csv"
OUT_DIR = "output"

# Maps the 2-digit NCES locale code (as an int) to our 6-tier scale.
LOCALE_TIER_MAP = {
    11: "Large Urban",
    12: "Urban",
    13: "Urban",
    21: "Suburban",
    22: "Suburban",
    23: "Suburban",
    31: "Mid-size",
    32: "Mid-size",
    33: "Mid-size",
    41: "Rural",
    42: "Distant Rural",
    43: "Distant Rural",
}

# Fixed ordering for anywhere we need to sort/plot these categories
TIER_ORDER = ["Distant Rural", "Rural", "Mid-size", "Suburban", "Urban", "Large Urban"]

MISSING_MARKERS = {"†", "–", "‡", "-", "", None}

# A handful of districts are named differently (or numbered differently) in
# the ELSI export than in the SLIDE staffing file. Maps the raw ELSI
# "Agency Name" -> the exact cleaned district name used in wa_librarians_long.csv.
NAME_ALIASES = {
    "INDEX ELEMENTARY SCHOOL DISTRICT 63": "Index School District (WA)",
    "NESPELEM SCHOOL DISTRICT": "Nespelem School District #14 (WA)",
    "NORTH BEACH SCHOOL DISTRICT NO. 64": "North Beach School District (WA)",
    "SEATTLE SCHOOL DISTRICT NO. 1": "Seattle Public Schools (WA)",
    "SUMNER-BONNEY LAKE SCHOOL DISTRICT": "Sumner School District (WA)",
    "WELLPINIT SCHOOL DISTRICT #49": "Wellpinit School District (WA)",
    # WA State Center for Childhood Deafness and Hearing Loss has no ELSI
    # entry at all, since it's a specialized state-run school, not a geographic
    # district, NCES doesn't assign it a locale code. Left unmatched
    # intentionally.
}


def clean_district_name(raw_name: str) -> str:
    """Match the same formatting used in clean_data.py for the main dataset."""
    raw_name = str(raw_name).strip()
    if raw_name.upper() in NAME_ALIASES:
        return NAME_ALIASES[raw_name.upper()]

    name = raw_name.title()
    name = name.replace("(Wa)", "(WA)")
    if not name.endswith("(WA)"):
        name = f"{name} (WA)"
    return name


def parse_locale_code(raw_value):
    """'33-Town: Remote' -> 33. Returns None for missing-data markers."""
    if raw_value in MISSING_MARKERS or pd.isna(raw_value):
        return None
    match = re.match(r"(\d{2})-", str(raw_value).strip())
    return int(match.group(1)) if match else None


def load_locale_long(path: str) -> pd.DataFrame:
    # Row 0 is "ELSI Export", then blank/source/filter/blank lines, header at row 6 (0-indexed 6th line -> skiprows=6)
    # Footer has 5 trailing lines (blank, blank, source note, blank, legend lines) - trim by dropping non-data rows instead of skipfooter for robustness
    raw = pd.read_csv(path, skiprows=6, engine="python")

    # Drop footer/notes rows: anything without a real Agency Name, or where
    # the State Name column doesn't say Washington (footer rows have odd content there)
    raw = raw[raw["Agency Name"].notna()]
    raw = raw[raw["State Name [District] Latest available year"].notna()]

    year_cols = [c for c in raw.columns if c.startswith("Locale [District]")]

    long_df = raw.melt(
        id_vars=["Agency Name"],
        value_vars=year_cols,
        var_name="year_raw",
        value_name="locale_raw",
    )
    long_df["year"] = long_df["year_raw"].str.extract(r"(\d{4}-\d{2})")
    long_df["district"] = long_df["Agency Name"].apply(clean_district_name)
    long_df["locale_code"] = long_df["locale_raw"].apply(parse_locale_code)
    long_df["locale_tier"] = long_df["locale_code"].map(LOCALE_TIER_MAP)

    return long_df[["district", "year", "locale_code", "locale_tier"]]


def main():
    locale_long = load_locale_long(RAW_LOCALE_PATH)
    main_df = pd.read_csv(MAIN_DATA_PATH)

    merged = main_df.merge(locale_long, on=["district", "year"], how="left")

    total_rows = len(merged)
    matched_rows = merged["locale_tier"].notna().sum()
    print(f"Matched locale data for {matched_rows} of {total_rows} district-year rows "
          f"({matched_rows/total_rows:.1%}).")

    unmatched_districts = sorted(
        merged.loc[merged["locale_tier"].isna(), "district"].unique()
    )
    if unmatched_districts:
        print(f"\n{len(unmatched_districts)} districts had no locale match in at least one year:")
        for d in unmatched_districts:
            print(f"  - {d}")
    else:
        print("\nEvery district matched successfully in every year.")

    out_path = f"{OUT_DIR}/wa_librarians_with_locale.csv"
    merged.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    # Quick sanity check: distribution of tiers in the latest year
    latest_year = sorted(merged["year"].unique())[-1]
    print(f"\nDistrict counts by tier, {latest_year}:")
    counts = (
        merged[merged["year"] == latest_year]["locale_tier"]
        .value_counts()
        .reindex(TIER_ORDER)
    )
    print(counts.to_string())


if __name__ == "__main__":
    main()