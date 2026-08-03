# Data Notes & Methodology Log

A running record of data sources, cleaning decisions, known gaps, and any
changes in measurement methodology encountered while building this dataset.
Intended to support the methodology/limitations section of the accompanying
research paper. Entries are in the order each data source was incorporated.

---

## 1. Librarian Staffing Data (OSPI SLIDE extract)

**Source:** `SLIDE_Data_File.csv`, OSPI staffing data, 2015-16 through 2024-25.

**Structure:** Wide format, one row per district, with separate columns per
year for five metrics (Librarian FTE, Teacher FTE, Ratio of Librarians to
Schools, Students-to-Librarian ratio, Teacher-to-Librarian ratio).

**Cleaning decisions:**
- Two summary rows ("Median," "Average") were present at the bottom of the
  file, mixed in with the 298 actual districts. These were split out into a
  separate reference table so they don't get accidentally treated as a
  district in any aggregation.
- The file uses `"--"` as a placeholder, but it means two different things
  depending on the column:
  - For **raw counts** (Librarian FTE, Teacher FTE), `"--"` was converted to
    **0**, since Teacher FTE is almost never missing for the same district-year,
    confirming the district existed and reported — the missing librarian
    count reflects an actual zero, not absent data.
  - For **derived ratios** (students-per-librarian, teacher-to-librarian),
    `"--"` was converted to **null**, since these ratios are mathematically
    undefined when librarian FTE = 0 (division by zero), not truly "missing."
- District name formatting was standardized (title case, consistent `(WA)`
  suffix). One naming collision was resolved: two separate "West Valley"
  districts exist (Spokane-area and Yakima-area), disambiguated in the source
  data by a parenthetical and preserved as distinct districts.

**Known limitation:** As of the most recent year (2024-25), **190 of 298
districts (64%)** report zero librarian FTE. This is a real, load-bearing
fact for the whole analysis — a majority of Washington districts have no
librarian at all in the most recent year on record, which limits how many
districts can meaningfully be included in any "students per librarian" or
librarian-ratio analysis (the ratio is undefined for them).

---

## 2. NAEP Reading Scores (Grade 4 & Grade 8, WA vs. National)

**Source:** NAEP Data Explorer exports (`.xls`), one file per grade.

**Structural mismatch with the rest of the dataset (important):**
- NAEP is administered only every **2 years** (2015, 2017, 2019, 2022,
  2024 — note the gap from 2019 to 2022, a skipped 2021 administration year
  due to COVID), not annually like the librarian data.
- NAEP reports **state-level scores only** — there is no NAEP breakdown by
  individual Washington district, and therefore **NAEP cannot be used for
  any district-level or locale-tier-level analysis.** It is retained in this
  project purely as **state-level context** (how WA compares to the national
  average over time), separate from the district-level achievement analysis
  described in Section 4.

**Data collection issue (corrected):** The first Grade 4 export pulled from
the NAEP Data Explorer only included the 2024 data point (a query-building
mistake, not a data availability issue) and had to be re-pulled to include
all five available years, matching the Grade 8 file.

**Finding of note:** Washington's reading score advantage over the national
average has narrowed substantially since 2017 in both grades, and briefly
went **negative** in Grade 4 in 2019 and 2022 (Washington scoring *below*
the national average) before a partial recovery in 2024:

| Year | Grade | WA − National gap |
|---|---|---|
| 2015 | 4 | +3.4 |
| 2017 | 4 | +1.2 |
| 2019 | 4 | −0.8 |
| 2022 | 4 | −0.8 |
| 2024 | 4 | +0.7 |
| 2015 | 8 | +1.8 |
| 2017 | 8 | +5.0 |
| 2019 | 8 | +3.1 |
| 2022 | 8 | +1.1 |
| 2024 | 8 | +1.2 |

---

## 3. Urban/Rural Locale Classification (NCES ELSI export)

**Source:** NCES ELSI Table Generator export of the federal 12-category
"urban-centric locale code," per district, per year, 2015-16 through 2024-25.

**Why NCES locale codes instead of an enrollment-based proxy:** Locale
codes are assigned from Census geography (distance to urbanized areas,
population thresholds), which distinguishes true rurality/urbanicity from
mere district size — a small district adjacent to a major city is
classified differently than an equally small, truly remote one. An
enrollment-size-based classification would have conflated these.

**Custom 6-tier collapse:** The 12 NCES codes were collapsed into a
6-category scale for this project (Distant Rural → Rural → Mid-size →
Suburban → Urban → Large Urban):

