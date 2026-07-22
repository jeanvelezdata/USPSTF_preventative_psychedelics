# Observational Adverse-Event / Demographics Codebook

**Purpose.** Field-by-field conventions for the standalone adverse-event / demographics extraction (seven extracted items, 44 articles). Authoritative reference for the implementation pass. Architecture and workflow are in `observational_studies_system_design.md`; the source item list is `opus_extraction_prompt_observational.md`.

**Design principles.** Be precise, conservative, evidence-based. Assert only what is explicitly stated or clearly inferable. Never guess a number to fill a field — code it not-reported. For a *safety* dataset, the cardinal error is understating harm; every judgment call is flagged, not buried.

---

## 1. Source item list → stored fields (crosswalk)

| # | Source item | Stored field(s) | Table |
|---|---|---|---|
| 1 | Number of adverse events / challenging experiences | `NumDistinctAEs`, `NParticipantsWithAE`, `AnyAEReported`, `SafetyReported` (gate), one `ae_events` row per distinct AE | both |
| 2 | Severity of AE | `Severity`, `SeverityIndeterminate`, `SeveritySource`, `MeetsFDASerious`, `InterventionRequired`; article rollup `WorstSeverity` | `ae_events` / `articles` |
| 3 | Textual description of AE | `Description`, `AE_type`, `Onset` | `ae_events` |
| 4 | Number of participants | `N`, `AE_denominator`, `ArmScope` | `articles` |
| 5 | % positive outcomes | **Dropped** — not extracted (see design §5) | — |
| 6 | % BIPOC | `PctBIPOC` | `articles` |
| 7 | % Indigenous | `PctIndigenous` | `articles` |
| 8 | % Gender | `PctFemale`, `GenderCategory` | `articles` |
| — | provenance / identity (added) | `StudyID`, `Citation`, `Title`, `Year`, `Corpus/Prefix`, `text_source`, `Model`, `PromptVersion`, `RubricVersion`, `Temperature` | `articles` |
| — | study-design verification (added) | `IsObservational` — subagent-verified check that the article is an observational design, not an RCT; corpus-curation QC, not a source item | `articles` |
| — | substance / condition classification (added) | `Condition` (Alcohol/Smoking/Opioid — disorder targeted), `Substance` (treatment substance(s) administered) | `articles` |

This is a **standalone dataset**; no cross-dataset key convention is required.

---

## 2. Missingness conventions

| Value | Meaning | Applies to |
|---|---|---|
| `"."` | Information not reported / not found in the article | any non-gate field |
| `"NA"` (+ brief reason) | Concept does not apply to this study | any field where the concept is inapplicable |
| `"Not numbered"` | Concept applies and is present, but no count was given | `NumDistinctAEs`, `AE_denominator` (NOT `NParticipantsWithAE` — see §3, which is integer/`"."`/`"NA"` only) |
| numeric / enum | Reported value | as typed below |

**Three-state distinction for AE presence (do not collapse):**
- Article states no AEs occurred → `AnyAEReported = N`, `NumDistinctAEs = 0`, `WorstSeverity = "None"`.
- AEs reported but not counted → `AnyAEReported = Y`, `NumDistinctAEs = "Not numbered"`.
- Article silent on AE/safety entirely → `SafetyReported = N`, and all AE fields `= "NA"`.

At merge, `"."` → `NaN`. Percent fields are numbers 0–100 with no `%` symbol.

---

## 3. `articles` table — one row per article

