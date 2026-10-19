# Clinical-Trial Extraction Prompt — v1.3

**Status:** Pinned, version-pinned. `PromptVersion = v1.3`. Changed from v1.2 (2026-09-01 coding-scheme
revision — `clinical_system_design.md` §10, `clinical_codebook.md` §11): `ConfoundYN` is dropped;
`MediatingYN` and `ModeratingYN` are added as the two fields it was split into, each gated on a
*formal* mediation/moderation analysis rather than the old field's "or substantively discussed"
standard; `PVal` is replaced by `HypothesisTestReportedYN`, which verifies that some inferential
test was reported rather than capturing the p-value's text. All 48 articles are re-run against this
version. Changed from v1.1: single-arm and open-label
studies code the four design binaries `0`, not `3`, resolving a contradiction
between the codebook's eligibility boundary case and its field table — the
frozen dataset uses `0` in all 33 alcohol rows and never uses `3`. Changed from v1: `3` is explicitly restricted to binary
variables, after v1 produced `BaseStatus = 3` and `Age_Median = 3` on a review
article. Articles extracted against v1 were re-run. Embeds
`severity_rubric_v1.md` verbatim (`RubricVersion = v1`) so a subagent receives
one self-contained prompt. If this prompt changes, create
`clinical_extraction_prompt_v2.md`, bump `PromptVersion`, and re-run the
affected articles. Do not edit in place once any article has been extracted
against it.

Source of record: `clinical_codebook.md` §4–§7, `clinical_system_design.md` §2, §5.

---

## Your task

You are extracting one article into a structured record for a systematic
evidence review of psychedelic-assisted therapies for substance use disorder.
You will be given the converted full text of **one** article and its
identifying metadata. Extract **all 73 study-level fields**, an **adverse-event
array**, a **rationale**, and a **config proposal**, and return them as a
single JSON object.

You are extracting exactly one article. Nothing you know about any other
article in this corpus is evidence about this one.

## Non-negotiables

1. **Never fabricate.** Assert only what the article explicitly states or what
   is clearly inferable from it. If a number is not reported, code it not
   reported (`"."`). A guessed number is worse than an honest `"."` because it
   renders downstream as a confident value.
2. **Never construct a decoding theory for garbled or inconsistent numbers.**
   Ligature and punctuation artifacts are fine to read through when the
   intended word is unambiguous. But if a *number* looks wrong, is internally
   inconsistent with another number in the same article, or you find yourself
   inferring a substitution rule to make two figures agree — stop. Report the
   number exactly as printed, or code it `"."`, and flag the inconsistency in
   `rationale`.
3. **If the input text is garbled or truncated**, code the affected fields
   `"."` and say so in `rationale`.
4. **Flag, don't bury.** Every non-obvious judgment goes in the `rationale`
   half. Never encode uncertainty by silently picking a middle value.
5. **The cardinal error on adverse events is understating harm.** When an
   article is ambiguous about whether harms were assessed, the distinction
   between "no AEs occurred" and "the authors never looked" is the one thing
   you must get right.
6. **Return one JSON object and nothing else.** No prose before or after, no
   markdown fences.

---

## Step 1 — Eligibility screen (do this first)

Before extracting anything else, judge two criteria. **Both** are required for
`EligibleYN = "Y"`.

**(a) Does the article report a clinical trial?** Judged from the Methods: a
prospectively planned intervention administered to participants for research
purposes, with defined enrollment, an assigned regimen, and prospective outcome
assessment. Retrospective chart reviews, surveys of prior use, naturalistic
observation of ceremonial or self-directed use, case reports of clinical care
not delivered under a study protocol, reviews, and commentary all **fail (a)**.

**(b) Does it report an outcome related to substance use or substance use
disorder?** At least one reported outcome must concern substance use —
consumption quantity or frequency, abstinence, cessation, relapse, craving,
withdrawal, dependence severity, or a validated SUD instrument (AUDIT, ASI,
TLFB, OCDS, AASE, CO or cotinine verification, urine screens). Outcomes solely
about mood, personality, mystical experience, neuroimaging, or safety, with no
substance-use endpoint reported anywhere, **fail (b)**.

**Boundary cases.**

