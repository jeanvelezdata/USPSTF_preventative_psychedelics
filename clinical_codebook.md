# Clinical-Trial Extraction Codebook

**Purpose.** Field-by-field conventions for the clinical-trial extraction (52 source variables + 2 identity columns + 19 added fields, one of them derived rather than extracted, over 48 articles), producing `clinical_trials/outputs/clinical_master.csv` and the linked `ae_events.csv`. Authoritative reference for the implementation pass and for the pinned per-article prompt. Architecture and workflow are in `clinical_system_design.md`; old↔new comparability is in `clinical_old_new_mapping.md`.

**Design principles.** Be precise, conservative, evidence-based. Assert only what is explicitly stated or clearly inferable. Never guess a number to fill a field — code it not-reported. Every non-obvious judgment is recorded in the `rationale` half, never buried in a value. Two additions specific to this codebook: for the four fields that position the forest plot (§4.3), a rationale entry is mandatory on *every* article, not only the non-obvious ones; and for adverse events, the cardinal error remains understating harm, so the observational pipeline's flag-don't-bury discipline (§6) carries over intact.

**Relationship to the observational codebook.** The severity rubric in §6 is imported verbatim from `observational_codebook.md` §5 and is authoritative in both places at `RubricVersion = v1`. Everything else diverges, most importantly the missingness convention (§3), for the reason given there.

---

## 1. Crosswalk — source variable → stored field(s) → table

| Group | Source | Stored field(s) | Table |
|---|---|---|---|
| Identity | `Citation/Title`, `Condition` (existing columns) | `Citation/Title`, `Condition`, plus derived `StudyID` | `clinical_master` |
| Effect size (Tier 1) | `Outcome`, `SD`, `PVal`, `SampleSize_NFinal` | same names; `metric` / `measure` derived at clean time from `EFFECT_SIZE_EXTRACTIONS` | `clinical_master` → plot frame |
| Design & methodological quality | 15 source variables | same names | `clinical_master` |
| Population & generalizability | 7 source variables | same names | `clinical_master` |
| Intervention & harms | `InterventionDescription`, `InterventionTherapy`, `HarmsAssessed` | same names, **plus** the AE gate block (§4.10) and one row per distinct AE | both |
| Equity & cultural framing | 3 source variables | same names | `clinical_master` |
| Outcomes & follow-up | 14 source variables | same names | `clinical_master` |
| Substances | 10 source binaries | same names | `clinical_master` |
| — | eligibility screen (added, decision 9) | `EligibleYN`, `EligibilityFailedCriterion`, `EligibilityNote` | `clinical_master` |
| — | AE severity (added, decision 6) | `SafetyReported`, `AnyAEReported`, `NumDistinctAEs`, `NParticipantsWithAE`, `AE_denominator`, `ArmScope`, `WorstSeverity` + `ae_events` rows | both |
| — | provenance (added) | `text_source`, `text_format`, `SourcePDF`, `Model`, `PromptVersion`, `RubricVersion`, `Temperature` | `clinical_master` |
| — | **dropped** | `url or link to pdf`, `Study Design Type` — removed per PI instruction. `Study Design Type` held the constant `"Clinical Trial"` in all 44 frozen rows and carried no information. | — |

**Composite detail.** `MethodologyDescribedYN` stays a single binary in the data half; its 14-criterion breakdown is captured as a structured object in the rationale half (§4.4). This is the one field whose rationale entry has a fixed schema rather than free text.

This is a **standalone dataset**. It shares no key with the observational dataset and is not joined to it.

---

## 2. Table inventory

| Table | Path | Grain |
|---|---|---|
| `clinical_master` | `clinical_trials/outputs/clinical_master.csv` (+ `.xlsx` export) | one row per article, 72 columns |
| `ae_events` | `clinical_trials/outputs/ae_events.csv` | one row per distinct AE, FK `StudyID` |
| `rationale_log` | `clinical_trials/outputs/rationale_log.md` | per-article and per-AE non-obvious calls |
| `human_review_queue` | `clinical_trials/outputs/human_review_queue.csv` | `SeverityIndeterminate = Y` rows, ineligible articles, pending config proposals |

---

## 3. Missingness conventions

**Two conventions coexist in `clinical_master`, and the split is by field origin, not by field meaning.**

### 3.1 The 52 source variables — numeric codes (decision 3)

| Value | Meaning | Applies to |
|---|---|---|
| `1` | Yes / present | binary variables |
| `0` | No / absent | binary variables |
| `3` | Concept does not apply to this study, or cannot be determined from the article | binary variables |
| `"."` | Information not reported / not found | any source variable |
| `"NA - <reason>"` | Concept does not apply | non-binary source variables |
| number / enum string | Reported value | as typed in §4 |

Use `3` when the variable's concept does not logically apply (e.g. `BlindingYN` for an open-label single-arm study). Use `"."` when the concept applies but the information was simply not reported.

**This diverges deliberately from the observational codebook's `Y` / `N` / `NA` enums.** Three reasons: `_lib.recode_binary()`, `_lib.BINARY_COLS`, and `descriptive_analyses.py` all consume the numeric codes and keep working untouched; the numeric `3` carries a distinction ("does not apply") that `N` collapses; and it makes old-vs-new comparison an exact cell-for-cell diff with no value translation layer that could itself introduce a discrepancy (`clinical_old_new_mapping.md` §4).

### 3.2 The added QC and provenance fields — `Y` / `N` enums

`EligibleYN`, `SafetyReported`, `AnyAEReported`, `ArmScope`, `WorstSeverity`, `text_source`, `text_format`, `EligibilityFailedCriterion`, and every `ae_events` enum use the observational pipeline's string conventions (`"Y"` / `"N"` / `"NA"` / `"Not numbered"` / named enum values). They are **not** added to `_lib.BINARY_COLS`, and `recode_binary()` never touches them.

**This rule is stated once here and applies everywhere.** The mixed convention within one table is a documented choice, not an inconsistency: the source variables keep numeric codes so the existing analysis layer is untouched, and the added fields keep string enums so the imported AE gate-consistency rules (§8) transfer verbatim from `observational_codebook.md` §7 rather than being rewritten against a different value domain. Any field added in future belongs to whichever group its consumers belong to; adding a numeric-coded field means also adding it to `BINARY_COLS`, and adding a string-enum field means confirming it is absent from that list.