| Our tier | NCES codes folded in |
|---|---|
| Large Urban | 11 (City, Large) |
| Urban | 12, 13 (City, Mid-size / Small) |
| Suburban | 21, 22, 23 (Suburb, Large / Mid-size / Small) |
| Mid-size | 31, 32, 33 (Town, Fringe / Distant / Remote) |
| Rural | 41 (Rural, Fringe) |
| Distant Rural | 42, 43 (Rural, Distant / Remote) |

**Data note — locale is not static:** A district's locale tier can change
from year to year (Census periodically redraws urbanized area boundaries).
This is treated as a genuine year-by-year variable, not a fixed per-district
label — a handful of WA districts do shift tiers within the study window.

**Matching to the main dataset:** 7 of 298 districts initially failed to
match due to naming differences between NCES's records and OSPI's SLIDE
file (renamed districts, numbering conventions, abbreviation differences).
6 were resolved via a manual alias table:

| SLIDE name | NCES/ELSI name |
|---|---|
| Index School District | Index Elementary School District 63 |
| Nespelem School District #14 | Nespelem School District |
| North Beach School District | North Beach School District No. 64 |
| Seattle Public Schools | Seattle School District No. 1 |
| Sumner School District | Sumner-Bonney Lake School District (renamed) |
| Wellpinit School District | Wellpinit School District #49 |

The 7th, **WA State Center for Childhood Deafness and Hearing Loss**, has no
NCES locale entry at all — it's a specialized state-run school, not a
geographic district, so NCES does not assign it a locale code. This is a
genuine, expected gap, not a matching failure. **Final match rate: 99.7%**
of district-year rows (2,970 of 2,980).

**Finding of note:** In the most recent year (2024-25), **139 of 298
districts (47%) fall into "Distant Rural"** — the dataset is heavily
weighted toward small rural districts, which should inform how any
statewide-average statistic is interpreted.

---

## 4. District-Level Reading Achievement (OSPI Smarter Balanced / Report Card)

**Source:** Four separate OSPI Report Card exports:
- Combined file, 2014-15 to 2021-22 (`ela_assessment_2014_2022.csv`)
- 2022-23, 2023-24, 2024-25 (individual per-year files; OSPI switched to
  single-year files after the 2021-22 combined file)

**Why this replaced NAEP as the "achievement" measure for the core
analysis:** The research question is about impact *by district
classification* (locale tier). NAEP cannot support that (state-level only,
see Section 2). Washington's own Smarter Balanced Assessment (SBA) is
reported by district, by year, making it the only viable achievement
measure for a locale-tier-level analysis.

**Missing year:** **2019-20 has no data at all** — spring 2020 statewide
testing was cancelled due to COVID. This is a full-year gap across every
district, not a suppression issue.

**Data quality issue found and corrected — duplicate rows:** Every
district-grade-year combination in the raw files has *two* rows: one for
the standard assessment (`TestAdministration = "SBAC"`) and one for the
alternate assessment given to students with significant cognitive
disabilities (`TestAdministration = "AIM"`), which is almost always
suppressed for small sample size. **An earlier version of the cleaning
script did not filter this and silently kept whichever row came first**,
which in some cases used a suppressed AIM row instead of the real SBAC
figure. This was caught and corrected by filtering to `SBAC` only before
combining; the corrected merge affected 1,904 district-year-grade
combinations from the 2014-2022 file alone.

**Methodology change in 2022-23 — metric renamed, not redefined:** OSPI
renamed `"PercentMetStandard"` (used 2014-15 through 2021-22) to `"Percent
Consistent Grade Level Knowledge And Above"` (used 2022-23 onward). Both use
the identical underlying definition — percent of students scoring **Level 3
or 4** on the SBA. These were combined into a single comparable column
(`ela_pct_met_gradeX`) safely spanning the full decade.

**Methodology change in 2023-24 — a genuinely new, broader metric added
(NOT comparable to the above):** Starting in 2023-24, OSPI began also
reporting `"Percent Foundational Grade-Level Knowledge And Above"`, which
includes **Level 2** in addition to 3 and 4, producing meaningfully higher
percentages than the historical measure. This is a real, publicly
contested methodology decision: OSPI has stated the new label reflects
updated guidance from the testing vendor on what "grade-level" performance
means, while some state legislators have publicly characterized the change
as inflating reported proficiency by redefining the bar without stating it
as clearly as the older label did. This project takes no position on that
dispute, but treats the two metrics as **structurally different and never
merges them**: `ela_pct_foundational_gradeX` is kept in its own column,
populated only for 2023-24 and 2024-25, and should not be plotted on the
same trend line as `ela_pct_met_gradeX` without clear separate labeling.