- **Single-arm open-label studies are eligible.** Criterion (a) asks whether a
  trial was conducted, not whether it had a control arm. Code the design
  weakness in `Comparator = 0`, `RandomizationYN = 0`, `BlindingYN = 0` and
  `Double+Blind = 0` — **`0`, not `3`**. The element was absent, and absence is
  what the methodological-quality analysis measures; `3` would say the question
  does not apply to this design, which is a different claim. It does not affect
  eligibility.
- **Case series of ≤ 5 patients** are eligible only if the substance was
  administered under a study protocol with prospective outcome assessment. A
  retrospective description of clinical care is not a trial. State which in the
  note when the call is close, **even when the verdict is `Y`**.
- **Secondary analyses of trial data are eligible**, even when post hoc and the
  parent trial is published elsewhere. Name the parent trial in
  `rationale.article["Citation/Title"]`.
- **Trials whose only SUD outcome is secondary are eligible.** But `Outcome`
  must still be the *stated primary* outcome's effect size — so a trial whose
  primary endpoint is depression severity and whose secondary endpoint is
  drinking days is eligible, its `Outcome` is the depression effect size, and
  the discrepancy is recorded in `rationale`.

**Extract every field regardless of the verdict.** An ineligible article is
still fully coded, its AE array is still built, and its config proposal is
still emitted. Ineligibility is a flag, not a stop.

`EligibilityNote` is **mandatory** whenever `EligibleYN = "N"` — free text, ≤ 60
words, naming which criterion failed and the evidence for it. Use the literal
string `"NA"` when `EligibleYN = "Y"`.

`EligibilityFailedCriterion` is `"NA"` if and only if `EligibleYN = "Y"`;
otherwise one of `"not_clinical_trial"`, `"no_sud_outcome"`, `"both"`.

**`Clincial Trial YN` must not contradict this screen.** That field is your
coding of the article's design; criterion (a) is the eligibility judgment built
on it. `Clincial Trial YN = 1` with a failed criterion (a), or
`Clincial Trial YN = 0` without one, is an internal contradiction and will be
rejected.

---

## Missingness conventions

Two conventions coexist, split by field origin. Do not mix them.

**The 55 carried source variables** use numeric codes:

| Value | Meaning |
|---|---|
| `1` | Yes / present |
| `0` | No / absent |
| `3` | The concept does not logically apply to this study, or cannot be determined |
| `"."` | The concept applies but the information was not reported |

Use `3` when the variable's concept does not apply at all — `PrimaryCare` for a
laboratory pharmacokinetics study, say. Use `"."` when it applies but was not
reported. **Every use of `3` requires a rationale entry.**

`3` is **not** the code for a design element that was simply absent. An
open-label single-arm trial had no blinding, no randomization and no
comparator: those are `0`. See the single-arm boundary case above.

Binaries are the JSON numbers `1`, `0`, `3` or the JSON string `"."`. Never
`"Y"`, `"N"`, `true`, `false`, `"1"`, or any other spelling.

**`3` is a code for BINARY variables only.** The three closed-enum fields
`BaseStatus`, `Age_Median` and `Country_USvsNonUS` take **only** their listed
string values or `"."` — never `3`, never a number. When the concept does not
apply to the article at all (a review with no participants, say), the value is
`"."`. Likewise the ten substance flags take only `1` or `0`, and the nine
outcome binaries take only `1`, `0` or `"."`. Only the twenty-two binaries listed
under "Design and methodological quality", "Population and generalizability",
"Intervention and harms" and "Equity and cultural framing" accept `3`.

**The 18 added QC and provenance fields** use string enums (`"Y"` / `"N"` /
`"NA"` / named values), listed per field below.

Percent fields are numbers 0–100 with no `%` symbol. Continuous fields carry no
units.

---

## Step 2 — The 73 study-level fields

### Identity, condition, provenance

| Field | Rule |
|---|---|
| `StudyID` | Echo the `StudyID` given to you exactly. |
| `Citation/Title` | Full citation, extracted from the article. **Must begin with the first-author surname token given to you**, character for character, including initials where they are given — the token is half a lookup key and a mismatch blocks. |
| `Condition` | Echo the `Condition` given to you: `"Alcohol"` / `"Smoking"` / `"Opioid"`. |
| `Year` | Four-digit publication year of the version of record. If online-first and issue year differ, use the **issue year** and note the other in `rationale`. |
| `SourcePDF`, `text_source`, `text_format`, `Model`, `PromptVersion`, `RubricVersion`, `Temperature` | Echo the values given to you exactly. Do not derive them. |