### 3.3 At merge

`"."` → `NaN`. Percent fields are numbers 0–100 with no `%` symbol. Continuous fields carry no units.

---

## 4. `clinical_master` — field-by-field

### 4.1 Identity, condition, provenance (added except `Citation/Title` and `Condition`)

| Field | Type | Valid values / rule |
|---|---|---|
| `StudyID` | text | `"{Surname} {Year}"`, e.g. `Bogenschutz 2022`. Primary key; FK target for `ae_events`. Derived from the manifest, echoed by the model, gate-verified against `_lib.first_author_surname(Citation/Title)`. A same-surname-same-year collision may take a suffix (`Surname Year b`) **in `StudyID` only** — the `(surname, Year)` config key cannot carry it, so such a collision is a blocking gate failure requiring a human decision. |
| `Citation/Title` | text | Full citation, extracted from the article. **Must begin with the first author's surname token**, because `first_author_surname()` splits on the first `,` or `;` and the resulting token is half the config-lookup key. Reproduce the manifest's frozen surname token exactly — including initials where the frozen key includes them (`_config_smoking.py` keys one study `('Johnson MW', 2026)`). |
| `Condition` | enum | `Alcohol` / `Smoking` / `Opioid`. Singular. The source folder is named `opioids` and the frozen Opioid file stores `"Opioids"`; both normalize to `Opioid`. |
| `Year` | integer | Four-digit publication year of the version of record. If online-first and issue year differ, use the issue year and note the other in `rationale`; a ±1 disagreement with the manifest is a near-miss requiring human confirmation. |
| `SourcePDF` | text | Path of the source PDF relative to `clinical_trials/inputs/pdfs/`, including the condition subfolder. |
| `text_source` | enum | `born-digital` / `OCR` / `manual`. Extraction engine. |
| `text_format` | enum | `markdown` / `text`. Whether the subagent read Markdown or the plain-text fallback. Orthogonal to `text_source`; an OCR'd article is always `text`. |
| `Model` | text | Model name + version used for extraction. |
| `PromptVersion` | text | Pinned prompt file version. |
| `RubricVersion` | text | Pinned severity-rubric version. `v1` denotes the same rubric text as the observational pipeline. |
| `Temperature` | number | Sampling temperature (0 for production). |

All seven provenance fields must be non-empty on every row (§8).

### 4.2 Eligibility (added — decision 9)

| Field | Type | Valid values / rule |
|---|---|---|
| `EligibleYN` | enum | `Y` / `N`. `Y` requires **all three**: (a) the article reports a clinical trial, (b) it reports an outcome related to substance use disorder, and (c) that outcome concerns tobacco, alcohol, or opioid use — the three conditions under review. |
| `EligibilityFailedCriterion` | enum | `not_clinical_trial` / `no_sud_outcome` / `out_of_scope_substance` / `both` / `NA`. `NA` if and only if `EligibleYN = Y`. `both` refers to (a) and (b). |
| `EligibilityNote` | text | Free text (≤ 60 words) naming which criterion failed and the evidence for it. **Mandatory whenever `EligibleYN = N`**; `"NA"` when `Y`. An empty, `"."`, or placeholder note on an ineligible article is a blocking gate failure. |

**Evidence that supports each verdict.** Criterion (a) is judged from the Methods: a prospectively planned intervention administered to participants for research purposes, with defined enrollment, an assigned regimen, and prospective outcome assessment. Retrospective chart reviews, surveys of prior use, naturalistic observation of ceremonial or self-directed use, case reports of clinical care not delivered under a study protocol, reviews, and commentary all fail (a). Criterion (b) is judged from the outcomes: at least one reported outcome must concern substance use or substance use disorder — consumption quantity/frequency, abstinence, cessation, relapse, craving, withdrawal, dependence severity, or a validated SUD instrument (AUDIT, ASI, TLFB, OCDS, AASE, CO/cotinine verification, urine screens). Outcomes solely about mood, personality, mystical experience, neuroimaging, or safety, with no substance-use endpoint reported anywhere, fail (b). Criterion (c) is judged from the target substance: a trial whose enrolled population and outcomes concern a substance outside tobacco, alcohol, and opioids — cocaine, methamphetamine, cannabis use disorder — fails (c) even when (a) and (b) are met, because the review's three conditions define its scope.

**Relation to `Clincial Trial YN`.** That variable is the model's coding of the article's design; criterion (a) is the eligibility judgment built on it. They are the same underlying fact and must agree: `Clincial Trial YN = 1` with a failed criterion (a), or `Clincial Trial YN = 0` without one, is an internal contradiction and blocks. `Clincial Trial YN ∈ {3, "."}` alongside a criterion-(a) pass is a warning — the design was undeterminable yet the screen reached a verdict, which a human should read.

**Worked examples.**

| Article shape | `EligibleYN` | `EligibilityFailedCriterion` | `EligibilityNote` |
|---|---|---|---|
| Cross-sectional survey of ayahuasca users reporting reduced drinking | `N` | `not_clinical_trial` | "Cross-sectional survey of naturalistic ceremonial users; no assigned intervention, no prospective protocol. SUD outcome (self-reported drinking reduction) is present, so criterion (b) is met." |
| Double-blind LSD trial in alcoholics reporting only MMPI personality change | `N` | `no_sud_outcome` | "Randomized double-blind trial (criterion a met), but the only reported outcomes are MMPI subscales; drinking behavior is discussed narratively in the Discussion with no measured endpoint." |
| Narrative review of psychedelics for addiction | `N` | `both` | "Review article. No participants, no assigned intervention, and no primary outcome data of its own." |
| Double-blind ibogaine trial in cocaine-dependent patients reporting craving and urine screens | `N` | `out_of_scope_substance` | "Randomized double-blind trial with substance-use outcomes (criteria a and b met), but the enrolled population is cocaine-dependent and every outcome concerns cocaine use; no tobacco, alcohol, or opioid endpoint. Fails criterion (c)." |
| Open-label single-arm psilocybin study, 15 participants, 6-month abstinence | `Y` | `NA` | `NA` |

**Boundary cases this corpus will produce.**