| Field | Type | Valid values / rule |
|---|---|---|
| `StudyID` | text | Human-readable primary key. `Surname Year` is a reasonable default (add a suffix — `Surname Year b` — for collisions), or a sequential corpus ID. No main-pipeline key normalization required. |
| `Citation` | text | Full citation string. |
| `Title` | text | The article's title, exactly as printed in the article (read from the source text, not derived from `Citation`). `"."` if the title page/header is garbled or missing. |
| `Year` | integer | Four-digit publication year. |
| `Corpus/Prefix` | text | Substance/condition grouping label if used for file organization; else `"."`. |
| `Condition` | enum | `Alcohol` / `Smoking` / `Opioid` — the substance use disorder the intervention/study population targeted. Matches the three condition categories used in the main USPSTF pipeline (`scripts/_config_<condition>.py`), even though this dataset is standalone and does not join that pipeline. `"."` only if genuinely indeterminate from the text. |
| `Substance` | text | The psychedelic/dissociative substance(s) administered as the treatment/intervention, as reported (e.g., "Psilocybin", "MDMA", "Ketamine", "Ibogaine", "LSD", "Ayahuasca"). Comma-separate if the study used more than one. `"."` if not reported. |
| `IsObservational` | enum | `Y` / `N` — model-verified check that the article describes an observational study (cohort, case series/report, cross-sectional, retrospective/prospective observational) rather than an RCT or other controlled experimental design. This corpus is curated to be all-observational, so `N` is a likely curation mistake, flagged for human review — it does **not** stop extraction of the rest of the row. |
| `N` | integer or `"."` | Number of participants (final analyzed sample unless the article only reports enrolled). |
| `AE_denominator` | integer or `"Not numbered"` or `"."` | The population the AE counts were assessed over (often the safety/enrolled N, which may differ from `N`). |
| `ArmScope` | enum | `psychedelic_arm` / `pooled` / `NA` — scope of `N`, AE counts, and demographics. Use `psychedelic_arm` when restricted to the active arm(s). |
| `PctFemale` | number 0–100 or `"."` | % female (AFAB if gender identity not reported). |
| `GenderCategory` | text or `"."` | Reported gender breakdown label (e.g., "male/female", "incl. non-binary n=2"), so non-binary/other reporting is not lost. |
| `PctBIPOC` | number 0–100 or `"."` | % Black, Indigenous, or People of Color = all non-white. Sum non-white groups if not given as one figure. Hispanic/Latino ethnicity crosses racial categories — capture as reported and note inconsistency in rationale. |
| `PctIndigenous` | number 0–100 or `"."` | % Indigenous participants. **Subset of BIPOC** — also counted within `PctBIPOC`. |
| `SafetyReported` | enum | `Y` / `N` — did the article assess/report AEs or safety at all? The gate that separates "no AEs" from "didn't look." |
| `AnyAEReported` | enum | `Y` / `N` / `NA` — any AE reported? `NA` only when `SafetyReported = N`. |
| `NumDistinctAEs` | integer or `"Not numbered"` or `"NA"` | Count of **distinct AE types** (primary counting unit). `0` only when `AnyAEReported = N`. |
| `NParticipantsWithAE` | integer or `"."` or `"NA"` | Participants with ≥1 AE, when reported (companion unit). |
| `WorstSeverity` | enum | `Mild` / `Moderate` / `Severe` / `None` / `NA`. Equals the max `Severity` across the article's `ae_events`; `None` when `AnyAEReported = N`; `NA` when `SafetyReported = N`. |
| `text_source` | enum | `born-digital` / `OCR` / `manual` — provenance of the extracted text (stratification variable for input-fidelity risk). |
| `Model` | text | Model name + version used for extraction. |
| `PromptVersion` | text | Pinned prompt file version. |
| `RubricVersion` | text | Pinned severity-rubric version. |
| `Temperature` | number | Sampling temperature (0 for production). |

---

## 4. `ae_events` table — one row per distinct AE

| Field | Type | Valid values / rule |
|---|---|---|
| `AE_ID` | text | Unique within article, e.g., `{StudyID}_AE01`. |
| `StudyID` | text (FK) | Must exist in `articles.StudyID`. |
| `AE_type` | enum | `AE` / `challenging_experience` / `both`. Challenging-experience phenomenology (CEQ sense) is expected and in-session — flag it, don't silently count it as a clinical AE. |
| `Description` | text | Concise free-text description of the event as reported (≤30 words). |
| `Onset` | enum | `in-session` / `post-session-acute` (hours–days) / `delayed` (weeks+) / `unknown`. Supports the PAT severity adaptation. |
| `Severity` | enum | `Mild` / `Moderate` / `Severe` — per §5. |
| `SeverityIndeterminate` | enum | `Y` / `N` — `Y` when graded on insufficient detail (defaulted per §5). Every `Y` goes to the human-review queue. |
| `SeveritySource` | enum | `author` (author assigned a CTCAE grade / SAE flag — use theirs) / `rubric` (graded via §5). |
| `InterventionRequired` | enum | `Y` / `N` / `.` — did the event require active intervention (pharmacological rescue, etc.)? |
| `MeetsFDASerious` | enum | `Y` / `N` — meets any FDA seriousness criterion (§5.2). Drives the Moderate/Severe tiebreak. |
| `Rationale` | text | Why this grade — mandatory for any non-obvious call, especially Mild-vs-Moderate and any indeterminate grade. Split into `rationale_log` at merge. |

---

## 5. Severity rubric (authoritative)

Three-level scale grounded in **CTCAE v5.0** collapsed to three bands, cross-walked with **FDA seriousness criteria**, adapted for psychedelic-assisted therapy (PAT).

**Core adaptation principle.** Intense in-session anxiety, fear, perceptual distortion, and challenging-experience phenomenology are *expected* effects of psychedelic dosing. Grade them **by consequences and intervention need, not by subjective intensity during dosing.** A high CEQ score alone → **Mild**, unless accompanied by intervention need or persistence beyond the dosing period.

**Severity source precedence.** If the authors assign a CTCAE grade or SAE flag, use it (`SeveritySource = author`). Otherwise apply this rubric (`SeveritySource = rubric`).

### 5.1 CTCAE grade → 3-band collapse (removes any grade straddling two bands)