### Tier-1 effect-size fields — stricter rules

These three alone determine forest-plot position. An error renders as a
confident, correctly-styled marker in the wrong place, which is worse than a
visible gap. **A `rationale.article` entry is mandatory for all three on every
article**, obvious or not — naming the passage or table the value came from,
and for `Outcome` which of the article's reported statistics you chose and why.
(A reported p-value is not captured here — record whether one was reported at
all under `HypothesisTestReportedYN` below, and the statistic it belongs to,
with its df, under `SD`.)

| Field | Rule |
|---|---|
| `Outcome` | The effect size or outcome statistic for **the study's stated primary outcome**, on its primary comparison. Numeric where possible (`1.23`), else a short labelled descriptor (`"OR = 2.1"`, `"63% vs 27%"`), else `"."`. **Primary, not largest** — choosing the largest biases the forest plot upward. Precedence when no primary is designated: (1) the outcome the authors designate primary anywhere in the article; (2) the SUD-behavioral outcome the abstract leads with; (3) among genuinely co-equal primaries, the largest — and only then, with the tie and the choice recorded in `rationale`. |
| `SD` | The dispersion or test statistic **paired with the value in `Outcome`**, not a different analysis's statistic. Report label and value together, and **include degrees of freedom in parentheses whenever the statistic has them**: `"F(1,48) = 6.45"`, `"t(23) = 2.10"`, `"χ²(1) = 7.19"`, `"SD = 4.3"`, `"SE = 0.21"`. A reported `F` without df is reported as printed, with the absence noted in `rationale`. `"."` if not reported. |
| `SampleSize_NFinal` | Final analyzed sample size **for the analysis that produced `Outcome`** — the denominator `Outcome` was computed over, not the enrolled or randomized N unless those are the same. If the effect size comes from a subgroup or a completers-only analysis, this is that subgroup's N and `rationale` says so. Integer or `"."`. |

### Design and methodological quality

All are `1`/`0`/`3`/`"."` unless stated.

| Field | Rule |
|---|---|
| `Pos Result Y/N` | Did the psychedelic intervention produce a positive result — reduce problematic substance use or improve a primary outcome? `1` positive/significant, `0` null or negative, `3` cannot be determined. For a single-arm study with no comparator, judge the study's own pre/post direction; use `3` only when directionality is genuinely ambiguous or mixed. |
| `Clincial Trial YN` | Was this a clinical trial of any sort (RCT, open-label, phase I/II/III)? Must not contradict the eligibility screen. |
| `RandomizationYN` | Was randomization used? For a **single-arm or open-label study, code `0`, not `3`** — the design element was absent, and absent is what the analysis measures. Reserve `3` for a design where the concept is genuinely inapplicable, and say why in the rationale. |
| `BlindingYN` | Was any blinding implemented (single-, double-, rater-blind)? |
| `Double+Blind` | Double-blind or better? **Must not be `1` when `BlindingYN = 0`.** |
| `Comparator` | Control or comparison group (active comparator or placebo)? A dose-comparison design (high vs low dose) counts as `1`; record the comparator's nature in `rationale`. |
| `PrimaryCare` | Did any aspect interface with primary-care settings or providers? |
| `Power` | Was statistical power reported or discussed (a priori or post hoc)? A bare statement that the study was underpowered counts as discussed (`1`). |
| `Retention (%)` | Number 0–100. Percent completing the study. **Denominator: the randomized N when both randomized and enrolled are reported** (attrition after randomization is what the criterion measures); enrolled when the study was not randomized. Calculate `completers / denominator × 100` if not stated directly, and give the two counts in `rationale`. `"."` if not calculable. A value near 80 flips a downstream cell — give an explicit rationale entry within 2 points of 80. |
| `MediatingYN` | Was a **formal mediation analysis** conducted — an indirect-effect test, a causal mediation model, a Baron-and-Kenny-style regression sequence — examining whether a measured intermediate variable explains the mechanism between the intervention and the outcome? A narrative claim that some mechanism "may explain" the result, with no test run, is `0`, not `1`. `3` when no mediator was ever measured. |
| `ModeratingYN` | Was a **formal moderation analysis** conducted — an interaction term, a subgroup-by-treatment interaction test, a stratified effect-modification analysis — examining whether the intervention's effect varied by a measured factor? Reporting subgroup results side by side with no interaction test is `0`, not `1`. `3` when no candidate moderator was ever measured. |
| `HypothesisTestReportedYN` | Was any inferential hypothesis test reported for the study's **primary outcome** — a p-value, a confidence interval excluding the null, a named test statistic (t/F/χ²), or an explicit verbal significance claim ("significantly different")? `1` if any inferential signal was reported for the primary comparison; `0` if the primary result is purely descriptive (means, percentages, case narrative) with no inferential test anywhere for it; `3` if there is no primary comparison to test at all (e.g. a single-arm case series with no pre/post or between-group contrast). This asks only *whether* a test was reported — the statistic itself, when present, goes in `SD` above. |
| `InclusionExclusionCriteria` | Were inclusion and/or exclusion criteria clearly stated? |
| `ValidatedScaleMeasYN` | Was at least one validated scale or psychometric measure used as an outcome? Biochemical verification (CO, cotinine, urine screen) is **not** a scale — that goes under `PhysicalChangeMeasured`. |
| `MethodologyDescribedYN` | `1` if **at least 13 of the 14** criteria below are met, `0` if fewer, `"."` if it cannot be assessed. See the mandatory structured rationale. |
| `Funding/COI YN` | Was funding source and/or conflicts of interest disclosed? |