- **Single-arm open-label studies.** Eligible. Criterion (a) asks whether a trial was conducted, not whether it had a control arm. `Comparator = 0` and `RandomizationYN = 0` record the design weakness; they do not make the study ineligible. Several frozen studies (Kurland 1967, MacLean 1961, O'Reilly 1964, Sessa 2019, Yoon 2019, Marvania 2024) are of this shape and route to Tier 2 as `single_arm_positive`.
- **Case series of ≤ 5 patients.** Eligible only if the substance was administered under a study protocol with prospective outcome assessment; a retrospective description of clinical care is not a trial. State which in the note when the call is close, even when the verdict is `Y`.
- **Secondary analyses of trial data.** Eligible if the article reports outcomes from a clinical trial, even when the analysis is post hoc and the parent trial is published elsewhere. Record the parent trial in `rationale.article.Citation/Title` — a secondary analysis and its parent are two rows keyed on different `(surname, year)` tuples, and a reviewer must be able to see they are not independent samples.
- **Trials whose only SUD outcome is a secondary endpoint.** Eligible. Criterion (b) asks whether an SUD outcome is reported, not whether it was primary. But `Outcome` (§4.3) must still be the *stated primary* outcome's effect size — so a trial whose primary endpoint is depression severity and whose secondary endpoint is drinking days is eligible, and its `Outcome` is the depression effect size, with the discrepancy recorded in `rationale`. Flag these: they are the studies where a forest plot of "effect on SUD" can most easily be misread.
- **Ineligible articles are still fully extracted.** Every field is coded, the AE array is built, config proposals are still emitted. They are retained in `clinical_master` and excluded from the analytic outputs by the single filter `_lib.analytic_frame()` (`clinical_system_design.md` §5.1), which a reviewer can flip.

### 4.3 Tier-1 effect-size fields — stricter rules

These four determine forest-plot position (constraint 3): `Outcome` drives `metric`/`measure`, `measure` and `SampleSize_NFinal` are the two arguments to `_lib.compute()`, and `SampleSize_NFinal` additionally sets marker size via `variance_g()` and CI width via `se_g`. An error here renders as a confident, correctly-styled marker in the wrong place, which is worse than a visible gap. **A `rationale.article` entry is mandatory for all four on every article**, whether or not the call was obvious — the only fields in this codebook with that requirement. The entry states which passage or table the value came from, and for `Outcome` which of the article's reported statistics was chosen and why.

| Field | Type | Valid values / rule |
|---|---|---|
| `Outcome` | text / numeric | The effect size or outcome statistic for **the study's stated primary outcome**, on the study's primary comparison. Numeric where possible (`1.23`), else a short labelled descriptor (`"OR = 2.1"`, `"63% vs 27%"`), else `"."`. **Sharpened** from "the largest or primary effect size": largest and primary are different statistics, and choosing the largest biases the forest plot upward. Precedence when no primary is designated: (1) the outcome the authors designate primary anywhere in the article; (2) the SUD-behavioral outcome the abstract leads with; (3) among genuinely co-equal primaries, the largest — and only then, with the tie and the choice recorded in `rationale`. |
| `SD` | text | The dispersion or test statistic **paired with the value in `Outcome`** — not a different analysis's statistic. Report the label and value together, and **include degrees of freedom in parentheses whenever the statistic has them**: `"F(1,48) = 6.45"`, `"t(23) = 2.10"`, `"χ²(1) = 7.19"`, `"SD = 4.3"`, `"SE = 0.21"`. `"."` if not reported. **Sharpened**: `convert_to_d()` requires `df_error` for `method = "F"` and assumes 1 df for `chi2`; the frozen dataset lost df into free-text notes, which is why several studies were downgraded to `excluded`. A reported `F` without df is still reported as printed, with the absence noted. |
| `PVal` | numeric / text | The p-value for the same primary outcome. Exact value when printed (`0.032`); the threshold string exactly as printed when only a threshold is given (`"<0.05"`, `">0.05"`). **Never convert `"NS"`, `"not significant"`, or `"ns"` into a number or a threshold** — record `"NS"` verbatim. `"."` if no p-value is reported at all. |
| `SampleSize_NFinal` | integer | Final analyzed sample size **for the analysis that produced `Outcome`** — the denominator that `Outcome` was computed over, not the enrolled or randomized N unless those are the same. If the effect size comes from a subgroup or a completers-only analysis, this is that subgroup's N and `rationale` says so. `"."` if not derivable. **Sharpened**: `variance_g()` assumes `n1 = n2 = N/2` on exactly this number, so a mismatched N mis-sizes the marker and mis-widths the CI while leaving the point estimate looking correct. |

`metric` and `measure` are **not** extracted fields. They are added at clean time by `_lib.extract_effect_size_fields()` from `EFFECT_SIZE_EXTRACTIONS`, keyed on `(surname, Year)`. The model's proposals for those entries go in `rationale.config_proposal`, never in `data` (`clinical_system_design.md` §5.3).

### 4.4 Design and methodological quality

| Field | Type | Valid values / rule |
|---|---|---|
| `Pos Result Y/N` | binary | Did the psychedelic intervention produce a positive result — reduce problematic substance use or improve a primary outcome? `1` = positive/significant result reported; `0` = null or negative; `3` = cannot be determined; `"."` = not reported. Kept in the RCT framing of the source item, **not** redefined as the observational pipeline's `PosResult` was: this is a trials corpus where a comparator is usually present. For a single-arm study with no comparator, judge the study's own pre/post direction; use `3` only when directionality is genuinely ambiguous or mixed. |
| `Clincial Trial YN` | binary | Was this a clinical trial of any sort (RCT, open-label, phase I/II/III)? `1`/`0`/`3`/`"."`. **Column name misspelling preserved verbatim** (decision 2). Must not contradict `EligibilityFailedCriterion` (§4.2). |
| `RandomizationYN` | binary | Was randomization used? `1`/`0`/`3` (not applicable, e.g. single-arm)/`"."`. |
| `BlindingYN` | binary | Was any blinding implemented (single-, double-, rater-blind)? `1`/`0`/`3`/`"."`. |
| `Double+Blind` | binary | Double-blind or better (triple-blind)? `1`/`0`/`3`/`"."`. Must not be `1` when `BlindingYN = 0`. |
| `Comparator` | binary | Control or comparison group (active comparator or placebo)? `1`/`0`/`3`/`"."`. A dose-comparison design (high vs low dose) counts as `1`; record the nature of the comparator in `rationale`. |
| `PrimaryCare` | binary | Did any aspect interface with primary care settings or providers? `1`/`0`/`3`/`"."`. |
| `Power` | binary | Was statistical power reported or discussed (a priori calculation or post hoc)? `1`/`0`/`3`/`"."`. A bare statement that the study was underpowered counts as discussed (`1`). |
| `Retention (%)` | number 0–100 | Percent of participants who completed the study. **Denominator sharpened**: use the randomized N when both randomized and enrolled are reported, since attrition after randomization is what the criterion measures; use enrolled when the study was not randomized. Calculate as `completers / denominator × 100` if not directly stated, and state the two counts used in `rationale`. `"."` if not calculable. Consumed by Table 2 and Table 3 at the ≥ 80% threshold, so a value near 80 warrants an explicit rationale entry. |
| `ConfoundYN` | binary | Were confounding, moderating, or mediating factors assessed — statistically adjusted, stratified, or substantively discussed? `1`/`0`/`3`/`"."`. |
| `InclusionExclusionCriteria` | binary | Were inclusion and/or exclusion criteria clearly stated? `1`/`0`/`3`/`"."`. |
| `ValidatedScaleMeasYN` | binary | Was at least one validated scale or psychometric measure used as an outcome? `1`/`0`/`3`/`"."`. Biochemical verification (CO, cotinine, urine screen) is not a scale; code it under `PhysicalChangeMeasured`. |
| `MethodologyDescribedYN` | binary | Were **at least 13 of 14** design criteria present or described: (1) study objective, (2) study design, (3) setting, (4) eligibility criteria, (5) intervention, (6) comparator, (7) outcomes, (8) sample size / power, (9) randomization, (10) blinding, (11) statistical methods, (12) results, (13) harms / AEs, (14) funding / COI. `1` = ≥ 13 met; `0` = < 13; `"."` = cannot be assessed. **A criterion is met when the element is *described*, including when it is described as absent** — "no blinding was used" satisfies criterion (10) while `BlindingYN = 0`. Conflating "described" with "present" would penalize exactly the well-reported studies. |
| `Funding/COI YN` | binary | Was funding source and/or conflicts of interest disclosed? `1`/`0`/`3`/`"."`. Punctuation in the column name preserved verbatim. |

**`MethodologyDescribedYN`'s mandatory structured rationale.** `rationale.article.MethodologyDescribedYN` is an object, not a string, with exactly these keys:

```json
{
  "criteria": {
    "objective": "Y", "design": "Y", "setting": "N", "eligibility": "Y",
    "intervention": "Y", "comparator": "Y", "outcomes": "Y", "sample_size_power": "N",
    "randomization": "Y", "blinding": "Y", "statistical_methods": "Y",
    "results": "Y", "harms": "Y", "funding_coi": "Y"
  },
  "n_met": 12,
  "note": "Setting never stated beyond 'outpatient'; no power calculation or sample-size justification."
}
```

All fourteen keys are required, each `"Y"` or `"N"`. `n_met` must equal the count of `"Y"`, and the binary must be `1` iff `n_met ≥ 13`; both are blocking arithmetic checks. The `note` names the failing criteria. What this buys is set out in `clinical_system_design.md` §5.2.

### 4.5 Population and generalizability

| Field | Type | Valid values / rule |
|---|---|---|
| `BaseStatus` | enum | `Severe` / `Moderate` / `Mild` / `"."` — severity of the target condition at baseline in the study population. **Closed enum only; never a number.** Grade only where the article assigns a severity or reports an instrument that maps to one (DSM-5 specifier or criterion count, AUDIT/SADQ/FTCD band, an author-stated label); `"."` where the article names the diagnosis but grades no severity. Do **not** infer a band from a bare diagnosis — `BaseStatusReportedYN` carries that fact instead. Two frozen rows hold `1`, which `_lib.clean()` silently converts to `NaN` and Table 1 counts as "Not reported". |
| `BaseStatusReportedYN` | binary | **Derived, not extracted** — computed by `_lib.base_status_reported()` after the merge; do not emit it from an extraction response. `1` where the article characterizes the target condition at baseline, **whether or not a severity band is graded**: naming the diagnosis (e.g. "patients with alcohol use disorder") counts. `"."` where there is no analysed sample to characterize (review, protocol, wrong source document), keyed off a missing `SampleSize_NFinal`. `0` where the analysed sample did not have the condition at baseline — currently only Nicholas 2022, whose sample had zero current AUD by MINI; that list is `_lib.BASE_STATUS_NOT_REPORTED`. This field, not `BaseStatus`, feeds Table 3's "Baseline status reported" indicator, so the gap map measures whether baseline status was reported while Table 1 keeps an ungraded row honestly in "Not reported". |
| `Age_Median` | enum | `<30` / `30-50` / `50+` / `"."` — the **bracket** containing the sample's median or mean age. **Closed enum only; never a numeric age.** Four frozen rows hold raw numbers (`48.5` ×1, `51.0` ×3); `clean()` maps only the literal string `'45'` — a value that does not occur anywhere in the data — so all four currently become `NaN` and are counted "Not reported" in Table 1. Emitting the bracket at extraction time is the fix; the stale `'45'` branch in `clean()` is noted as dead code, not removed. |
| `PercentFem` | number 0–100 | Percentage identifying as female (AFAB if gender identity not reported). No `%` symbol. `"."` if not reported. |
| `RaceEthnicity_BIPOCPercent` | number 0–100 | Percentage Black, Indigenous, or People of Color = all non-white. Sum non-white groups if not given as one figure and show the arithmetic in `rationale`. Hispanic/Latino ethnicity crosses racial categories and is reported inconsistently — capture as reported and note the ambiguity. `"."` if not reported. |
| `SocioeconomicStatusYN` | binary | Were low-SES participants explicitly included or described (income reported, low-income eligibility criteria, public-insurance enrolment)? `1`/`0`/`3`/`"."`. |
| `Country_USvsNonUS` | enum | `US` / `NonUS` / `Both` / `"."`. **Sharpened, and this is a correction rather than a tightening.** The source prompt specifies free-text country names, but the frozen data contains only the four tokens `US` (16), `NonUS` (23), `Both` (1), `USA` (3), `.` (1) — and both consumers assume the enum: `_lib.COUNTRY_MAP` maps `USA`→`US`, `US`→`US`, `NonUS`→`Non-US`, `Both`→`US and Non-US`, and Table 1 counts only the three mapped labels. A literal country name such as `"Brazil"` would pass through `COUNTRY_MAP` unchanged and then match none of Table 1's buckets, silently counting as zero everywhere. Emit one of the four tokens; put the actual country name(s) in `rationale`. Emit `US` rather than `USA` for new rows; `USA` remains valid on read for the frozen comparison. |
| `RecruitmentRepresentYN` | binary | Was recruitment reflective of real-world community or clinical populations, as opposed to highly screened or volunteer-only samples? `1`/`0`/`3`/`"."`. |

### 4.6 Intervention and harms

| Field | Type | Valid values / rule |
|---|---|---|
| `InterventionDescription` | text | ≤ 30 words: substance, dose, route, session structure, setting. `"."` if not described. |
| `InterventionTherapy` | binary | Was therapy, counseling, integration, and/or preparation included beyond drug administration alone? `1`/`0`/`3`/`"."`. |
| `HarmsAssessed` | binary | Were harms or adverse events assessed as part of the study? `1`/`0`/`3`/`"."`. Preserved verbatim as a numeric binary (decision 2) because `BINARY_COLS`, Table 2, and Table 3 consume it. **Must agree with `SafetyReported`** (§4.10): `SafetyReported = "Y"` ⟺ `HarmsAssessed = 1`; `SafetyReported = "N"` ⟺ `HarmsAssessed ∈ {0, 3, "."}`. Blocking. |

### 4.7 Equity and cultural framing

| Field | Type | Valid values / rule |
|---|---|---|
| `CulturalFraming` | binary | Explicit reference to racial/ethnic identity, historical or intergenerational trauma, or culturally specific language or context? `1`/`0`/`3`/`"."`. |
| `IndigenousFramework` | binary | Were Indigenous frameworks, knowledge systems, or traditional practices explicitly referenced or integrated? `1`/`0`/`3`/`"."`. Describing a plant medicine's traditional origin in passing is not integration; code `0` and note the distinction. |
| `Reciprocity` | binary | Did the study explicitly address reciprocity or benefit-sharing for marginalized or Indigenous groups (community partnership, compensation, co-authorship, data sovereignty)? `1`/`0`/`3`/`"."`. |

### 4.8 Outcomes and follow-up

| Field | Type | Valid values / rule |
|---|---|---|
| `Followup in months` | number | Longest follow-up duration, in months. **Sharpened**: measure from **end of treatment** when the article reports both an end-of-treatment and a from-baseline horizon, and say which in `rationale` when the two differ materially. Conversion guide: 2 weeks = 0.5, 1 month = 1, 6 months = 6, 1 year = 12. `"."` if not reported. **This is a continuous field, not a binary** — it is deliberately excluded from `BINARY_COLS` because `3` means three months here, not "does not apply". Consumed by Table 5 at bin boundaries 1, 3, 6, 12, 24. |
| `BehaviorChangeMeasured` | binary | Behavioral changes measured (use frequency, craving, compulsive behavior)? `1`/`0`/`"."`. |
| `PhysicalChangeMeasured` | binary | Physical or biological outcomes measured (biomarkers, physiological measures, vital signs, CO levels)? `1`/`0`/`"."`. |
| `MentalHealthChangeMeasured` | binary | Mental-health outcomes measured (depression, anxiety, PTSD, well-being scales)? `1`/`0`/`"."`. |
| `QualityOfLifeMeasured` | binary | Quality of life explicitly measured with any instrument? `1`/`0`/`"."`. |
| `Implementation Outcome` | binary | Implementation outcomes measured — feasibility, acceptability, fidelity, reach, adoption, sustainability (Proctor et al. or equivalent)? `1`/`0`/`"."`. Space in the column name preserved verbatim. |
| `ReductionMeasured` | binary | Partial behavioral reduction reported as a distinct outcome (reduced use, harm-reduction endpoint — not just cessation)? `1`/`0`/`"."`. |
| `CessationMeasured` | binary | Complete cessation of the target behavior reported as an outcome? `1`/`0`/`"."`. |
| `RelapseMeasured` | binary | Relapse or return to use explicitly tracked? `1`/`0`/`"."`. |
| `MortalityMeasured` | binary | Mortality measured or reported as an outcome? `1`/`0`/`"."`. Deaths reported only as adverse events count here as `1`, and also generate an `ae_events` row. |

These nine outcome binaries are documented in the source prompt with no `3` code. `recode_binary()` maps `3` to `"Does not apply"` uniformly across all of `BINARY_COLS`, so a `3` would not break anything, but it is not a valid emission — use `"."`.

### 4.9 Substances

| Field | Type | Valid values / rule |
|---|---|---|
| `Psilocybin` | binary | Psilocybin, including whole mushrooms, studied as an intervention? `1`/`0`. |
| `Ayahuasca` | binary | Ayahuasca (DMT + MAOI brew)? `1`/`0`. |
| `LSD` | binary | LSD? `1`/`0`. |
| `Mescaline` | binary | Mescaline or peyote? `1`/`0`. |
| `Ibogaine` | binary | Ibogaine or iboga? `1`/`0`. |
| `MDMA` | binary | MDMA? `1`/`0`. |
| `Ketamine` | binary | Ketamine, including esketamine? `1`/`0`. |
| `Cannabis` | binary | Cannabis (THC, CBD, or combinations)? `1`/`0`. |
| `OtherPsychedelic` | binary | Other psychedelics not listed above (DMT alone, 5-MeO-DMT, salvia, ibogaine analogues, novel compounds)? `1`/`0`. **Any substance outside the eight named keys routes here** — that is what the column is for. Name it in `rationale`. |
| `MultiplePsychedelic` | binary | Did the study use or compare more than one psychedelic substance? `1`/`0`. Must be `1` when two or more of the nine substance binaries are `1`. |

**These are intervention flags, not exposure flags.** Code `1` only for a substance administered as part of the study's intervention. A comparator drug that is itself a psychedelic (Hollister 1969 compares LSD against dextroamphetamine; a dextroamphetamine arm sets no flag, whereas an LSD-vs-psilocybin comparison sets both) counts; a substance merely discussed, or used by participants before enrolment, does not.

`_lib.primary_substance()` returns the **first** positively-coded column in the fixed order `Psilocybin, LSD, Mescaline, Ayahuasca, Ibogaine, OtherPsychedelic, MDMA, Ketamine, Cannabis`, and that return value is the plot's `substance` — driving color, grouping, and legend. For a multi-substance study, the plot therefore shows only the first in that order. This is existing behavior, preserved; note the full substance list in `rationale` so a reader of the results table can see what the single plotted label omits.

### 4.10 Adverse-event gate fields (added — decision 6)

Imported as a block from `observational_codebook.md` §3. Importing the severity rubric without these leaves `ae_events` uninterpretable: no denominator, no arm scope, and no way to distinguish a real zero from silence.

| Field | Type | Valid values / rule |
|---|---|---|
| `SafetyReported` | enum | `Y` / `N` — did the article assess or report AEs/safety at all? The gate that separates "no AEs" from "didn't look". Must agree with `HarmsAssessed` (§4.6). |
| `AnyAEReported` | enum | `Y` / `N` / `NA` — `NA` only when `SafetyReported = N`. |
| `NumDistinctAEs` | integer / `"Not numbered"` / `"NA"` | Count of **distinct AE types**, the primary counting unit. "12 participants reported headache" is one type. `0` only when `AnyAEReported = N`. |
| `NParticipantsWithAE` | integer / `"."` / `"NA"` | Participants with ≥ 1 AE, when reported. Integer, `"."`, or `"NA"` only — never `"Not numbered"`. |
| `AE_denominator` | integer / `"Not numbered"` / `"."` | The population AE counts were assessed over — often the safety or enrolled population, which may differ from `SampleSize_NFinal`. **Never takes `"NA"`**: when no safety assessment was done, use `"."`. |
| `ArmScope` | enum | `psychedelic_arm` / `pooled` / `NA` — scope of the AE counts and demographics. Use `psychedelic_arm` whenever every reported AE/demographic value comes only from psychedelic-exposed participants, **including single-arm studies**, whose entire sample is exposed by definition. Use `pooled` only when reported values mix exposed and comparator participants. Reserve `NA` for the rare case where arm scope genuinely does not apply — not merely because the study has one arm. |
| `WorstSeverity` | enum | `Mild` / `Moderate` / `Severe` / `None` / `NA`. Equals the maximum `Severity` across this article's `ae_events` rows; `None` when `AnyAEReported = N`; `NA` when `SafetyReported = N`. |

**Three-state AE presence — do not collapse:**

- Article states no AEs occurred → `SafetyReported = Y`, `AnyAEReported = N`, `NumDistinctAEs = 0`, `WorstSeverity = None`, zero `ae_events` rows.
- AEs reported but not counted → `SafetyReported = Y`, `AnyAEReported = Y`, `NumDistinctAEs = "Not numbered"`.
- Article silent on AEs/safety entirely → `SafetyReported = N`, `AnyAEReported = NA`, `NumDistinctAEs = NA`, `WorstSeverity = NA`, `AE_denominator = "."`, zero `ae_events` rows.

---

## 5. `ae_events` — one row per distinct AE

| Field | Type | Valid values / rule |
|---|---|---|
| `AE_ID` | text | `{StudyID}_AE01`, `{StudyID}_AE02`, … in order of first mention. Unique within article. |
| `StudyID` | text (FK) | Must exist in `clinical_master.StudyID`. |
| `AE_type` | enum | `AE` / `challenging_experience` / `both`. CEQ-sense challenging-experience phenomenology is expected and in-session — flag it rather than silently counting it as a clinical AE. |
| `Description` | text | Concise description of the event as reported, ≤ 30 words. |
| `NAffected` | integer / `"."` | Number of participants who experienced this AE type. **Added for the clinical corpus**, where trial AE tables routinely report per-event counts ("headache 12/25") that the observational corpus rarely gave. Without it, `NumDistinctAEs` and `NParticipantsWithAE` cannot be reconciled to the per-event detail trials publish. `"."` when the article names the AE without a count. |
| `Onset` | enum | `in-session` / `post-session-acute` (hours–days) / `delayed` (weeks+) / `unknown`. Supports the PAT severity adaptation. |
| `Severity` | enum | `Mild` / `Moderate` / `Severe`, per §6. |
| `SeverityIndeterminate` | enum | `Y` / `N` — `Y` when graded on insufficient detail (defaulted per §6.4). Every `Y` goes to the human-review queue. |
| `SeveritySource` | enum | `author` (authors assigned a CTCAE grade or SAE flag — use theirs) / `rubric` (graded via §6). |
| `InterventionRequired` | enum | `Y` / `N` / `"."` — did the event require active intervention (pharmacological rescue, etc.)? |
| `MeetsFDASerious` | enum | `Y` / `N` — meets any FDA seriousness criterion (§6.2). Drives the Moderate/Severe tiebreak. |

**No `Rationale` field inside `ae_events` objects.** Every non-obvious call, for both the article and each AE, goes in the top-level `rationale` object (§7), matching the implemented observational contract.

---

## 6. Severity rubric (authoritative)

Three-level scale grounded in **CTCAE v5.0** collapsed to three bands, cross-walked with **FDA seriousness criteria**, adapted for psychedelic-assisted therapy (PAT). Reproduced here verbatim from `observational_codebook.md` §5; `RubricVersion = v1` denotes the same text in both pipelines, and a divergence requires bumping one of them.

**Core adaptation principle — preserved.** In psychedelic-assisted therapy, intense in-session anxiety, fear, perceptual distortion, and challenging-experience phenomenology (Barrett CEQ sense) are *expected* effects of dosing. Grade them **by consequences and intervention need, not by subjective intensity during dosing.** A high CEQ score alone → **Mild**, unless accompanied by intervention need or persistence beyond the dosing period.

**Severity source precedence.** If the authors assign a CTCAE grade or an SAE flag, use theirs (`SeveritySource = author`). Otherwise apply this rubric (`SeveritySource = rubric`).

### 6.1 CTCAE grade → 3-band collapse

| CTCAE v5.0 grade | Band | Rule |
|---|---|---|
| Grade 1 | **Mild** | Asymptomatic/mild; no intervention indicated. |
| Grade 2 | **Moderate** | Minimal/local/noninvasive intervention indicated, or limiting age-appropriate instrumental ADL. |
| Grade 3 | **Moderate**, unless it meets an FDA seriousness criterion → **Severe** | FDA-seriousness is the single tiebreaker between the top two bands. |
| Grade 4 | **Severe** | Life-threatening; urgent intervention indicated. |
| Grade 5 | **Severe** | Death related to AE. |
| **Any grade** meeting an FDA seriousness criterion (§6.2) | **Severe** | Seriousness overrides the grade-based band upward, never downward. |

**Grade-3 tiebreak.** A Grade 3 event is **Moderate by default, Severe only if it meets an FDA seriousness criterion.** No event falls in two rows.

Verify the exact CTCAE v5.0 anchor wording against the current source document before this rubric enters the manuscript methods.

### 6.2 FDA seriousness criteria (serious if it meets **any** one)

- Death
- Life-threatening event
- Inpatient hospitalization or prolongation of existing hospitalization
- Persistent or significant disability/incapacity
- Congenital anomaly/birth defect
- A medically important event requiring intervention to prevent one of the above

PAT-specific events that are `Severe` because they typically meet a seriousness criterion or are labeled SAEs: suicidal behavior/attempt, psychosis or prolonged psychotic reaction, seizure, serious cardiovascular event, hospitalization, HPPD, or any event the authors themselves label an SAE.

### 6.3 Operational band definitions (PAT context)

- **Mild** — Transient, expected, self-limiting; no or minimal intervention; resolves within/shortly after the session; no functional impairment beyond the acute dosing period. Expected acute drug effects (transient anxiety, nausea, headache, mild transient BP/HR elevation, perceptual distortion, reassurance-resolved challenging experience) default here unless they escalate.
- **Moderate** — Requires active intervention (benzodiazepine rescue, antihypertensive, antiemetic) **or** causes functional impairment persisting beyond the dosing day (persisting anxiety, low mood, sleep disturbance lasting days to a few weeks) — but meets **no** FDA seriousness criterion.
- **Severe** — CTCAE Grade 4–5, **or** any event meeting an FDA seriousness criterion, **or** any author-labeled SAE.

### 6.4 Under-specified AEs

When an AE is reported with too little detail to grade: grade on whatever intervention/outcome/seriousness signals are present. Absent any such signal, default **Mild** and set `SeverityIndeterminate = Y`. This is a deliberate safety-direction choice — defaulting such events to Severe would overstate harm as much as ignoring them understates it. Therefore:

1. Flag every such grade and route it to human review before publication.
2. Record the missing information in that AE's `rationale.ae_events` entry.
3. Keep the flag usable as a filter, so a sensitivity analysis can recompute AE rates with indeterminate events excluded or escalated.

Never silently absorb an ungradeable event into a point estimate.

### 6.5 Where the clinical context differs from the observational one

Trial reports carry author-assigned CTCAE grades and explicit SAE designations far more often than naturalistic reports do, so **`SeveritySource = author` will be the common case in the 2010+ stratum and near-absent in the pre-1980 one** — CTCAE and its NCI predecessors postdate that literature entirely. Two consequences:

- A pre-1980 article claiming `SeveritySource = author` **on the basis of a CTCAE grade** is a warning at the gate (§8): those authors cannot have used a scale that did not yet exist. They may legitimately have used their own severity or seriousness language, which is still a valid `author` source — the rationale entry must say which.
- `SeverityIndeterminate = Y` should be expected to concentrate in the pre-1980 stratum, where harms are described narratively rather than tabulated. Any AE-rate comparison across eras must therefore stratify on `SeveritySource` and `SeverityIndeterminate`, or it will read a reporting-convention change as a safety difference.

---

## 7. Response contract

The model returns, per article, a **single JSON object** with two halves and nothing else — no prose, no markdown fences:

```json
{
  "data": {
    "article": { "…all 72 clinical_master fields…" },
    "ae_events": [ { "…all ae_events fields…" } ]
  },
  "rationale": {
    "article": {
      "Outcome": "…", "SD": "…", "PVal": "…", "SampleSize_NFinal": "…",
      "MethodologyDescribedYN": { "criteria": { … }, "n_met": 12, "note": "…" },
      "FieldName": "why this non-obvious call was made"
    },
    "ae_events": { "AE_ID": "why this severity / type / onset" },
    "config_proposal": {
      "metric": "…", "measure": …, "method": "…", "confidence": "…",
      "direction": 1, "df_error": …, "note": "…",
      "tier2_category": "…", "tier2_basis": "…", "computed_or": …
    }
  }
}
```

Rules:

- Both halves are valid JSON. `data` is machine-validated against §4–§5 and the §8 gate; `rationale` is split into `rationale_log.md` at merge.
- Source-variable binaries use only `1`, `0`, `3`, `"."` — never `"Y"`, `"N"`, `true`, `false`, or other strings. Added QC/provenance fields use only their listed string enums (§3.2).
- `rationale.article` requires entries for `Outcome`, `SD`, `PVal`, `SampleSize_NFinal` on **every** article, and for `MethodologyDescribedYN` as the structured object above. Other fields need entries only where the call was non-obvious — but every use of `3`, every use of `"NA"`, every `SeverityIndeterminate = Y`, and every field affected by garbled input must be explained.
- `rationale.config_proposal` is the model's *proposal* for the `_config_<condition>.py` entries. It never enters `data` and is applied only through the ratification rule in `clinical_system_design.md` §5.3.
- If input text appears garbled or truncated, code the affected fields not-reported and say so in `rationale`. **Never construct a decoding theory for garbled or internally inconsistent numbers** — report the number exactly as printed, or code it not-reported, and flag the inconsistency. A fabricated decode is worse than an honest "not reported."

---

## 8. Validation gate — field level

Deterministic, run at merge. **Blocking failures prevent any output table from being written**; only `validation_report.txt` is produced. Architecture-level framing is in `clinical_system_design.md` §8.

**Blocking**

- **Column set** exactly the 54 carried + 18 added names, spelled verbatim including `Clincial Trial YN`, `Funding/COI YN`, `Retention (%)`, `Followup in months`, `Implementation Outcome`, `Double+Blind`, `Pos Result Y/N`.
- **Type/enum** per field against §4–§5. Source binaries ∈ {`1`, `0`, `3`, `"."`}; `BaseStatus` ∈ {`Severe`, `Moderate`, `Mild`, `"."`}; `Age_Median` ∈ {`<30`, `30-50`, `50+`, `"."`}; `Country_USvsNonUS` ∈ {`US`, `NonUS`, `Both`, `"."`}; percent fields numeric 0–100; `Followup in months` numeric ≥ 0.
- **Eligibility** — `EligibilityFailedCriterion = NA` iff `EligibleYN = Y`; `EligibilityNote` non-empty and not `"."`/`"NA"` whenever `EligibleYN = N`; no contradiction with `Clincial Trial YN` (§4.2).
- **Harms/safety** — `SafetyReported = Y` ⟺ `HarmsAssessed = 1`.
- **AE gate consistency** — the three-state rules in §4.10; `WorstSeverity` = max `Severity` across the article's `ae_events`; `AnyAEReported = Y` ⇒ ≥ 1 `ae_events` row or `NumDistinctAEs = "Not numbered"`; referential integrity of `ae_events.StudyID`; every `SeverityIndeterminate = Y` row present in `human_review_queue.csv`.
- **Checklist arithmetic** — `n_met` = count of `"Y"` across the 14 criteria; `MethodologyDescribedYN = 1` iff `n_met ≥ 13`.
- **Internal design consistency** — `Double+Blind = 1` requires `BlindingYN = 1`; `MultiplePsychedelic = 1` whenever ≥ 2 substance binaries are `1`.
- **Provenance completeness** — `Model`, `PromptVersion`, `RubricVersion`, `Temperature`, `text_source`, `text_format`, `SourcePDF` non-empty on every row.
- **Identity** — `first_author_surname(Citation/Title)` equals the frozen manifest surname; `(surname, Year)` unique across the master.
- **Config-key existence** — every eligible study has `EFFECT_SIZE_EXTRACTIONS` and `CONVERSION_RULES` entries, and every Tier-1-excluded eligible study has a `TIER2_RATINGS` entry; reported as a named list of `(surname, year)` tuples, never a bare `KeyError`.
- **Config proposal discipline** — `confidence = clean` only for `d`, `g`, `eta_p`, `F`, `chi2`, `OR`, `RR`; `method = "F"` requires numeric `df_error`.
- **Rationale completeness** — `Outcome`, `SD`, `PVal`, `SampleSize_NFinal`, and the structured `MethodologyDescribedYN` object present in `rationale.article` for every article.

**Warning (reported, non-blocking)**

- `EligibleYN = N`, with the note quoted.
- `Clincial Trial YN ∈ {3, "."}` while criterion (a) passed.
- Checklist criterion `harms = N` with `HarmsAssessed = 1`; `funding_coi = N` with `Funding/COI YN = 1`; `comparator = N` with `Comparator = 1`. **Only these directions** — the reverse is legitimate, since a criterion asks whether an element was described and the binary asks whether it was present.
- `text_format = text` or `text_source = OCR`, with the failing fidelity check named.
- A pre-1980 article with `SeveritySource = author` justified by a CTCAE grade (§6.5).
- Any config entry auto-ratified rather than human-ratified.
- A `substance` value outside `SUBSTANCE_ORDER_UNIFIED`, which renders in fallback grey.
- `Retention (%)` within 2 points of the 80% threshold, since the value flips a Table 2 and Table 3 cell.

---

## 9. What was sharpened, and why

Every change from `opus_extraction_prompt.md`, so a reviewer can see exactly what moved.

| # | Field | Change |
|---|---|---|
| 1 | `Outcome` | "Largest **or** primary" → **stated primary**, with an explicit precedence ladder. Largest and primary are different statistics; choosing the largest biases the forest plot upward. |
| 2 | `SD` | Degrees of freedom now **required in parentheses** for any statistic that has them. `convert_to_d()` needs `df_error` for `F`; the frozen dataset lost df into free-text notes. |
| 3 | `PVal` | `"NS"` is recorded verbatim and **never** converted to a number or threshold. |
| 4 | `SampleSize_NFinal` | Must be the denominator of the analysis that produced `Outcome`, including when that is a subgroup. `variance_g()` assumes `n1 = n2 = N/2` on exactly this number. |
| 5 | All four above | `rationale` entry now **mandatory on every article**, not only non-obvious ones. |
| 6 | `Country_USvsNonUS` | Free-text country names → the closed enum `US` / `NonUS` / `Both` / `"."`. **A correction, not a tightening**: the source prompt's free-text spec contradicts both the frozen data and the two consumers (`COUNTRY_MAP`, Table 1), which would silently count a literal country name as zero everywhere. |
| 7 | `Age_Median` | Closed enum only, never a raw age. Four frozen rows hold numerics that `clean()` converts to `NaN`; its `'45'` remap targets a value not present in the data. |
| 8 | `BaseStatus` | Closed enum only. Two frozen rows hold `1`, currently silently `NaN`. |
| 9 | `Retention (%)` | Denominator defined: randomized N when both randomized and enrolled are reported, else enrolled. Previously "enrolled" with no rule for randomized designs. |
| 10 | `Followup in months` | Measured from **end of treatment** when both horizons are reported. Previously "from baseline **or** end of treatment", which made the field non-comparable across studies — and it feeds Table 5's bin boundaries. |
| 11 | `MethodologyDescribedYN` | Structured 14-key rationale object with gate-checked arithmetic; explicit rule that a criterion is met when the element is *described*, including described as absent. |
| 12 | `Pos Result Y/N` | Kept in RCT framing (unlike the observational `PosResult` redefinition), with an explicit rule for single-arm studies and for when `3` applies. |
| 13 | Substance binaries | Explicit "intervention flags, not exposure flags" rule, and a note that `primary_substance()` plots only the first in a fixed order. |
| 14 | `HarmsAssessed` | Now tied to `SafetyReported` by a blocking equivalence, so the two conventions cannot drift. |
| 15 | `Year` | Version of record specified (issue year over online-first) because a ±1 disagreement breaks the `(surname, Year)` config key. |

---

## 10. Cross-references

- Architecture, workflow, conversion, adapter, validation gate, visual regression: `clinical_system_design.md`.
- Old↔new field crosswalk, row identity, comparison procedure, acceptance criteria: `clinical_old_new_mapping.md`.
- Severity rubric source of record and the observational pipeline it is shared with: `observational_codebook.md` §5, `observational_studies_system_design.md` §3.
