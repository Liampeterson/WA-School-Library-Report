"""
clean_naep.py

Cleans the two NAEP Data Explorer exports (Grade 4 and Grade 8 reading,
Washington vs. National) into one tidy reference table.

Each input file is a legacy .xls export from the NAEP Data Explorer with
a handful of title/header rows above the real data, which starts at the
row containing "Year | Jurisdiction | All students | Average scale score".

This script:
1. Reads both .xls files (requires the 'xlrd' package for old .xls format)
2. Finds the real header row automatically in each (so it's not fragile
   if NCES changes the exact row count in a future export)
3. Adds a "grade" column (4 or 8) since that information only lives in
   the filename / title, not the data itself
4. Combines both into a single long-format table:
     year, grade, jurisdiction, avg_scale_score
5. Adds a derived "gap" table: Washington score minus National score,
   per year and grade, which is often the more tellable stat than the
   raw scores alone
6. Saves both to the output/ folder

Run with:
    python clean_naep.py
"""

import pandas as pd

INPUT_FILES = {
    4: "Raw_data/naep_grade4.xls",
    8: "Raw_data/naep_grade8.xls",
}

OUT_DIR = "output"


def load_naep_file(path: str, grade: int) -> pd.DataFrame:
    raw = pd.read_excel(path, engine="xlrd", header=None)

    # Find the row that actually contains the column headers
    header_row_idx = raw[
        raw.apply(lambda row: row.astype(str).str.contains("Year").any(), axis=1)
    ].index[0]

    data = pd.read_excel(
        path, engine="xlrd", header=header_row_idx
    )

    # Keep only real data rows (drop NOTE/SOURCE footer rows, blank rows)
    data = data.dropna(subset=["Year", "Jurisdiction", "Average scale score"])
    data = data[["Year", "Jurisdiction", "Average scale score"]].copy()
    data.columns = ["year", "jurisdiction", "avg_scale_score"]
    data["year"] = data["year"].astype(int)
    data["grade"] = grade

    return data


def main():
    frames = [load_naep_file(path, grade) for grade, path in INPUT_FILES.items()]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[["year", "grade", "jurisdiction", "avg_scale_score"]]
    combined = combined.sort_values(["grade", "year", "jurisdiction"]).reset_index(drop=True)

    # ---- Build the WA-minus-National "gap" table ----
    pivoted = combined.pivot_table(
        index=["year", "grade"], columns="jurisdiction", values="avg_scale_score"
    ).reset_index()
    pivoted["gap_wa_vs_national"] = pivoted["Washington"] - pivoted["National"]
    gap_table = pivoted[["year", "grade", "National", "Washington", "gap_wa_vs_national"]]
    gap_table = gap_table.rename(columns={
        "National": "national_avg_score",
        "Washington": "washington_avg_score",
    })
    gap_table = gap_table.sort_values(["grade", "year"]).reset_index(drop=True)

    import os
    os.makedirs(OUT_DIR, exist_ok=True)

    combined_path = os.path.join(OUT_DIR, "naep_reading_long.csv")
    gap_path = os.path.join(OUT_DIR, "naep_reading_gap.csv")

    combined.to_csv(combined_path, index=False)
    gap_table.to_csv(gap_path, index=False)

    print(f"Combined {len(combined)} rows across grades {sorted(INPUT_FILES.keys())}.")
    print(f"Saved: {combined_path}")
    print(f"Saved: {gap_path}")
    print()
    print(gap_table.to_string(index=False))


if __name__ == "__main__":
    main()