**Suppression:** Small-sample districts show text values (`"Suppressed:
N<10"`, `"N<10"`, `"<19%"`, `">80%"`) instead of a specific percentage.
These were converted to null rather than estimated, with a companion
`is_suppressed` flag. Roughly a third of district-grade-year rows are
suppressed, and — consistent with the locale finding above — this is
concentrated in small, rural districts. **This means any locale-tier
comparison will have measurably thinner achievement data in the "Distant
Rural" tier than in more urban tiers, which should be disclosed alongside
any tier-level comparison rather than treated as a neutral gap.**

**Final coverage:** 9 of 10 years have at least partial achievement data
(all except 2019-20). 75.8% of all district-year rows in the full merged
dataset have a non-null achievement value for at least one grade.

---

## 5. Free/Reduced Price Lunch (FRL %) — Deferred

**Status:** Not yet incorporated. Two issues were identified during
sourcing and are documented here so the omission is deliberate and
explained, not accidental:

1. **NCES/federal FRL data has a known reliability problem for this exact
   study window.** The Community Eligibility Provision (CEP), which lets
   high-poverty schools serve free meals to all students without
   collecting individual household eligibility applications, expanded
   rapidly nationwide over almost exactly this project's timeframe — from
   roughly 14,200 schools in 2014-15 to over 28,700 by 2018-19. Districts
   that adopt CEP stop collecting individual FRL eligibility data, meaning
   the federal FRL field increasingly goes missing specifically for
   higher-poverty districts, and specifically gets worse in the later
   years of the study window.
2. **OSPI's Child Nutrition Program Reports** (the WA-specific alternative)
   were checked but did not appear to provide consistent year-by-year
   historical district-level data across the full 2015-2025 span needed
   for this project.

