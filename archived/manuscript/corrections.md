# Manuscript corrections — removal of Prior 2014

Target file: `USPSTF Manuscript and Outline_USPS.md`
Data as of: `clinical_trials/outputs/clinical_master.csv` (49 rows, **42 eligible**) and
`observational_studies/outputs/articles.csv` (36 rows, 33 unique studies) as they stand
on disk right now.

Line numbers refer to the current file and will drift as you edit — work top-down.

---

## 0. What changed

**P.L. Prior 2014** (*Ibogaine effect on cocaine craving and use in dependent patients*)
is a cocaine-dependence trial. All 20 participants were enrolled under DSM-IV cocaine
dependence and every outcome — Minnesota Cocaine Craving Scale, cocaine-positive urine
screens — concerns cocaine. It reports no tobacco, alcohol, or opioid endpoint, so it
falls outside the review's three conditions.

It has been marked ineligible rather than deleted, matching how the other six exclusions
are handled: the row stays in `clinical_master.csv` with `EligibleYN = N`,
`EligibilityFailedCriterion = out_of_scope_substance`, and a written note. The screening
pipeline drops it from every table and figure automatically.

`out_of_scope_substance` is a **new failure code**. The codebook previously defined two
eligibility criteria; there are now three, and `clinical_codebook.md` §4.2 has been
updated to match:

> (a) the article reports a clinical trial, (b) it reports an outcome related to
> substance use disorder, and (c) that outcome concerns tobacco, alcohol, or opioid
> use — the three conditions under review.

**Corpus effect:**

| | before | after |
|---|---|---|
| Articles screened (clinical) | 49 | 49 |
| Eligible clinical trials | 43 | **42** |
| Exclusions | 6 | **7** |
| Opioid trials | 7 | **6** |
| Alcohol / smoking trials | 32 / 4 | 32 / 4 (unchanged) |
| Total trial participants | 2,118 | **2,098** (opioid 320 → 300) |
| Tier 1 (poolable) | 16 | 16 (unchanged) |
| Tier 2 (qualitative) | 27 | **26** |
| Clinical AE events | 186 | **185** (one mild event) |
| Observational corpus | 33 studies | 33 (untouched) |

**Prior was never in Tier 1** — its F(3,12) has a 3-df numerator and was already
`confidence = excluded`. So the pooled estimate, Figure 2A, and the psychedelic row of
Table 5 are **unchanged**. It sat in Tier 2 as `moderate_positive`, which is what
Figure 2B loses.

**Regenerated on disk** (all via `run_pipeline.py`, which now also drives the unified
figures and the three manuscript tables):

- `figures/Unified_Tier1_ForestPlot.png` — content identical, file rewritten
- `figures/Unified_Tier2_CatPlot.png` — Prior 2014 row gone from the Opioid/Ibogaine block
- `tables/Table3_USPSTF_GapMap_bySubstance.docx` — new script `scripts/table3_gapmap.py`
- `tables/Table4_AE_Safety_Summary.docx` — new script `scripts/table4_ae_safety.py`
- `tables/Tier1_PooledMeta.txt` — new script `scripts/pooled_meta.py`
- all per-condition `.docx` / `.xlsx` / `.png` outputs

> **Three pre-existing errors surfaced while verifying the new scripts against the
> published tables.** They are unrelated to Prior and are flagged inline below as
> ⚠ **PRE-EXISTING**. Each new script was validated by re-inserting Prior and checking it
> reproduces the published cells: Table 3 matched 35 of 37 rows, Table 4 matched every
> cell but one rounding case, Table 2's substance grid and the entire pooled
> meta-analysis matched exactly.

---

## 1. Methods §2.2 — eligibility screen (line 85)

Two criteria become three, and the exclusion tally changes.

**Replace** the opening and the exclusion list:

> Each article was first screened against three eligibility criteria: (a) that it
> reported an original clinical trial rather than a protocol, review, or commentary,
> (b) that it reported at least one substance-use outcome, and (c) that the outcome
> concerned tobacco, alcohol, or opioid use, the three conditions under review.
> Articles failing any criterion were retained in the dataset with an explicit failure
> code and reason, but excluded from all analyses. Of 49 articles screened in the
> clinical trial data, 42 were eligible; the 7 exclusions comprised two study protocols
> (O'Donnell 2022; Vanderijst 2024), two narrative reviews or methodological critiques
> of prior trials (Costello 1969; Smart 1964), one article reporting no substance-use
> outcome (Denson 1970), one article whose only available scan did not contain the
> target text (Ludwig 1969), and one double-blind trial conducted entirely in
> cocaine-dependent patients, outside the review's three conditions (Prior 2014).

**Optional, same line.** The adjudication tally ("Of 281 adjudicated fields…") includes
8 fields belonging to Prior 2014. If you want that QC statistic restricted to eligible
articles, it becomes: *Of 273 adjudicated fields, the automated value was upheld in 140
(51%), the prior value in 74 (27%), 32 (12%) were judged equivalent notations of the
same fact, and 27 (10%) were judged unresolvable.* None of Prior's 8 fields was decided
in favour of the hand extraction, so nothing was written back and no downstream value
depends on this choice.

---

## 2. Methods §3.1 — tier assignment (lines 95, 101)

**Line 95**, first sentence:

> Each of the 42 included studies, comprising 32 alcohol studies, 4 smoking studies, and
> 6 opioid studies, was assigned to either Tier 1 or Tier 2.

Same line, later: "Rather than excluding these 27 studies" → **26 studies**.

**Line 101**, first sentence: "Of the 43 clinical trials" → **Of the 42 clinical trials**.
The count of 16 poolable trials is unchanged.

---

## 3. Results §1 — opening paragraph (line 115)

- "identified 76 peer-reviewed articles" → **75**
- "43 eligible clinical-trial articles (32 alcohol, 7 opioid, 4 smoking)" →
  **42 eligible clinical-trial articles (32 alcohol, 6 opioid, 4 smoking)**
- "For opioid trials, 43% used ibogaine, 43% used ketamine, and 14% used LSD." →
  **"For opioid trials, 50% used ketamine, 33% used ibogaine, and 17% used LSD."**

The observational sentence (33 studies; 19 alcohol, 12 opioid, 5 tobacco; Anderson 2019
and Thomas 2013 multi-condition) is unchanged, as is the smoking, alcohol, ayahuasca,
and Smith 1958 material.

---

## 4. Table 2 — Clinical trials by behavior and substance (lines 119–129)

Only the clinical-trial columns move; every observational column is unchanged.

Header row 121: **n = 43 → n = 42** (all trials) and **n = 7 → n = 6** (opioid trials).

| Substance | % of Studies (trials) | % Opioid trials |
|---|---|---|
| Psilocybin | 28% → **29%** | 0% (unchanged) |
| Ayahuasca | 0% (unchanged) | 0% (unchanged) |
| LSD | 30% → **31%** | 14% → **17%** |
| Mescaline/peyote | 2% (unchanged) | 0% (unchanged) |
| Ibogaine | 7% → **5%** | 43% → **33%** |
| MDMA | 9% → **10%** | 0% (unchanged) |
| Ketamine | 26% (unchanged) | 43% → **50%** |
| > 1 psychedelic | 2% (unchanged) | 0% (unchanged) |

Alcohol and smoking trial columns are unchanged throughout.

---

## 5. Results §1 — narrative paragraphs (lines 131–143)

**Line 131.** "focused its methodological assessment on the 44 clinical trial
publications" → **42**. ⚠ **PRE-EXISTING**: 44 was already wrong; the figure has never
been 44 under any version of the corpus.

**Line 133.**

- "58% of trials involved randomization" → **60%**
- "higher in opioid (71%) and alcohol (59%)" → **opioid (83%)**; alcohol 59% and
  tobacco 25% unchanged
- "Participant blinding was reported in 51% of trials" → **50%**
- "whereas 71% of opioid trials utilized blinding" → **67%**
- "double-blinding was used in 57% of opioid trials" → **50%**

**Line 135.**

- "While 77% of all trials used validated outcome measurement scales" → **76%**
- "compared to 72% for alcohol and 86% for opioids" → alcohol 72% unchanged,
  opioids → **83%**; tobacco 100% unchanged
- "Only 23% of the total sample reported the results of power calculations" → **24%**
- **"only two (5%) of all trials included any interface with primary care settings
  (Grabski, 2022; Prior, 2014)"** → **"only one (2%) of all trials included any
  interface with primary care settings (Grabski, 2022)"**. Prior was the only opioid
  trial coded `PrimaryCare = 1`; the opioid cell drops to 0%.

**Line 137.**

- "Baseline severity was reported in 70% of trials overall … 57% of opioid and 69% of
  alcohol trials" → **98% overall; 97% alcohol; 100% opioid; 100% tobacco**.
  ⚠ **PRE-EXISTING**: this prose contradicts the manuscript's own Table 3, which already
  printed 98%/97%/97%/100%. The prose was carrying values from an earlier build, before
  `BaseStatusReportedYN` was derived; and Table 3's opioid cell read "97%", which is not
  attainable with a denominator of 7. Both are now 100% for opioid.
- "Female representation averaged 28% overall (alcohol 31%; opioids 13%; tobacco 35%)"
  → **29% overall; opioids 15%**; alcohol 31% and tobacco 35% unchanged
- BIPOC sentence unchanged (opioid 51%; alcohol 20%; tobacco 8%)
- "Only 5% of trials recruited a participant pool reflective of real-world community or
  primary care populations" → **2%**; "and no opioid or tobacco trial did so" remains
  true
- "Inclusion of low-SES participants was limited (19% overall)" — unchanged
- "Fewer than half of trials (47%) were conducted in the United States" → **48%**
- "only one of seven opioid trials (14%) was" → **one of six opioid trials (17%)**

**Line 139.** "therapeutic support in 100% of tobacco, 88% alcohol and 43% of opioid
studies" → opioid **50%**. The 100%-intervention-description and adverse-event sentences
are unchanged (86% overall; 100% tobacco; 100% opioid; 81% alcohol).

**Line 141.** Unchanged. Savage 1973 is still the single culturally-framed trial and
still rounds to 2% of the sample.

**Line 143.**

- "Complete cessation was reported in 72% of studies" → **71%**; "including 100% of
  tobacco studies" unchanged
- "Relapse was tracked in 86% of opioid trials" → **83%**; tobacco 75% and alcohol 56%
  unchanged
- "100% of tobacco and opioid studies measured physical/biological outcomes, compared to
  56% of alcohol studies" → alcohol **53%**. ⚠ **PRE-EXISTING**: Table 3 already printed
  53% for this cell; only the prose said 56%.
- "Measurement of implementation outcomes (28%)" → **29%**; quality of life 14% and
  mortality 12% unchanged

---

## 6. Table 3 — Methodological evaluation (lines 147–185)

Regenerated in full at `tables/Table3_USPSTF_GapMap_bySubstance.docx`. Replace the
manuscript table with the following. Header: **All (n=42) | Alcohol (n=32) |
Opioids (n=6) | Smoking (n=4)**.

| Domain | Indicator | All (n=42) | Alcohol (n=32) | Opioids (n=6) | Smoking (n=4) |
| :---- | :---- | ----- | ----- | ----- | ----- |
| **Study Identification & Design** | Were subjects randomized? | 60% | 59% | 83% | 25% |
|  | Were participants blinded? | 50% | 53% | 67% | 0% |
|  | Was the study double-blinded? | 36% | 38% | 50% | 0% |
|  | Did the study include a control or comparison group?\* | 64% | 66% | 83% | 25% |
|  | Interfaces with primary care | 2% | 3% | 0% | 0% |
|  | Power reported or discussed | 24% | 28% | 17% | 0% |
|  | Percent retention ≥ 80% | 74% | 75% | 50% | 100% |
|  | Validated scale or measure used | 76% | 72% | 83% | 100% |
|  | Assessed Confounding, Moderating or Mediating | 83% | 84% | 67% | 100% |
|  | Were inclusion/exclusion criteria clearly stated? | 83% | 81% | 100% | 75% |
|  | Were funding sources and COIs disclosed? | 86% | 84% | 83% | 100% |
| **Population & Generalizability** | Was baseline status reported? | 98% | 97% | 100% | 100% |
|  | Age range reported | 90% | 88% | 100% | 100% |
|  | Average Percent of Participants = Female | 29% | 31% | 15% | 35% |
|  | Average Percent of Participants = BIPOC | 21% | 20% | 51% | 8% |
|  | Are low SES participants included? | 19% | 19% | 17% | 25% |
|  | Country of study is the US | 48% | 47% | 17% | 100% |
|  | Recruitment reflective of community/clinical populations\*\* | 2% | 3% | 0% | 0% |
| **Intervention & Safety** | Description of intervention content / delivery? | 100% | 100% | 100% | 100% |
|  | Was therapy / counseling / integration / prep included? | 83% | 88% | 50% | 100% |
|  | Were harms or AEs assessed? | 86% | 81% | 100% | 100% |
| **Equity\*\*\*** | Was a cultural frame used | 2% | 0% | 17% | 0% |
|  | Were Indigenous frameworks referenced? | 0% | 0% | 0% | 0% |
|  | Did the study address reciprocity for Indigenous groups? | 0% | 0% | 0% | 0% |
| **Outcomes & Follow-Up** | Was psychedelic intervention associated with improvement of behavior? | 81% | 78% | 83% | 100% |
|  | Largest or Main Effect Size/Outcome reported | 100% | 100% | 100% | 100% |
|  | P-value reported | 71% | 75% | 83% | 25% |
|  | Median longest follow-up in months | 6 | 6 | 8 | 6 |
|  | Were behavioral changes measured? | 100% | 100% | 100% | 100% |
|  | Were physical/biological outcomes measured? | 64% | 53% | 100% | 100% |
|  | Were mental health outcomes measured? | 57% | 56% | 67% | 50% |
|  | Was quality of life measured? | 14% | 19% | 0% | 0% |
|  | Were implementation outcomes measured? | 29% | 38% | 0% | 0% |
|  | Was a partial behavioral reduction reported? | 76% | 84% | 17% | 100% |
|  | Was a complete cessation reported? | 71% | 69% | 67% | 100% |
|  | Was relapse tracked? | 62% | 56% | 83% | 75% |
|  | Was mortality measured? | 12% | 6% | 50% | 0% |

⚠ **PRE-EXISTING — decision needed on the "Recruitment reflective" row.** Footnote \*\*
defines this indicator as a composite filter (≤65% male, ≥40% BIPOC, low-SES
participants included). Computed that way it is **2% / 3% / 0% / 0%**, which is what the
table above and the regenerated `.docx` print. The published row read 5% / 3% / 14% / 0%
— identical, cell for cell, to the "Interfaces with primary care" row above it, which
suggests the primary-care values were copied down by mistake. Only one trial
(Bogenschutz 2022) satisfies the composite; the `RecruitmentRepresentYN` column, if you
meant that instead, gives 14% / 19% / 0% / 0%. Tell me which definition you want and I
will re-run; the script takes a one-line change.

Footnote \*\* should also read "≤65% male" rather than "65% male" whichever way you go.

---

## 7. Results §2 — Net benefits (lines 195, 201)

**Line 195.**

- "Among the 43 trials totalling 2,118 participants" → **42 trials totalling 2,098
  participants**
- "(tobacco: 100%; opioids: 86%; alcohol: 78%)" → **opioids 83%**; 81% overall,
  tobacco 100%, and alcohol 78% unchanged
- Observational sentence (979,474; 58,078 excluding Jones; 85%, 28/33) — unchanged
- "Twenty eight percent (12) of clinical trials recorded at least one moderate/severe
  adverse event." → **"Forty percent (17 of 42) of clinical trials recorded at least one
  moderate/severe adverse event."** ⚠ **PRE-EXISTING**: 12 / 28% matches neither the old
  nor the new data; the manuscript's own Table 4 said 18/37 for the same quantity
  restricted to trials that assessed AEs. The two are now 17 of 42 (all trials) and
  17/36 (trials assessing AEs).
- "Across the 43 trials, 186 discrete adverse events were recorded, of which 78% (145)
  were mild and 13% (24) severe." → **"Across the 42 trials, 185 discrete adverse events
  were recorded, of which 78% (144) were mild and 13% (24) severe."**
- The trailing clause beginning "Regarding **t**he 33 observational studies … of which
  78% (145) were mild and 13% (24) severe." is garbled and duplicates the clinical-trial
  figures inside an observational sentence. The observational counts are 75 mild / 14
  moderate / 11 severe of 100 events.

**Line 201** repeats line 195 in a partly duplicated paragraph and needs the same
treatment: "compared to 2,118 in the 43 clinical trials" → **2,098 in the 42 clinical
trials**; "of 186 and 100 total adverse events reported, respectively" → **185 and 100**.
The severity percentages (13% of trial events, 11% of observational events) are unchanged
— 24/185 still rounds to 13%.

---

## 8. Table 4 — Net benefit profile (lines 207–217)

Regenerated at `tables/Table4_AE_Safety_Summary.docx`. Only the clinical block moves.

| Study Type (N) | N total | Positive SU outcome | Assessing AEs | ≥1 mod/severe AE | Mild | Mod. | Severe |
| :---- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Clinical Trial (42)** | **2,098** | **81%** | **36 (86%)** | **17/36 (47%)** | **144** | **17** | **24** |
|     Tobacco (4) | 127 | 100% | 4 (100%) | 2/4 (50%) | 23 | 2 | 0 |
|     Opioids (6) | 300 | 83% | 6 (100%) | 3/6 (50%) | 5 | 3 | 6 |
|     Alcohol (32) | 1,671 | 78% | 26 (81%) | 12/26 (46%) | 116 | 12 | 18 |
| **Observational (33)** | **979,474** | **85%** | **22 (67%)** | **10/22 (45%)** | **75** | **14** | **11** |
|     Tobacco (5) | 215,165 | 80% | 4 (80%) | 1/4 (25%) | 17 | 1 | 0 |
|     Opioids (12) | 966,437 | 83% | 8 (67%) | 5/8 (63%) | 18 | 1 | 10 |
|     Alcohol (19) | 12,679 | 84% | 13 (68%) | 4/13 (31%) | 54 | 12 | 1 |

⚠ **PRE-EXISTING** in the clinical rows: the published alcohol cell read 13/26 (50%) and
the total 18/37 (49%). Counted from `ae_events.csv` — by event severity or by the
article-level `WorstSeverity` field, which agree exactly — alcohol has 12 such studies,
not 13. The published totals were one study high before Prior was touched.

Every observational row reproduces its published value exactly.

---

## 9. Benchmarking §3 and Table 5 (lines 239, 253) — **no change**

Prior contributed no poolable estimate, so nothing here moves. Re-derived from scratch by
`scripts/pooled_meta.py` and confirmed against the published text: 16 trials, N = 973,
g = 0.46 (95% CI 0.22–0.70), z = 3.78, p = 1.6 × 10⁻⁴, OR 2.30 (1.49–3.55), Q = 46.1 on
15 df (p = 5.2 × 10⁻⁵), τ² = 0.146, I² = 67%, prediction interval −0.33 to 1.25,
leave-one-out 0.42 (omitting Johnson MW 2026) to 0.53 (omitting Hollister 1969).

One note on the prediction interval: −0.33 to 1.25 uses the normal quantile. The
Higgins–Thompson–Spiegelhalter convention uses t at k−2 df, which widens it to −0.40 to
1.32. The script prints the published (normal) version; switching is a one-line change if
you want the more conservative interval.

---

## 10. Discussion (lines 263, 265, 271)

**Line 263.** "severe adverse events recorded in 24 of 186 discrete events across the 43
trials, and 78% of recorded events graded mild" → **24 of 185 discrete events across the
42 trials**; 78% mild is unchanged (144/185).

**Line 265.** "low frequency of primary care integration (5%) into the study designs" →
**2%**.

**Line 271.**

- "only 5% of clinical trials recruited participants representative of real-world
  community or primary care populations" → **2%**
- "only 19% included low socioeconomic status (SES) participants" — unchanged
- "average female participation was 28%" → **29%**
- "average BIPOC participation was 21%" — unchanged
- "only 5% of studies had any interaction within primary care settings" → **2%**

The closing sentence ("No studies used cultural framing, Indigenous frameworks, or
reciprocity principles") overstates the cultural-framing row — Savage 1973 does, at 2%.
That was true before this change too, so fix it only if you want to.

---

## 11. Figures

**Figure 2A** (line 223, `Unified_Tier1_ForestPlot.png`) — **content unchanged**. Prior
was never on the forest plot. The file has been rewritten, so if the manuscript embeds
figures as base64 you can leave the existing embed in place.

**Figure 2B** (line 229, `Unified_Tier2_CatPlot.png`) — **must be re-embedded**. The
Prior 2014 row is gone from the Opioid Use Disorder / Ibogaine block, which now shows
D.C. Mash 2000 and P. Glue 2016 only. Tier 2 falls from 27 to 26 studies, and the
moderate-positive category from 6 to 5 (Grabski 2022, Jovaisa T 2006, Krupitsky 2002,
Pagni 2024, Pahnke 1970).

---

## 12. Elsewhere

**Supplemental Table S.1** (referenced at line 131, not in this repo) lists all included
studies and must drop the Prior 2014 row.

Anywhere the manuscript says "43 trials" outside the lines listed above, it is now 42;
"7 opioid trials" is now 6. Lines 85, 95, 101, 115, 131, 195, 201, and 263 are the
occurrences found in this file.