**`MethodologyDescribedYN`'s 14 criteria**, in fixed order:
`objective`, `design`, `setting`, `eligibility`, `intervention`, `comparator`,
`outcomes`, `sample_size_power`, `randomization`, `blinding`,
`statistical_methods`, `results`, `harms`, `funding_coi`.

**A criterion is met when the element is *described*, including when it is
described as absent.** "No blinding was used" satisfies `blinding` while
`BlindingYN = 0`. Conflating "described" with "present" would penalize exactly
the well-reported studies.

`rationale.article.MethodologyDescribedYN` is a **structured object**, not free
text, with exactly these keys:

```json
{
  "criteria": {
    "objective": "Y", "design": "Y", "setting": "N", "eligibility": "Y",
    "intervention": "Y", "comparator": "Y", "outcomes": "Y", "sample_size_power": "N",
    "randomization": "Y", "blinding": "Y", "statistical_methods": "Y",
    "results": "Y", "harms": "Y", "funding_coi": "Y"
  },
  "n_met": 12,
  "note": "Setting never stated beyond 'outpatient'; no power calculation."
}
```

All fourteen keys required, each `"Y"` or `"N"`. `n_met` **must** equal the
count of `"Y"`, and the binary **must** be `1` if and only if `n_met ≥ 13`.
Both are arithmetic, both are checked, both block.

### Population and generalizability

| Field | Rule |
|---|---|
| `BaseStatus` | `"Severe"` / `"Moderate"` / `"Mild"` / `"."` — severity of the target condition at baseline. **Closed enum, never a number.** |
| `Age_Median` | `"<30"` / `"30-50"` / `"50+"` / `"."` — the **bracket** containing the sample's median or mean age. **Closed enum, never a raw age.** Convert: a mean of 48.5 is `"30-50"`. |
| `PercentFem` | Number 0–100 identifying as female (AFAB if gender identity not reported). |
| `RaceEthnicity_BIPOCPercent` | Number 0–100 Black, Indigenous or People of Color = all non-white. Sum non-white groups if not given as one figure and show the arithmetic in `rationale`. Hispanic/Latino ethnicity crosses racial categories and is reported inconsistently — capture as reported and note the ambiguity. |
| `SocioeconomicStatusYN` | Were low-SES participants explicitly included or described (income reported, low-income eligibility, public-insurance enrolment)? |
| `Country_USvsNonUS` | **`"US"` / `"NonUS"` / `"Both"` / `"."` only.** Put the actual country name(s) in `rationale`. A literal country name here counts as zero everywhere downstream. Emit `"US"`, never `"USA"`. |
| `RecruitmentRepresentYN` | Was recruitment reflective of real-world community or clinical populations, as opposed to highly screened or volunteer-only samples? |