**Plan:** This may be revisited if a reliable WA-specific district-level
poverty/income measure with full decade coverage is located (e.g., via the
Report Card's diversity-tab download, checked year by year). Until then,
the achievement analysis should be read with the explicit caveat that
**no poverty/income control is currently included**, so any
librarian-vs-achievement relationship found may be confounded by district
wealth.

---

## 6. External Context Statistics (Homepage KPIs)

Added to give newcomers immediate context on Washington's broader education standing, separate from the district-level librarian/achievement analysis that is this project's core dataset. These are **single point-in-time figures from third-party sources**, not part of the project's own data pipeline, and are hardcoded with inline citations rather than pulled from a CSV.

| Statistic | Value | Source |
|---|---|---|
| Washington's national education rank | 31st (down from 27th) | Annie E. Casey Foundation, *2026 KIDS COUNT Data Book*, based on 2024 data |
| Washington's national per-pupil spending rank | 17th ($18,564/student) | U.S. Census Bureau, Annual Survey of School System Finances, FY2024 (current operating expenditures per pupil) |
| WA 4th graders not proficient in reading | 68% | Annie E. Casey Foundation, *2026 KIDS COUNT Data Book* (NAEP-based, 2024 data) |
| WA 8th graders not proficient in reading | 69% | Reporting on Annie E. Casey Foundation KIDS COUNT data, 2024 |
| WA districts with zero librarian FTE | 64% (192 of 298) | This project's own SLIDE staffing data, 2024-25 |

**Important methodological note — do not conflate with the SBA "met standard" figures used elsewhere on this dashboard:** The 68%/69% "not proficient" figures above come from Annie E. Casey Foundation's analysis of **NAEP** achievement levels, which uses a *stricter* proficiency bar than Washington's own Smarter Balanced Assessment (SBA). This dashboard's other sections (Rankings, District Profile, Correlation) use the SBA's "% met standard" (Level 3-4) measure, which shows a considerably less severe rate (~50% "not meeting standard" statewide in 2024-25 -- see Section 4 above). Both are legitimate, real measures of reading achievement, but **they are not the same measure and should never be presented as if they were** -- the homepage KPI section cites the NAEP/Casey Foundation figures explicitly as such, and the rest of the dashboard continues to use SBA-sourced figures, explicitly labeled.

**A note on user-recalled figures during this session:** the initial figures suggested for this section (60% of districts with zero librarians; 16th in per-pupil spending) were close but not exact -- the verified, sourced figures (64%; 17th) were used instead. This is noted here as an example of why every externally-sourced statistic on this dashboard is checked against a primary source before publication, not taken from memory or approximation.

---

## 7. District Report Card — Library Staffing Grade

Added as part of the "District Report Card" feature (the renamed district lookup tool). Assigns each district a letter grade (A-F) based **only on librarian staffing**, deliberately excluding reading achievement, funding, or any other school quality measure -- blending those in would imply this project can show causation, which it cannot (there is no poverty/income control in this analysis; see Section 5).

**Grading logic:**
1. A district reporting **zero librarian FTE receives an automatic F**, regardless of any other factor.
2. Districts with a librarian are scored on three **percentile ranks relative to all other Washington districts that also have a librarian**, in the most recent year (2024-25):
   - 50% -- Students per librarian (lower is better)
   - 30% -- Librarians per school, i.e. building-level coverage (higher is better)
   - 20% -- 10-year staffing trend, 2015-16 to 2024-25 (higher/less negative is better)
3. Composite score >= 80 -> A, >= 60 -> B, >= 40 -> C, else D.

**Why percentile-based rather than an absolute standard:** an external "recommended" student-to-librarian ratio could have been used instead (some library associations publish these), but no specific figure was verified against a citable primary source for this project, so a percentile-based grade was used instead -- fully transparent and defensible without relying on an unverified benchmark.

**Known limitation, disclosed on the page itself:** because this is a *relative* grade, the distribution of letter grades is stable relative to peers even in a year where every district's staffing changed in the same direction -- it cannot show the whole state improving or declining over time the way an absolute-standard grade would. Verified against the real dataset: 192 districts receive an automatic F (zero librarians), and the remaining 106 staffed districts spread across A (17), B (29), C (18), and D (42) -- a real distribution, not everything clustering in one band.

---

## 8. Advanced Analysis Section (Seaborn/SciPy)

Added two static charts (generated via `generate_advanced_analysis.py`, using pandas, Seaborn, and SciPy) to the renamed "Advanced Analysis" page (formerly "Correlation").

**A first version of this section tested the wrong thing and was replaced.** It included a Kruskal-Wallis test of whether the *achievement* gap between tiers was statistically significant (result: H=8.63, p=0.071 — not significant at p<0.05). That test was methodologically legitimate and honestly reported, but on reflection it directly re-tested the exact claim the whole dashboard's narrative rests on, creating a real risk that a skeptical reader could use a non-significant p-value to dismiss the project's central finding — a risk not worth taking for a section that's meant to *add* rigor, not introduce a contradiction with the main argument. It was replaced with two analyses that add statistical depth to the project's strongest, least-contestable finding (librarian *access*) instead of retesting achievement.

**Chart 1 — Chi-square test of independence, locale tier × has-a-librarian** (`assets/access_chi_square.png`): tests whether having a librarian at all is independent of locale tier, 2024-25. Result:
```
chi2 = 92.46, p = 3.96e-19, dof = 4
Large Urban excluded from the test (n=1; expected cell counts below 5, violating chi-square's assumptions)
```
This is overwhelmingly significant — unsurprising given the access gap (89% vs. 0% zero-librarian rates) is far starker than any achievement difference, but it's still valuable to have the rigorous confirmation on record rather than relying on the visual bar chart alone.

**Chart 2 — Missingness heatmap** (`assets/missingness_heatmap.png`): % of districts with usable (non-suppressed) Grade 4 achievement data, by locale tier and year. Turns the existing Section 4 caveat ("suppression is concentrated in rural districts") into an actual visual rather than leaving it as a prose statement only.

**A real data bug was caught and fixed while building the missingness heatmap.** Seattle Public Schools — Washington's largest district, and the sole "Large Urban" tier district — showed 0% achievement data availability in *every single year*, which should have been (and was) treated as a red flag rather than a real finding. Investigation traced this to `clean_achievement.py` never having received the same district-name alias fix that `clean_locale.py` got early in this project (Section 3): OSPI's assessment files list Seattle as `"Seattle School District No. 1"`, which doesn't match the SLIDE staffing file's `"Seattle Public Schools (WA)"` without the alias. This meant **Seattle was silently excluded from every achievement-based figure on this dashboard** (Achievement Gap chart, District Report Card, Rankings, the original Correlation scatter) since those features were built, without any error or warning. The fix was ported over from `clean_locale.py`, `clean_achievement.py` was re-run, and `output/wa_librarians_full.csv` was regenerated. Seattle now correctly shows real Grade 4/8 achievement data (roughly 60-68% met standard across the decade). All achievement-dependent figures elsewhere on the dashboard update automatically from the corrected CSV — no other code changes were needed.

---

## Open items / things to revisit

- [ ] FRL % / poverty control (see Section 5)
- [ ] Confirm whether the 2023-24 / 2024-25 "Foundational" metric should be
      used at all in the final analysis, or reported only as a footnote
      given its non-comparability to prior years
- [x] As locale-tier achievement comparisons are built, explicitly report
      the sample size (n districts with non-suppressed data) per tier per
      year, not just the average, given the suppression skew toward rural
      districts -- addressed in Section 8's boxplot, which overlays
      individual district points so sample size per tier is visible
      directly, not just implied


