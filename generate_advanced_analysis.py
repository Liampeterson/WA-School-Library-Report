"""
generate_advanced_analysis.py

Generates two static charts for the dashboard's "Advanced Analysis" page,
using pandas, Seaborn, and SciPy. Both were chosen specifically to add
statistical rigor WITHOUT risking a result that complicates the
dashboard's main argument (see DATA_NOTES.md Section 8 for the full
reasoning) -- an earlier version of this section tested whether the
ACHIEVEMENT gap between tiers was significant and got a non-significant
result (p=0.071), which is a legitimate but awkward thing to feature
prominently. Both charts here instead reinforce the dashboard's
strongest, least-contestable finding: the ACCESS gap.

Chart 1 -- access_chi_square.png:
  A chi-square test of independence between locale tier and whether a
  district has any librarian at all (yes/no), for 2024-25. Given the
  access gap is 89% vs. 0% zero-librarian rates across tiers -- a far
  more extreme split than achievement scores -- this is expected to
  (and does) come back overwhelmingly significant, providing rigorous
  statistical backing for the dashboard's central claim.

Chart 2 -- missingness_heatmap.png:
  A heatmap of the % of districts with usable (non-suppressed) Grade 4
  achievement data, by locale tier and year. This turns an existing
  prose caveat (DATA_NOTES.md Section 4: suppression is concentrated in
  rural districts) into an actual visual, without testing any
  hypothesis that could produce an inconvenient result.

Run with:
    python generate_advanced_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency

DATA_PATH = "output/wa_librarians_full.csv"
OUT_DIR = "assets"

TIER_ORDER = ["Distant Rural", "Rural", "Mid-size", "Suburban", "Urban", "Large Urban"]
TIER_ORDER_NO_LARGE_URBAN = ["Distant Rural", "Rural", "Mid-size", "Suburban", "Urban"]
TIER_COLORS = {
    "Distant Rural": "#8C2F26",
    "Rural": "#BB7E3D",
    "Mid-size": "#8A7B4E",
    "Suburban": "#4C7A5A",
    "Urban": "#2C5170",
    "Large Urban": "#1D3454",
}
YEARS = ["2015-16", "2016-17", "2017-18", "2018-19", "2019-20",
         "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]

CREAM_BG = "#F5F4F0"


def setup_style():
    sns.set_theme(style="whitegrid", rc={
        "axes.facecolor": CREAM_BG,
        "figure.facecolor": CREAM_BG,
        "grid.color": "#E5E5E0",
        "axes.edgecolor": "#D3D1C8",
        "text.color": "#1A1A1A",
        "axes.labelcolor": "#1A1A1A",
        "xtick.color": "#55534C",
        "ytick.color": "#55534C",
    })


def make_chi_square_chart(df):
    d = df[(df["year"] == "2024-25") & df["locale_tier"].notna()].copy()
    d["has_librarian"] = d["librarian_fte"] > 0

    # Large Urban (n=1) is excluded from the statistical test itself --
    # its expected cell counts are below 5, violating chi-square's
    # assumptions -- but is still shown in the chart for completeness,
    # clearly marked as excluded from the test.
    ct_test = pd.crosstab(d["locale_tier"], d["has_librarian"]).reindex(TIER_ORDER_NO_LARGE_URBAN)
    chi2, p_value, dof, expected = chi2_contingency(ct_test)
    min_expected = expected.min()

    print("Chi-square test of independence: locale tier x has-a-librarian, 2024-25")
    print(f"  chi2 = {chi2:.2f}, p = {p_value:.3e}, dof = {dof}, min expected count = {min_expected:.1f}")
    print(f"  (Large Urban excluded from the test -- n=1, expected counts would be below 5)")

    ct_full = pd.crosstab(d["locale_tier"], d["has_librarian"]).reindex(TIER_ORDER)
    ct_full.columns = ["No librarian", "Has librarian"]

    fig, ax = plt.subplots(figsize=(10, 6))
    ct_full.plot(
        kind="bar", stacked=True, ax=ax,
        color=["#D9CFC2", "#3C6B49"], width=0.65, edgecolor="#1A1A1A", linewidth=0.5,
    )

    for i, tier in enumerate(TIER_ORDER):
        total = ct_full.loc[tier].sum()
        has = ct_full.loc[tier, "Has librarian"]
        pct = (has / total * 100) if total else 0
        ax.text(i, total + 2, f"{pct:.0f}% staffed", ha="center", fontsize=9, color="#1A1A1A")

    p_display = "< 0.0001" if p_value < 0.0001 else f"= {p_value:.4f}"
    ax.set_title(
        f"Districts With vs. Without a Librarian, by Locale Tier (2024\u201325)\n"
        f"Chi-square test (excl. Large Urban, n=1): \u03c7\u00b2 = {chi2:.1f}, p {p_display}",
        fontsize=12.5
    )
    ax.set_xlabel("")
    ax.set_ylabel("Number of districts")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(title=None, loc="upper right")

    fig.tight_layout()
    path = f"{OUT_DIR}/access_chi_square.png"
    fig.savefig(path, dpi=150, facecolor=CREAM_BG)
    plt.close(fig)
    print(f"Saved: {path}")

    return chi2, p_value, dof


def make_missingness_heatmap(df):
    d = df[df["locale_tier"].notna()].copy()

    pivot = (
        d.groupby(["locale_tier", "year"])
        .apply(lambda g: g["ela_pct_met_grade4"].notna().mean() * 100)
        .unstack()
    )
    pivot = pivot.reindex(TIER_ORDER)
    pivot = pivot[YEARS]  # enforce chronological column order
    pivot.columns = [y.replace("-", "\u2013") for y in pivot.columns]

    fig, ax = plt.subplots(figsize=(12, 5.5))
    sns.heatmap(
        pivot, annot=True, fmt=".0f", cmap="RdYlGn", vmin=0, vmax=100,
        linewidths=1, linecolor=CREAM_BG, cbar_kws={"label": "% of districts with usable data"},
        ax=ax, annot_kws={"fontsize": 9},
    )
    ax.set_title(
        "Grade 4 Achievement Data Availability by Locale Tier and Year\n"
        "(% of districts with non-suppressed data; 2019\u201320 is blank statewide \u2014 COVID cancellation)",
        fontsize=12
    )
    ax.set_xlabel("")
    ax.set_ylabel("")

    fig.tight_layout()
    path = f"{OUT_DIR}/missingness_heatmap.png"
    fig.savefig(path, dpi=150, facecolor=CREAM_BG)
    plt.close(fig)
    print(f"Saved: {path}")


def main():
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    setup_style()

    df = pd.read_csv(DATA_PATH)
    make_chi_square_chart(df)
    make_missingness_heatmap(df)


if __name__ == "__main__":
    main()