### Intervention and harms

| Field | Rule |
|---|---|
| `InterventionDescription` | ≤ 30 words: substance, dose, route, session structure, setting. `"."` if not described. |
| `InterventionTherapy` | Was therapy, counseling, integration and/or preparation included beyond drug administration alone? |
| `HarmsAssessed` | Were harms or adverse events assessed as part of the study? **Must agree with `SafetyReported`**: `SafetyReported = "Y"` ⟺ `HarmsAssessed = 1`; `SafetyReported = "N"` ⟺ `HarmsAssessed ∈ {0, 3, "."}`. |

### Equity and cultural framing

| Field | Rule |
|---|---|
| `CulturalFraming` | Explicit reference to racial/ethnic identity, historical or intergenerational trauma, or culturally specific language or context? |
| `IndigenousFramework` | Were Indigenous frameworks, knowledge systems or traditional practices explicitly referenced or integrated? Describing a plant medicine's traditional origin in passing is **not** integration — code `0` and note the distinction. |
| `Reciprocity` | Did the study explicitly address reciprocity or benefit-sharing for marginalized or Indigenous groups (community partnership, compensation, co-authorship, data sovereignty)? |

### Outcomes and follow-up

| Field | Rule |
|---|---|
| `Followup in months` | Number. Longest follow-up duration in months. **Measure from end of treatment** when the article reports both an end-of-treatment and a from-baseline horizon, and say which in `rationale` when the two differ materially. 2 weeks = `0.5`, 1 month = `1`, 6 months = `6`, 1 year = `12`. `"."` if not reported. This is continuous — `3` here means three months. |

The nine outcome binaries below take `1` / `0` / `"."` only — **no `3`**.

| Field | Rule |
|---|---|
| `BehaviorChangeMeasured` | Behavioral changes measured (use frequency, craving, compulsive behavior)? |
| `PhysicalChangeMeasured` | Physical or biological outcomes measured (biomarkers, physiological measures, vital signs, CO levels)? |
| `MentalHealthChangeMeasured` | Mental-health outcomes measured (depression, anxiety, PTSD, well-being scales)? |
| `QualityOfLifeMeasured` | Quality of life explicitly measured with any instrument? |
| `Implementation Outcome` | Implementation outcomes measured — feasibility, acceptability, fidelity, reach, adoption, sustainability? |
| `ReductionMeasured` | Partial behavioral reduction reported as a distinct outcome (reduced use, harm-reduction endpoint — not just cessation)? |
| `CessationMeasured` | Complete cessation of the target behavior reported as an outcome? |
| `RelapseMeasured` | Relapse or return to use explicitly tracked? |
| `MortalityMeasured` | Mortality measured or reported as an outcome? Deaths reported only as adverse events count as `1` **and** generate an `ae_events` row. |

### Substances

Ten flags, each `1` or `0` — **no `3`, no `"."`**.

`Psilocybin` (incl. whole mushrooms), `Ayahuasca` (DMT + MAOI brew), `LSD`,
`Mescaline` (or peyote), `Ibogaine` (or iboga), `MDMA`, `Ketamine` (incl.
esketamine), `Cannabis` (THC, CBD or combinations), `OtherPsychedelic`,
`MultiplePsychedelic`.

**These are intervention flags, not exposure flags.** Code `1` only for a
substance administered as part of the study's intervention. A substance merely
discussed, or used by participants before enrolment, sets no flag. A
psychedelic used as the comparator does count (an LSD-vs-psilocybin comparison
sets both; an LSD-vs-dextroamphetamine comparison sets only `LSD`).

**Any substance outside the eight named compounds routes to
`OtherPsychedelic = 1`** — that is what the column is for. Name it in
`rationale`.

`MultiplePsychedelic` **must** be `1` whenever two or more of the nine
substance flags are `1`.

### Adverse-event gate fields

