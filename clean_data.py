"""
clean_data.py
 
Cleans the WA OSPI School Librarian Staffing Data (SLIDE_Data_File.csv).
 
What this script does:
1. Loads the raw wide-format CSV (one row per district, 10 years of data
   spread across many columns).
2. Splits off the "Median" and "Average" summary rows into their own
   reference file, since they aren't real districts.
3. Reshapes ("melts") the data from wide format into long/tidy format:
   one row per district-year, with a column for each metric. This makes
   the data far easier to query with SQL and plot over time.
4. Cleans up the "--" placeholder values:
     - For Librarians / Teachers (raw counts), "--" is treated as 0,
       since a missing count almost always means "none reported."
     - For the three ratio columns, "--" is treated as a true missing
       value (blank), since a ratio can be legitimately undefined
       (e.g. can't divide by a librarian count of 0).
5. Standardizes district name formatting.
6. Writes two clean CSVs to the output/ folder:
     - wa_librarians_long.csv   (main district-level dataset)
     - wa_librarians_summary.csv (statewide Median/Average rows, long format)
 
Run this from the project's root folder with:
    python clean_data.py
"""
 
import pandas as pd
 
# ---- 1. Load the raw file ----------------------------------------------
 
RAW_PATH = "Raw_data/SLIDE_Data_File.csv"
OUT_DIR = "output"
 
df = pd.read_csv(RAW_PATH)
 
# ---- 2. Split off the summary rows -------------------------------------
 
summary_mask = df["Agency"].isin(["Median", "Average"])
summary_df = df[summary_mask].copy()
df = df[~summary_mask].copy()
 
# ---- 3. Standardize district names --------------------------------------
 
def clean_district_name(name: str) -> str:
    """Title-case the district name but keep '(WA)' and parentheticals tidy."""
    name = name.strip()
    # Title-case everything, then fix the state suffix casing
    name = name.title()
    name = name.replace("(Wa)", "(WA)")
    return name
 
df["Agency"] = df["Agency"].apply(clean_district_name)
summary_df["Agency"] = summary_df["Agency"].apply(clean_district_name)
 
# ---- 4. Reshape wide -> long --------------------------------------------
 
# Each metric has 10 year-specific columns, e.g. "Librarians (2024-25)".
# We melt each metric group separately, then merge them together on
# district + year.
 
METRICS = {
    "Librarians": "librarian_fte",
    "Ratio of Librarians to Schools": "librarians_per_school",
    "Students to Librarian FTE Ratio": "students_per_librarian",
    "Teacher FTE to Librarian FTE Ratio": "teachers_per_librarian",
    "Teachers": "teacher_fte",
}
 
# Raw counts get missing values treated as 0; ratios get treated as NaN.
COUNT_COLUMNS = {"librarian_fte", "teacher_fte"}
 
 
def melt_metric(source_df: pd.DataFrame, raw_label: str, clean_name: str) -> pd.DataFrame:
    """Melt one metric's 10 year-columns into (Agency, year, clean_name) rows."""
    year_cols = [c for c in source_df.columns if c.startswith(f"{raw_label} (")]
    long_df = source_df.melt(
        id_vars=["Agency"],
        value_vars=year_cols,
        var_name="year_raw",
        value_name=clean_name,
    )
    # Extract "2024-25" out of "Librarians (2024-25)"
    long_df["year"] = long_df["year_raw"].str.extract(r"\((\d{4}-\d{2})\)")
    long_df = long_df.drop(columns=["year_raw"])
 
    # Convert "--" placeholders
    long_df[clean_name] = long_df[clean_name].replace("--", pd.NA)
    long_df[clean_name] = pd.to_numeric(long_df[clean_name], errors="coerce")
 
    if clean_name in COUNT_COLUMNS:
        long_df[clean_name] = long_df[clean_name].fillna(0)
 
    return long_df
 
 
def build_long_dataset(source_df: pd.DataFrame) -> pd.DataFrame:
    merged = None
    for raw_label, clean_name in METRICS.items():
        piece = melt_metric(source_df, raw_label, clean_name)
        if merged is None:
            merged = piece
        else:
            merged = merged.merge(piece, on=["Agency", "year"], how="outer")
    return merged
 
 
district_long = build_long_dataset(df)
summary_long = build_long_dataset(summary_df)
 
# ---- 5. Tidy up column names and sort order ------------------------------
 
district_long = district_long.rename(columns={"Agency": "district"})
summary_long = summary_long.rename(columns={"Agency": "statistic"})
 
district_long = district_long.sort_values(["district", "year"]).reset_index(drop=True)
summary_long = summary_long.sort_values(["statistic", "year"]).reset_index(drop=True)
 
# ---- 6. Save cleaned output ----------------------------------------------
 
import os
os.makedirs(OUT_DIR, exist_ok=True)
 
district_out_path = os.path.join(OUT_DIR, "wa_librarians_long.csv")
summary_out_path = os.path.join(OUT_DIR, "wa_librarians_summary.csv")
 
district_long.to_csv(district_out_path, index=False)
summary_long.to_csv(summary_out_path, index=False)
 
print(f"Cleaned {len(district_long['district'].unique())} districts "
      f"across {len(district_long['year'].unique())} years.")
print(f"Saved: {district_out_path}")
print(f"Saved: {summary_out_path}")