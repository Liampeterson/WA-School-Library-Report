"""
clean_achievement.py

Cleans and combines OSPI's district-level ELA (Smarter Balanced) assessment
data across all four source files spanning 2014-15 through 2024-25, then
merges the result onto the main librarian + locale dataset.

SOURCE FILES (all expected in data/):
  ela_assessment_2014_2022.csv   -- combined file, 2014-15 to 2021-22
  ela_assessment_2022_23.csv     -- single year
  ela_assessment_2023_24.csv     -- single year
  ela_assessment_2024_25.csv     -- single year (large, unfiltered export --
                                     contains every subject/subgroup/level,
                                     so this one needs more filtering)

IMPORTANT DATA QUALITY NOTES (read before changing this script):

1. TestAdministration duplicate rows: every district-grade-year has TWO
   rows -- one for the standard test ("SBAC") and one for the alternate
   assessment for students with significant cognitive disabilities
   ("AIM"), which is almost always suppressed for small sample size.
   We filter to TestAdministration == "SBAC" only. An earlier version of
   this script did NOT do this and silently kept whichever row came
   first, which sometimes used a suppressed AIM row instead of the real
   SBAC number -- if you're diffing against old output, this is why
   numbers changed.

2. Metric rename in 2022-23 (NOT a redefinition): the old column
   "PercentMetStandard" (2014-15 to 2021-22) and the new column
   "Percent Consistent Grade Level Knowledge And Above" (2022-23
   onward) both use the same definition -- percent of students scoring
   Level 3 or 4. These ARE safely comparable across the full decade and
   are combined into one column: ela_pct_met_gradeX.

3. A second, broader, NOT comparable metric appears starting in 2023-24:
   "Percent Foundational Grade-Level Knowledge And Above", which
   includes Level 2 as well as 3/4. This produces meaningably higher
   percentages and measures something different. It's kept in its own
   column (ela_pct_foundational_gradeX) and should never be merged with
   ela_pct_met_gradeX in a single trend line.

4. Suppression: small-sample districts show text like "Suppressed:
   N<10", "N<10", "<19%", ">80%" instead of a specific number. These are
   left as null rather than estimated, with a companion is_suppressed
   flag column so blanks can be told apart from "no data collected at
   all."

Run with:
    python clean_achievement.py
"""

import pandas as pd
import re

OUT_DIR = "output"
MAIN_DATA_PATH = "output/wa_librarians_with_locale.csv"

PCT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)%$")

NEEDED_COLS_LEGACY = [
    "SchoolYear", "OrganizationLevel", "DistrictName", "GradeLevel",
    "TestAdministration", "StudentGroup", "TestSubject",
    "PercentMetStandard",
]

# Same alias table used in clean_locale.py -- OSPI's assessment files use
# these older/differently-formatted names for a handful of districts,
# which don't match the SLIDE staffing file's naming without this fix.
# NOTE: this was originally only applied in clean_locale.py, which meant
# Seattle Public Schools (WA's largest district) was silently excluded
# from every achievement figure on this dashboard -- caught while
# investigating a missingness heatmap that showed Seattle at 0% data
# availability in every single year, which should have been an obvious
# red flag rather than a real finding.
NAME_ALIASES = {
    "INDEX ELEMENTARY SCHOOL DISTRICT 63": "Index School District (WA)",
    "NESPELEM SCHOOL DISTRICT": "Nespelem School District #14 (WA)",
    "NORTH BEACH SCHOOL DISTRICT NO. 64": "North Beach School District (WA)",
    "SEATTLE SCHOOL DISTRICT NO. 1": "Seattle Public Schools (WA)",
    "SUMNER-BONNEY LAKE SCHOOL DISTRICT": "Sumner School District (WA)",
    "WELLPINIT SCHOOL DISTRICT #49": "Wellpinit School District (WA)",
}


def clean_district_name(raw_name: str) -> str:
    raw_name = str(raw_name).strip()
    if raw_name.upper() in NAME_ALIASES:
        return NAME_ALIASES[raw_name.upper()]

    name = raw_name.title()
    name = name.replace("(Wa)", "(WA)")
    if not name.endswith("(WA)"):
        name = f"{name} (WA)"
    return name


def parse_percent(value):
    """'80.6%' -> 80.6. Suppressed/bounded values -> NaN (not guessed)."""
    if pd.isna(value):
        return float("nan")
    match = PCT_PATTERN.match(str(value).strip())
    return float(match.group(1)) if match else float("nan")