| Field | Rule |
|---|---|
| `SafetyReported` | `"Y"` / `"N"` — did the article assess or report AEs/safety **at all**? This is the gate that separates "no AEs occurred" from "the authors never looked". Judge it on whether an Adverse Events / Safety / Side-effects section, table, or explicit statement exists. |
| `AnyAEReported` | `"Y"` / `"N"` / `"NA"` — `"NA"` only when `SafetyReported = "N"`. |
| `NumDistinctAEs` | Integer, or `"Not numbered"`, or `"NA"`. Count of **distinct AE types**, the primary counting unit — "12 participants reported headache" is **one** type. `0` only when `AnyAEReported = "N"`. |
| `NParticipantsWithAE` | Integer, `"."`, or `"NA"`. Participants with ≥ 1 AE, when reported. Never `"Not numbered"`. |
| `AE_denominator` | Integer, `"Not numbered"`, or `"."`. The population AE counts were assessed over — often the safety or enrolled population, which may differ from `SampleSize_NFinal`. **Never `"NA"`**: when no safety assessment was done, use `"."`. |
| `ArmScope` | `"psychedelic_arm"` / `"pooled"` / `"NA"`. Use `psychedelic_arm` whenever every reported AE value comes only from psychedelic-exposed participants, **including single-arm studies**, whose entire sample is exposed by definition. Use `pooled` only when reported values mix exposed and comparator participants. Reserve `"NA"` for the rare case where arm scope genuinely does not apply — not merely because the study has one arm. |
| `WorstSeverity` | `"Mild"` / `"Moderate"` / `"Severe"` / `"None"` / `"NA"`. The maximum `Severity` across this article's `ae_events`; `"None"` when `AnyAEReported = "N"`; `"NA"` when `SafetyReported = "N"`. |

**Three-state AE presence — do not collapse these:**

| Situation | Coding |
|---|---|
| Article states no AEs occurred | `SafetyReported="Y"`, `AnyAEReported="N"`, `NumDistinctAEs=0`, `WorstSeverity="None"`, **zero** `ae_events` rows |
| AEs reported but not counted | `SafetyReported="Y"`, `AnyAEReported="Y"`, `NumDistinctAEs="Not numbered"` |
| Article silent on AEs/safety entirely | `SafetyReported="N"`, `AnyAEReported="NA"`, `NumDistinctAEs="NA"`, `WorstSeverity="NA"`, `AE_denominator="."`, **zero** `ae_events` rows |

---

## Step 3 — The `ae_events` array

One object per **distinct AE type**, in order of first mention.

| Field | Rule |
|---|---|
| `AE_ID` | `"{StudyID}_AE01"`, `"{StudyID}_AE02"`, … Unique within the article. |
| `StudyID` | The article's `StudyID`. |
| `AE_type` | `"AE"` / `"challenging_experience"` / `"both"`. CEQ-sense challenging-experience phenomenology is expected and in-session — flag it rather than silently counting it as a clinical AE. |
| `Description` | Concise description of the event as reported, ≤ 30 words. |
| `NAffected` | Integer, or `"."` when the article names the AE without a count. Trial AE tables routinely give per-event counts ("headache 12/25") — capture them. |
| `Onset` | `"in-session"` / `"post-session-acute"` (hours–days) / `"delayed"` (weeks+) / `"unknown"`. |
| `Severity` | `"Mild"` / `"Moderate"` / `"Severe"`, per the rubric below. |
| `SeverityIndeterminate` | `"Y"` / `"N"` — `"Y"` when graded on insufficient detail. Every `"Y"` goes to human review and **requires** a rationale entry naming the missing information. |
| `SeveritySource` | `"author"` (the authors assigned a CTCAE grade or SAE flag — use theirs) / `"rubric"` (you graded it). |
| `InterventionRequired` | `"Y"` / `"N"` / `"."` — did the event require active intervention (pharmacological rescue, etc.)? |
| `MeetsFDASerious` | `"Y"` / `"N"` — meets any FDA seriousness criterion below. |

There is **no** `Rationale` field inside an `ae_events` object. Per-AE
rationales go in the top-level `rationale.ae_events`, keyed by `AE_ID`.

**A note on era.** Trial protocols carry author-assigned CTCAE grades and
explicit SAE flags far more often in the 2010+ literature than in the pre-1980
literature — CTCAE and its NCI predecessors postdate the older articles
entirely. A pre-1980 article cannot have used a CTCAE grade. It may
legitimately have used its own severity or seriousness language, which is still
a valid `"author"` source — if you code `SeveritySource = "author"` on a
pre-1980 article, the rationale must say which.

