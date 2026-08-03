"""
clean_statewide_ela.py

Extracts OSPI's own official STATEWIDE ELA "met standard" percentage
(grades 4 and 8) from the same four source files used in
clean_achievement.py -- but pulled from the OrganizationLevel == "State"
rows instead of aggregating district rows ourselves.

Why this matters: a simple average of district-level percentages would
weight a 50-student district the same as a 50,000-student one. OSPI's
own state-level row is the enrollment-weighted true statewide figure,
so it's used directly here rather than re-derived.

Same methodology notes as clean_achievement.py apply:
- Filtered to TestAdministration == "SBAC" only (excludes the small,
  usually-suppressed "AIM" alternate assessment rows)
- "PercentMetStandard" (2014-15 to 2021-22) and "Percent Consistent
  Grade Level Knowledge And Above" (2022-23 onward) are the same
  Level 3-4 definition, safely combined into one column
- 2019-20 has no data (COVID cancellation)

Output: output/state_ela_trend.csv, one row per year with
grade4_pct_met and grade8_pct_met columns.

Run with:
    python clean_statewide_ela.py
"""

import pandas as pd
import re

OUT_DIR = "output"
PCT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)%$")


def parse_percent(value):
    if pd.isna(value):
        return float("nan")
    match = PCT_PATTERN.match(str(value).strip())
    return float(match.group(1)) if match else float("nan")


def load_legacy_state(path):
    df = pd.read_csv(
        path,
        usecols=["SchoolYear", "OrganizationLevel", "GradeLevel", "TestAdministration",
                 "StudentGroup", "TestSubject", "PercentMetStandard"],
        low_memory=False,
    )
    d = df[
        (df["OrganizationLevel"] == "State")
        & (df["TestAdministration"] == "SBAC")
        & (df["StudentGroup"] == "All Students")
        & (df["TestSubject"] == "ELA")
        & (df["GradeLevel"].isin([4, 8]))
    ].copy()
    d["year"] = d["SchoolYear"]
    d["grade"] = d["GradeLevel"].astype(int)
    d["pct_met"] = d["PercentMetStandard"].apply(parse_percent)
    return d[["year", "grade", "pct_met"]]


def load_new_state(path):
    header = pd.read_csv(path, nrows=0).columns.tolist()
    metric_col = "Percent Consistent Grade Level Knowledge And Above"
    cols = ["SchoolYear", "OrganizationLevel", "GradeLevel", "TestAdministration",
            "StudentGroup", "TestSubject", metric_col]
    df = pd.read_csv(path, usecols=[c for c in cols if c in header], low_memory=False)
    d = df[
        (df["OrganizationLevel"] == "State")
        & (df["TestAdministration"] == "SBAC")
        & (df["StudentGroup"] == "All Students")
        & (df["TestSubject"] == "ELA")
        & (df["GradeLevel"].isin(["04", "08"]))
    ].copy()
    d["year"] = d["SchoolYear"]
    d["grade"] = d["GradeLevel"].astype(int)
    d["pct_met"] = d[metric_col].apply(parse_percent)
    return d[["year", "grade", "pct_met"]]


def main():
    parts = [
        load_legacy_state("raw_data/ela_assessment_2014_2022.csv"),
        load_new_state("raw_data/ela_assessment_2022_23.csv"),
        load_new_state("raw_data/ela_assessment_2023_24.csv"),
        load_new_state("raw_data/ela_assessment_2024_25.csv"),
    ]
    combined = pd.concat(parts, ignore_index=True)

    # Only keep years that overlap with the librarian dataset (2015-16 onward)
    combined = combined[combined["year"] != "2014-15"]

    pivoted = combined.pivot_table(index="year", columns="grade", values="pct_met", aggfunc="first")
    pivoted.columns = [f"grade{int(c)}_pct_met" for c in pivoted.columns]
    pivoted = pivoted.reset_index().sort_values("year")

    out_path = f"{OUT_DIR}/state_ela_trend.csv"
    pivoted.to_csv(out_path, index=False)

    print("Official OSPI statewide ELA 'met standard' rate by year:")
    print(pivoted.to_string(index=False))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