| CTCAE v5.0 grade | Band | Rule |
|---|---|---|
| Grade 1 | **Mild** | Asymptomatic/mild; no intervention indicated. |
| Grade 2 | **Moderate** | Minimal/local/noninvasive intervention indicated, or limiting age-appropriate instrumental ADL. |
| Grade 3 | **Moderate**, unless it meets an FDA seriousness criterion → **Severe** | FDA-seriousness is the single tiebreaker between the top two bands. |
| Grade 4 | **Severe** | Life-threatening; urgent intervention indicated. |
| Grade 5 | **Severe** | Death related to AE. |
| **Any grade** meeting an FDA seriousness criterion (§5.2) | **Severe** | Seriousness overrides the grade-based band upward, never downward. |

Verify exact CTCAE v5.0 anchor wording against the current source document before this rubric enters the manuscript methods.

### 5.2 FDA seriousness criteria (an event is "serious" if it meets **any** one)

- Death
- Life-threatening event
- Inpatient hospitalization or prolongation of existing hospitalization
- Persistent or significant disability/incapacity
- Congenital anomaly/birth defect
- A medically important event requiring intervention to prevent one of the above

PAT-specific events that are `Severe` because they typically meet a seriousness criterion or are labeled SAEs: suicidal behavior/attempt, psychosis or prolonged psychotic reaction, seizure, serious cardiovascular event, hospitalization, HPPD (hallucinogen-persisting perception disorder), or any event the authors themselves label an SAE.

### 5.3 Operational band definitions (PAT context)

- **Mild** — Transient, expected, self-limiting; no or minimal intervention; resolves within/shortly after the session; no functional impairment beyond the acute dosing period. Expected acute drug effects (transient anxiety, nausea, headache, mild transient BP/HR elevation, perceptual distortion, reassurance-resolved challenging experience) default here unless they escalate.
- **Moderate** — Requires active intervention (benzodiazepine rescue, antihypertensive, antiemetic) **or** causes functional impairment persisting beyond the dosing day (persisting anxiety, low mood, sleep disturbance lasting days to a few weeks) — but meets **no** FDA seriousness criterion.
- **Severe** — CTCAE Grade 4–5, **or** any event meeting an FDA seriousness criterion, **or** any author-labeled SAE.

### 5.4 Under-specified AEs

When an AE is reported with too little detail to grade: grade on whatever intervention/outcome/seriousness signals are present. Absent any such signal, default **Mild** and set `SeverityIndeterminate = Y`. This default reflects that these are expected transient effects, but it is a judgment call with a safety-direction hazard. Therefore:
1. Flag every such grade (`SeverityIndeterminate = Y`) and route it to human review before publication.
2. Record the missing information in `Rationale`.
3. Keep the flag usable as a filter so a sensitivity analysis can recompute AE rates with indeterminate events excluded or escalated.

Never silently absorb an ungradeable event into a point estimate.

---

## 6. Response contract (for the extraction prompt)

The model returns, per article, a **single JSON object** with two halves and nothing else (no prose, no markdown fences):

```json
{
  "data": {
    "article": { "...articles-table fields for this article..." },
    "ae_events": [ { "...ae_events-table fields..." } ]
  },
  "rationale": {
    "article": { "field": "why this non-obvious call was made" },
    "ae_events": { "AE_ID": "why this severity/type/onset" }
  }
}
```

- Both halves are valid JSON — the "output only JSON" contract of the main prompt is preserved.
- The `data` half is machine-validated against §3–§4 and the §7 gate; the `rationale` half is split into `rationale_log` at merge.
- Binary/enum fields use only their listed values — never `true`/`false`/`"Y"` where an enum is specified, never free text where an enum is specified.
- If input text appears garbled or truncated (OCR failure), code affected fields not-reported (`"."`) and say so in `rationale`; do not guess.

---

## 7. Validation gate (deterministic, blocks merge on failure)

- **Type/enum check** against §3–§4.
- **Gate-consistency rules:**
  - `SafetyReported = N` ⇒ `AnyAEReported = NA`, `NumDistinctAEs = NA`, `WorstSeverity = NA`, zero `ae_events` rows.
  - `AnyAEReported = N` ⇒ `NumDistinctAEs = 0`, `WorstSeverity = None`, zero `ae_events` rows.
  - `AnyAEReported = Y` ⇒ ≥1 `ae_events` row **or** `NumDistinctAEs = "Not numbered"`.
  - `WorstSeverity` = max `Severity` across the article's `ae_events`.
  - `PctIndigenous ≤ PctBIPOC` when both are numeric.
  - Every `ae_events.StudyID` ∈ `articles.StudyID` (referential integrity).
  - Every `SeverityIndeterminate = Y` row present in the human-review queue.
- **Provenance completeness:** `Model`, `PromptVersion`, `RubricVersion`, `Temperature`, `text_source` non-empty for every article.

Failures are written to `validation_report.txt` with the offending `StudyID` and rule; nothing merges until the report is clean or the exception is documented.

**Non-blocking design warning.** `IsObservational = N` is reported in `validation_report.txt` as a warning, not a failure — it flags a likely corpus-curation mistake for human review but does not block the merge, since the row itself is still internally valid and fully extracted.

---

## 8. Cross-references

- Architecture, workflow, schema, and severity rubric: `observational_studies_system_design.md`.
- Source item list: `opus_extraction_prompt_observational.md`.