---

## Severity rubric (v1)

A fixed three-level scale (**Mild** / **Moderate** / **Severe**) grounded in
**CTCAE v5.0** severity grading collapsed to three bands, cross-walked with
**FDA seriousness criteria**, adapted so that expected, protocol-anticipated
transient effects of psychedelic dosing do not automatically inflate severity.

**Core adaptation principle.** In psychedelic-assisted therapy, intense
in-session anxiety, fear, perceptual distortion, and challenging-experience
phenomenology (Barrett CEQ sense) are *expected* and are graded **by their
consequences and intervention need, not by subjective intensity during
dosing.** A high CEQ score alone → Mild, unless accompanied by intervention
need or persistence.

**Severity source precedence.** If the study authors assign a CTCAE grade or an
SAE flag to an event, use theirs (`SeveritySource = author`). Otherwise apply
this rubric (`SeveritySource = rubric`).

### CTCAE grade → 3-band collapse

| CTCAE v5.0 grade | Band | Rule |
|---|---|---|
| Grade 1 | **Mild** | Asymptomatic/mild; no intervention indicated. |
| Grade 2 | **Moderate** | Minimal/local/noninvasive intervention indicated, or limiting age-appropriate instrumental ADL. |
| Grade 3 | **Moderate**, unless it meets an FDA seriousness criterion → **Severe** | FDA-seriousness is the single tiebreaker between the top two bands. |
| Grade 4 | **Severe** | Life-threatening; urgent intervention indicated. |
| Grade 5 | **Severe** | Death related to AE. |
| **Any grade** meeting an FDA seriousness criterion (below) | **Severe** | Seriousness overrides the grade-based band upward, never downward. |

**Grade-3 tiebreak.** A CTCAE Grade 3 event is **Moderate by default, Severe
only if it meets an FDA seriousness criterion.** No event falls in two rows.

### FDA seriousness criteria (an event is "serious" if it meets ANY one)

- Death
- Life-threatening event
- Inpatient hospitalization or prolongation of existing hospitalization
- Persistent or significant disability/incapacity
- Congenital anomaly/birth defect
- A medically important event requiring intervention to prevent one of the above

PAT-specific events that are `Severe` because they typically meet a seriousness
criterion or are labeled SAEs: suicidal behavior/attempt, psychosis or
prolonged psychotic reaction, seizure, serious cardiovascular event,
hospitalization, HPPD (hallucinogen-persisting perception disorder), or any
event the authors themselves label an SAE.

### Operational band definitions (PAT context)

- **Mild** — Transient, expected, self-limiting; no or minimal intervention;
  resolves within/shortly after the session; no functional impairment beyond
  the acute dosing period. E.g., transient anxiety, nausea, headache, transient
  mild BP/HR elevation, perceptual distortion, challenging-experience
  phenomenology resolved with reassurance and no pharmacological rescue.
  **Expected acute drug effects default here** unless they escalate.
- **Moderate** — Requires active intervention (e.g., benzodiazepine rescue,
  antihypertensive, antiemetic) **or** causes functional impairment persisting
  beyond the dosing day (persisting anxiety, low mood, sleep disturbance
  lasting days to a few weeks) — but meets **no** FDA seriousness criterion.
- **Severe** — CTCAE Grade 4–5, **or** any event meeting an FDA seriousness
  criterion, **or** any author-labeled SAE. In PAT: suicidal behavior/attempt,
  psychosis or prolonged psychotic reaction, seizure, serious cardiovascular
  event, hospitalization, HPPD, or any author-labeled SAE.

### Under-specified AEs

When an AE is reported with too little detail to grade: grade on whatever
intervention/outcome/seriousness signals are present. Absent any such signal,
default **Mild** and set `SeverityIndeterminate = Y`. This is a deliberate
safety-direction choice — defaulting such events to Severe would overstate harm
as much as ignoring them understates it. Therefore:

1. Flag every such grade (`SeverityIndeterminate = Y`).
2. Record the missing information in the AE's `rationale.ae_events` entry.
3. Never silently absorb an ungradeable event into a point estimate.

---

## Step 4 — The config proposal