def load_legacy_file(path: str) -> pd.DataFrame:
    """2014-15 to 2021-22 combined file. GradeLevel is an int (4, 8)."""
    df = pd.read_csv(path, usecols=NEEDED_COLS_LEGACY, low_memory=False)
    df = df[
        (df["OrganizationLevel"] == "District")
        & (df["TestAdministration"] == "SBAC")
        & (df["StudentGroup"] == "All Students")
        & (df["TestSubject"] == "ELA")
        & (df["GradeLevel"].isin([4, 8]))
    ].copy()

    df["district"] = df["DistrictName"].apply(clean_district_name)
    df["year"] = df["SchoolYear"]
    df["grade"] = df["GradeLevel"].astype(int)
    df["ela_pct_met"] = df["PercentMetStandard"].apply(parse_percent)
    df["ela_pct_foundational"] = float("nan")  # metric didn't exist yet

    return df[["district", "year", "grade", "ela_pct_met", "ela_pct_foundational"]]


def load_new_file(path: str) -> pd.DataFrame:
    """2022-23 onward. GradeLevel is a zero-padded string ('04', '08')."""
    # 2022-23 doesn't have the "Foundational" column yet -- handle gracefully
    header = pd.read_csv(path, nrows=0).columns.tolist()
    has_foundational = "Percent Foundational Grade-Level Knowledge And Above" in header

    cols = [
        "SchoolYear", "OrganizationLevel", "DistrictName", "GradeLevel",
        "TestAdministration", "StudentGroup", "TestSubject",
        "Percent Consistent Grade Level Knowledge And Above",
    ]
    if has_foundational:
        cols.append("Percent Foundational Grade-Level Knowledge And Above")

    df = pd.read_csv(path, usecols=cols, low_memory=False)
    df = df[
        (df["OrganizationLevel"] == "District")
        & (df["TestAdministration"] == "SBAC")
        & (df["StudentGroup"] == "All Students")
        & (df["TestSubject"] == "ELA")
        & (df["GradeLevel"].isin(["04", "08"]))
    ].copy()

    df["district"] = df["DistrictName"].apply(clean_district_name)
    df["year"] = df["SchoolYear"]
    df["grade"] = df["GradeLevel"].astype(int)
    df["ela_pct_met"] = df["Percent Consistent Grade Level Knowledge And Above"].apply(parse_percent)
    df["ela_pct_foundational"] = (
        df["Percent Foundational Grade-Level Knowledge And Above"].apply(parse_percent)
        if has_foundational else float("nan")
    )

    return df[["district", "year", "grade", "ela_pct_met", "ela_pct_foundational"]]


def main():
    legacy = load_legacy_file("data/ela_assessment_2014_2022.csv")
    y2223 = load_new_file("data/ela_assessment_2022_23.csv")
    y2324 = load_new_file("data/ela_assessment_2023_24.csv")
    y2425 = load_new_file("data/ela_assessment_2024_25.csv")

    all_years = pd.concat([legacy, y2223, y2324, y2425], ignore_index=True)

    # Sanity check: should be at most one row per district/year/grade now
    dupes = all_years.groupby(["district", "year", "grade"]).size()
    if (dupes > 1).any():
        print(f"WARNING: {(dupes > 1).sum()} district/year/grade combos still have duplicate rows.")

    all_years["is_suppressed"] = all_years["ela_pct_met"].isna()

    # Pivot grade 4 / grade 8 into their own columns for both metrics
    def pivot_metric(value_col, prefix):
        p = all_years.pivot_table(
            index=["district", "year"], columns="grade", values=value_col, aggfunc="first"
        ).reset_index()
        p.columns = ["district", "year"] + [f"{prefix}_grade{int(c)}" for c in p.columns[2:]]
        return p

    met = pivot_metric("ela_pct_met", "ela_pct_met")
    foundational = pivot_metric("ela_pct_foundational", "ela_pct_foundational")

    achievement = met.merge(foundational, on=["district", "year"], how="outer")

    # ---- Merge onto the main dataset ----
    main_df = pd.read_csv(MAIN_DATA_PATH)
    merged = main_df.merge(achievement, on=["district", "year"], how="left")

    years_in_achievement = sorted(all_years["year"].unique())
    years_in_main = sorted(main_df["year"].unique())
    print(f"Achievement data now covers: {years_in_achievement}")
    print(f"Main dataset covers: {years_in_main}")

    missing_years = [y for y in years_in_main if y not in years_in_achievement]
    print(f"Years still missing achievement data entirely: {missing_years or 'none'}")
    print()

    matched = merged["ela_pct_met_grade4"].notna() | merged["ela_pct_met_grade8"].notna()
    print(f"Matched achievement data for {matched.sum()} of {len(merged)} total district-year rows "
          f"({matched.mean():.1%}).")

    out_path = f"{OUT_DIR}/wa_librarians_full.csv"
    merged.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    # Quick statewide sanity check: average grade 4 ELA proficiency by year
    print("\nStatewide average grade 4 'met standard' rate by year:")
    print(merged.groupby("year")["ela_pct_met_grade4"].mean().round(1).to_string())


if __name__ == "__main__":
    main()