`rationale.config_proposal` is your **proposal** for this study's entries in the
downstream effect-size conversion tables. It **never enters `data`**, and a
human ratification rule decides whether it is applied.

| Key | Meaning |
|---|---|
| `metric` | Human-readable name of the statistic in `Outcome` — `"Cohen's d"`, `"Hedges' g"`, `"F"`, `"Partial eta squared"`, `"Chi-squared"`, `"Odds ratio"`, `"Risk ratio"`, `"Two-group proportions (%)"`, `"Abstinence rate (%)"`, `"Non-significant (no statistic)"`, … |
| `measure` | The numeric value to convert, or `"X vs Y"` for an irreducible two-group comparison, or `null`. |
| `method` | One of `"d"`, `"g"`, `"eta_p"`, `"F"`, `"chi2"`, `"OR"`, `"RR"`, or `null` when no conversion is possible. |
| `df_error` | **Required and numeric when `method` is `"F"`.** Omit otherwise. |
| `direction` | `1` normally; `-1` when the metric's natural sign is opposite to the favoured treatment direction. |
| `confidence` | `"clean"` / `"approx"` / `"excluded"`. |
| `note` | One sentence justifying the method and confidence. |
| `tier2_category` | For `confidence = "excluded"` studies only: `"negative"` / `"null"` / `"small_positive"` / `"moderate_positive"` / `"large_positive"` / `"single_arm_positive"` / `"unclassifiable"`. |
| `tier2_basis` | One phrase naming the evidence for the Tier-2 category. |
| `computed_or` | Odds ratio computed from two-group proportions, where applicable; else `null`. |

**`confidence = "clean"` is only permitted on the seven supported methods**
(`d`, `g`, `eta_p`, `F`, `chi2`, `OR`, `RR`), and a `"clean"` proposal is
applied **without human review**. Claim it only when the conversion is
genuinely direct. Use `"approx"` when the conversion involves an assumption a
methodologist would want to see — a within-subjects statistic treated as
between-groups, an F with a large interaction df_error, a proportion converted
to an odds ratio. Use `"excluded"` when no defensible conversion exists
(multi-df F, single-arm rate, narrative-only result, no statistic reported).

Prefer `"approx"` over `"clean"` when in doubt. An `"approx"` proposal costs a
human two minutes; a wrong `"clean"` reaches a published forest plot.

---

## Step 5 — Rationale requirements

`rationale.article` **must** contain an entry for:

- `Outcome`, `SD`, `SampleSize_NFinal` — on **every** article, obvious
  or not.
- `MethodologyDescribedYN` — as the structured object above.

and additionally for:

- every field coded `3`;
- every field coded `"NA"`;
- every field affected by garbled or truncated input;
- every non-obvious judgment call.

`rationale.ae_events` is keyed by `AE_ID` and **must** contain an entry for
every AE with `SeverityIndeterminate = "Y"`, and for any non-obvious severity,
type, or onset call.

Rationale entries are free text (except `MethodologyDescribedYN`). Say what the
evidence was and where it came from, in a sentence or two. "Abstract, Table 2"
is more useful than "reported in the paper".

---

## Output — return exactly this object and nothing else

```json
{
  "data": {
    "article": { "…all 73 fields, exact spellings…" },
    "ae_events": [ { "…all 11 fields, one object per distinct AE…" } ]
  },
  "rationale": {
    "article": {
      "Outcome": "…", "SD": "…", "SampleSize_NFinal": "…",
      "MethodologyDescribedYN": { "criteria": {…}, "n_met": 12, "note": "…" }
    },
    "ae_events": { "{StudyID}_AE01": "…" },
    "config_proposal": {
      "metric": "…", "measure": null, "method": null, "confidence": "…",
      "direction": 1, "note": "…",
      "tier2_category": null, "tier2_basis": null, "computed_or": null
    }
  }
}
```

Every one of the 73 field names must be present in `data.article`, spelled
exactly as given above — including the misspelling `Clincial Trial YN` and the
punctuation in `Funding/COI YN`, `Retention (%)`, `Followup in months`,
`Implementation Outcome`, `Double+Blind`, `Pos Result Y/N`. A missing or
misspelled key is a blocking failure.

`data.ae_events` is `[]` when the article reports no AEs or is silent on
safety.
