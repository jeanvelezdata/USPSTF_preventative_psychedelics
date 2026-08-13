# System Design — Clinical-Trial Extraction

**Scope.** The 52-variable clinical-trial codebook (`archived/prompts/opus_extraction_prompt.md`) applied to the 48-PDF clinical corpus in `clinical_trials/inputs/pdfs/{alcohol,opioids,smoking}/`, producing **one master study-level table** with `Condition` as a column, plus a linked `ae_events` table. This replaces the hand-pasted, one-article-at-a-time extraction that produced `data/Alcohol_Dataset.xlsx`, `data/Smoking_Dataset.xlsx`, and `data/Opioid_Dataset.xlsx`. Those three files are **frozen, read-only** from here on and serve only as the old-pipeline reference for `archived/migration/clinical_old_new_mapping.md` (decision 5).

**Relationship to the observational dataset.** Separate and standalone. The observational AE/demographics dataset (`observational_studies/`) is not joined to this one, shares no key, and is analyzed independently. What crosses over is *architecture* — subagent isolation, manifest checkpointing, the two-part response contract, provenance archival, the deterministic merge/validate gate — and one piece of *content*: the CTCAE v5.0 → 3-band severity rubric with FDA-seriousness cross-walk (`observational_codebook.md` §5), imported verbatim so adverse events in both datasets are graded on the same scale.

**Codebook.** Field-by-field conventions live in the companion `clinical_codebook.md`. **Migration contract.** Old↔new comparability lives in `archived/migration/clinical_old_new_mapping.md`.

**Execution environment.** Claude Code on a Claude subscription with token limits (no Anthropic API key) — the same environment as the observational pipeline, and the same two consequences (`observational_studies_system_design.md`, preamble): the run must be **checkpointed** so a token-limit interruption resumes rather than restarts, and **archival artifacts must be written explicitly** because nothing in an orchestrated run archives itself. The clinical case makes both sharper: at 52 fields plus an AE array per article, a lost mid-corpus batch is roughly six times the re-work of a lost observational batch.

---

## 1. Architecture — one subagent per article, checkpointed

Each article is extracted by its own Claude Code Task-tool subagent, dispatched in batches of **4**. The subagent boundary is inherited from the observational design (§1) and is not re-argued here; what differs is the clinical case's specific contamination and error modes.

**Why isolation matters more here, not less.** The observational extraction had 8 items and one anchoring hazard (severity). This extraction has 52 fields, of which **twelve are methodological-quality judgments made relative to an implicit standard** — `BlindingYN`, `Double+Blind`, `Power`, `ConfoundYN`, `InclusionExclusionCriteria`, `ValidatedScaleMeasYN`, `MethodologyDescribedYN`, `Funding/COI YN`, `RecruitmentRepresentYN`, `PrimaryCare`, `SocioeconomicStatusYN`, `Retention (%)`. Reading a fully CONSORT-compliant 2022 RCT immediately before a 1961 open-label case series drags the older article's codes downward; the reverse order drags them up. The corpus spans 1958–2026 and the era split (Pre-1980 vs 2010+) **is the manuscript's primary comparison**, so cross-article anchoring would corrupt the exact contrast the analysis rests on. A shared-context loop is therefore not merely noisier — it is biased in the direction of the finding.

Two further clinical-specific hazards: the ten substance binaries bleed across articles in a shared context (a psilocybin study read after four LSD studies invites a spurious `LSD = 1`), and `Outcome` selection — picking *which* statistic is the study's primary result — anchors on whatever effect size was salient in the previous article.

**Multiple articles per call is rejected** for the reason the observational design gives, plus one more: a 52-field JSON object per article, packed 4-up behind delimiters, is where field-to-article misattribution starts — a value landing in the right key of the wrong article's object is silent, schema-valid, and undetectable by any gate.

**Batch size 4, not 6.** Per-call output is ~2–4 k tokens (52 fields + rationale + AE array) against the observational pipeline's ~1 k. A failed batch costs proportionally more to re-run, and 48 articles at 4-per-batch is 12 batches — still small enough that batch count is not a constraint worth optimizing.

Scale: roughly 1.5–2.5 M input + 0.15 M output tokens for the full corpus. Cost and latency are non-issues; isolation and auditability drive the design.

### 1.1 Workflow

1. **Convert (scripted, deterministic).** PDF → Markdown, with a text fallback. §1.2.
2. **Build/reconcile the manifest (scripted + one human metadata pass).** §1.3.
3. **Dispatch.** For each not-yet-done article, spawn one subagent with that article's converted text plus the pinned prompt (`clinical_trials/prompts/clinical_extraction_prompt_v1_1.md`). The subagent's **first** action is the eligibility screen (§5.1); it then extracts all 52 codebook fields, the added QC/provenance fields, and the AE array — **regardless of the eligibility verdict** (decision 9). It returns the two-part object (§2) for that one article.
4. **Checkpoint on return.** As each subagent completes, immediately write `{StudyID}_request.json`, `{StudyID}_response.json`, and mark the `StudyID` done in the manifest. An interrupted session **resumes from the manifest**, re-dispatching only unfinished articles. This same discipline is the audit trail.
5. **Merge + validate (separate, deterministic step).** Assemble `clinical_master.csv` + `ae_events.csv`, split the rationale halves into `rationale_log.md`, emit config proposals (§5.3), and run the validation gate (§8). Kept outside the subagents so it re-runs without re-extracting.
6. **Ratify config entries.** Auto-ratified and carried-forward proposals are applied to `scripts/_config_<condition>.py`; pending ones go to a human. §5.3.
7. **Rebuild figures and tables.** `run_pipeline.py`, unchanged in its per-condition structure. §6.4.
8. **Visual regression + old/new comparison.** §9. Both are gate steps, not suggestions.

Bump `PromptVersion` on any prompt change and `RubricVersion` on any rubric change, so archived responses stay traceable to what produced them; a revision means re-running the affected articles (cheap at this scale).

### 1.2 Conversion — PDF → Markdown, text fallback (decision 8)

**Tool.** `pymupdf4llm.to_markdown()`. Chosen because it sits on PyMuPDF, already the pipeline's PDF engine (`observational_studies/scripts/preprocess_pdfs.py`), so the Markdown tier, the plain-text fallback, and the OCR page rasterizer are one library family with one failure surface. It is a new dependency (`pymupdf4llm`) to be added to `requirements.txt` and pinned in `requirements-lock.txt`.

**Why Markdown, for this codebook specifically.** Plain-text extraction destroys exactly the two structures this codebook depends on:

- **Headings locate the fields.** Eight of `MethodologyDescribedYN`'s fourteen criteria (§5.2) are "does the article have a section stating X" judgments — objective, design, setting, eligibility, outcomes, statistical methods, harms, funding/COI. `HarmsAssessed` and the entire `SafetyReported` gate turn on whether an "Adverse Events" / "Safety" / "Side effects" section exists at all; that is the difference between a real "no AEs occurred" and "the authors never looked." `Funding/COI YN` lives in back matter that plain-text extraction merges into the references. With headings preserved, these are locatable; without them, they are guessed.
- **Table markup keeps numbers attached to their labels.** `Outcome`, `SD`, `PVal`, `SampleSize_NFinal`, `Retention (%)`, `PercentFem`, and `RaceEthnicity_BIPOCPercent` are read out of results and baseline-characteristics tables. When a two-column PDF table collapses into whitespace-mangled prose, a number silently re-associates with the wrong row or the wrong arm. Those first four fields position the forest-plot marker (§6.3), so a table-collapse error is not a missing value — it is a *wrong* value that renders as a confident point estimate.

**Fallback chain, per article.**

| Step | Action | Recorded as |
|---|---|---|
| 1 | `pymupdf4llm.to_markdown(pdf)` → `inputs/text/{StudyID}.md` | `text_source = born-digital`, `text_format = markdown` |
| 2 | Markdown fails the fidelity check → PyMuPDF `page.get_text("text")` → `{StudyID}.txt` | `text_source = born-digital`, `text_format = text` |
| 3 | Plain text yields < 200 stripped chars (image-only PDF) → Tesseract at 300 dpi → `{StudyID}.txt` | `text_source = OCR`, `text_format = text` |
| 4 | OCR also yields < 200 chars | left unprocessed, `done = N`, flagged for manual transcription |

`text_source` keeps its observational value domain (`born-digital` / `OCR` / `manual`). `text_format` (`markdown` / `text`) is added alongside it rather than folded into it, because engine and format are orthogonal — an OCR'd article is always `text_format = text`, but a born-digital one may be either. Both are provenance fields on every row (§8).

**Per-article fidelity check** (deterministic, run at conversion; failing any one check demotes the article to plain text and records the failing check in the manifest's `fidelity_note`):

1. **No text loss.** `len(md.strip()) / len(txt.strip()) ≥ 0.90`. Markdown conversion must not drop content.
2. **No runaway.** `len(md.strip()) / len(txt.strip()) ≤ 1.6`. Guards against figure/image placeholder spam inflating the file without adding readable content.
3. **Structure actually recovered.** At least one ATX heading (`^#{1,6}\s`) in the Markdown. A conversion that produced no headings has bought nothing over plain text and costs tokens.
4. **Tables survived.** If `page.find_tables()` detects ≥ 1 table anywhere in the PDF, the Markdown must contain ≥ 1 pipe-table row (`^\s*\|`). A detected table that did not become pipe markup collapsed, which is the failure mode Markdown was adopted to prevent.

Checks 1–2 are cheap guards; 3–4 are the ones that matter. An article that fails 4 but passes 3 is worse than plain text for the four Tier-1 fields specifically, because it *looks* structured — hence demotion rather than partial acceptance.

### 1.3 Corpus reconciliation and the manifest

48 PDFs (alcohol 37, opioids 7, smoking 4) against 44 frozen rows (33 / 7 / 4). Opioid and smoking match exactly; the entire gap is alcohol, where four PDFs were dropped during the hand extraction. Those four are in scope now and are converted, screened, extracted, and coded like everything else.

**Manifest schema** — `clinical_trials/inputs/manifest.csv`, one row per PDF:

| Column | Source | Notes |
|---|---|---|
| `StudyID` | derived | `"{Surname} {Year}"`, from the human metadata pass. Primary key. |
| `Condition` | folder | `alcohol`→`Alcohol`, `opioids`→`Opioid`, `smoking`→`Smoking`. The folder is plural; the canonical label is singular. |
| `pdf_path` | scan | Path relative to `inputs/pdfs/`, including the condition subfolder. |
| `citation` | **human** | Full citation, **beginning with the first author's surname token**. See "Identity" below. |
| `surname` | derived | `_lib.first_author_surname(citation)`. Frozen at manifest build; the config-lookup key. |
| `year` | **human** | Four-digit publication year. The other half of the config-lookup key. |
| `old_row_match` | derived | `(surname, year)` tuple found in a frozen `data/<Condition>_Dataset.xlsx`, or `NEW`. |
| `text_source` | conversion | `born-digital` / `OCR` / `manual`. |
| `text_format` | conversion | `markdown` / `text`. |
| `fidelity_note` | conversion | Which fidelity check failed, if any; blank on a clean Markdown pass. |
| `done` | dispatch | `Y` / `N`. Resume key. |

**Why `citation` and `year` are a human pass.** PDF filenames in this corpus are not citations (`1-s2.0-S037687162200093X-main (1).pdf`, `115d425e-5129-48c5-8c21-e1af10229ed5 (1).pdf`), and the observational pipeline already established that these are "not derivable from the PDF alone" and left for a metadata-backfill step (`preprocess_pdfs.py` docstring). It is 48 rows of hand metadata, once, and it is what makes the automatic old↔new join possible.

**Matching, and which direction blocks.**

| Condition | Disposition | Reason |
|---|---|---|
| PDF present with no manifest row | **BLOCK** | An unconverted article silently absent from the dataset. |
| Manifest row with no PDF | **BLOCK** | Dangling reference; the extraction has nothing to read. |
| Manifest row whose `(surname, year)` matches no frozen old row | **WARN**, listed by `StudyID` | Expected for the four previously dropped alcohol studies; the corpus is a superset by design. |
| Frozen old row matching no manifest row | **BLOCK** | Data loss: a study that was in the evidence base has vanished. Overridable only by a human-authored `expected_missing.csv` entry giving a reason. |
| Duplicate `(surname, year)` across manifest rows | **BLOCK** | The config dicts are keyed on this tuple and cannot disambiguate. See "Identity". |

The reconciliation report — matched, new, missing, per condition — is written to `archived/migration/reconciliation_report.txt` and is the input to `archived/migration/clinical_old_new_mapping.md`.

**Identity** (constraint 2). `StudyID = f"{first_author_surname(Citation/Title)} {Year}"`, and `(surname, Year)` remains the lookup key into `scripts/_config_<condition>.py`. `first_author_surname()` splits `Citation/Title` on the first `,` or `;` and normalizes curly apostrophes and non-breaking hyphens, so the extracted citation **must begin with the first author's surname token**. Three consequences the design must handle:

- The surname token is **frozen in the manifest**, not re-derived from the model's output. The subagent extracts `Citation/Title` from the article (per the PI's instruction), and the gate asserts `first_author_surname(model_citation) == manifest.surname`. A mismatch is a **blocking** failure printing both tokens. This matters concretely: `_config_smoking.py` keys one study `('Johnson MW', 2026)` and another `('Johnson', 2016)` — the initials are part of the key, so a citation rendered `"Johnson, M. W., …"` instead of `"Johnson MW, …"` would silently key to `('Johnson', 2026)` and miss.
- A `StudyID` collision (same surname, same year) may be disambiguated with a suffix — `Surname Year b` — **in `StudyID` only**. The config key is the `(surname, Year)` tuple and cannot carry the suffix, so a genuine same-surname-same-year pair is a **blocking** gate failure requiring a human to decide how to key it. No such pair exists in the current corpus (`Sessa 2019`/`2021`, `Pagni 2024`/`2025`, `Jensen 1963`/`2024`, `Bogenschutz 2015`/`2022` all differ by year), but the expanded corpus may introduce one.
- `Year` disagreements between the manifest and the model (online-first vs issue year) break the tuple. The gate matches surname first, then year within ±1, and reports the pair as a **near-miss requiring human confirmation** — never auto-merged.

### 1.4 Provenance and reproducibility

Archive, per article: the pinned prompt + rubric version, the exact converted text seen (path + SHA-256), the model's rationale, model name/version and parameters (temperature 0), and the raw response. Step 4 of §1.1 produces all of these.

Two honest caveats for the methods appendix:

1. **Determinism.** Even at temperature 0, LLM output is not guaranteed bit-identical across runs or model minor-versions. The defensible claim is *"every request and response is archived verbatim"* (provenance), not *"re-running reproduces identical codes"* (determinism). Inherited from `observational_studies_system_design.md` §1.2.
2. **The frozen rows have no provenance.** `data/<Condition>_Dataset.xlsx` was produced by pasting `archived/prompts/opus_extraction_prompt.md` into a chat one article at a time. There is no archived request, no archived response, no recorded model version, no recorded date, no pinned prompt version. Nothing can be reconstructed about how any individual old value was produced. Therefore: **the provenance claim attaches to the new master table only.** The frozen files must be described in the manuscript as a historical hand extraction retained for migration comparison, never as part of the provenance chain. `archived/migration/clinical_old_new_mapping.md` is what converts "we redid it" into evidence that redoing it did not change the evidence — which is the only rigorous role the old files can play.

---

## 2. Response contract — two-part object

Each subagent returns a **single JSON object** with two halves and nothing else (no prose, no markdown fences):

```json
{
  "data": {
    "article": { "…54 study-level fields…" },
    "ae_events": [ { "…one object per distinct AE…" } ]
  },
  "rationale": {
    "article": { "FieldName": "why this non-obvious call was made" },
    "ae_events": { "AE_ID": "why this severity / type / onset" },
    "config_proposal": { "…proposed _config_<condition>.py entries…" }
  }
}
```

Adapted from the observational contract (`observational_codebook.md` §6) in three ways:

- **`data.article` is the flat clinical row**, not the narrow observational one: all 52 codebook variables under their exact existing names — including the misspelling `Clincial Trial YN` and the punctuation in `Funding/COI YN`, `Citation/Title`, `Retention (%)`, `Followup in months`, `Implementation Outcome` (decision 2) — plus the added eligibility, AE-gate, and provenance fields.
- **`rationale.config_proposal`** is a third rationale key with no counterpart in the observational contract. It carries the model's proposed `EFFECT_SIZE_EXTRACTIONS` / `CONVERSION_RULES` / `TIER2_RATINGS` entries. It **never enters `data`** and is applied only through the ratification rule in §5.3.
- **`rationale.article.MethodologyDescribedYN` is a structured object, not free text** (§5.2).

`data` is machine-validated against `clinical_codebook.md` §4–§5 and the §8 gate. The `rationale` half is split at merge into `rationale_log.md`.

---

## 3. Severity rubric

Imported unchanged from the observational pipeline: a fixed three-level scale grounded in **CTCAE v5.0** collapsed to three bands, cross-walked with **FDA seriousness criteria**, adapted so that expected, protocol-anticipated transient effects of psychedelic dosing do not automatically inflate severity. Core adaptation principle, the Grade-3 tiebreak, severity-source precedence, and the under-specified-AE default are as stated in `observational_studies_system_design.md` §3 and are not re-argued. The authoritative, implementation-ready version is reproduced in `clinical_codebook.md` §6; `RubricVersion = v1` denotes the same rubric text in both pipelines, and a divergence requires bumping one of them.

**Where the clinical context differs.** Trial protocols carry author-assigned CTCAE grades and explicit SAE flags far more often than naturalistic reports do, so `SeveritySource = author` will be the common case in the 2010+ stratum and near-absent in the pre-1980 one — CTCAE and its NCI predecessors postdate that literature entirely. Two consequences, both encoded as gate rules in §8: a pre-1980 article claiming an author-assigned *CTCAE grade* is a warning (the authors cannot have used a scale that did not exist; they may still have used their own severity language, which is a legitimate `author` source), and `SeverityIndeterminate = Y` should be expected to concentrate in the pre-1980 stratum, where harms are described narratively. The era stratification therefore applies to the AE data as much as to the methodological-quality data, and any AE-rate comparison across eras must stratify on `SeveritySource` and `SeverityIndeterminate`.

---

## 4. Adverse-event data model

Structure imported from `observational_studies_system_design.md` §4 (decision 6): **AE-level long format**, one row per distinct AE with its own severity, plus an article-level `WorstSeverity` rollup; the **three-state AE presence** distinction (real 0 / reported-but-not-counted / article silent) preserved through the `SafetyReported` gate; `AE_type` flagging AE vs. challenging experience; **distinct AE types** as the primary counting unit with participants-affected as a companion; `AE_denominator` and `ArmScope` so a per-study AE rate is defensible.

Two clinical-specific points:

**`HarmsAssessed` and `SafetyReported` both exist, and the gate makes that safe.** `HarmsAssessed` is preserved verbatim as a numeric binary (decision 2) because it is load-bearing for `_lib.BINARY_COLS`, `recode_binary()`, Table 2, and Table 3 in `descriptive_analyses.py`. `SafetyReported` is added as a `Y`/`N` enum (decision 6) because every imported AE gate-consistency rule is written against it. Collapsing either one breaks the other's consumers, so both are stored and a blocking consistency rule keeps them from drifting:

> `SafetyReported = "Y"` ⟺ `HarmsAssessed = 1`. `SafetyReported = "N"` ⟺ `HarmsAssessed ∈ {0, 3, "."}`.

The redundancy is deliberate and documented rather than accidental.

**Per-AE participant counts are added.** Trial AE tables routinely report "headache: 12/25", which the observational corpus rarely did. `ae_events.NAffected` (integer / `"."`) captures it. Without it, the distinct-type count and the article-level `NParticipantsWithAE` cannot be reconciled to the per-event detail that trials actually publish.

---

## 5. Eligibility screening, the composite checklist, and the Tier-1 fields

These three are the clinical pipeline's adapted items — the counterpart to `observational_studies_system_design.md` §5.

### 5.1 Eligibility screening (decision 9)

**Two criteria, both required:** (a) the article reports a **clinical trial**; (b) it reports an **outcome related to substance use disorder**. This replaces the observational pipeline's `IsObservational` corpus-curation check — criterion (a) *is* the design check, inverted.

**Where it runs: the opening step of the extraction subagent, not a separate pass.** Justification on context-isolation grounds: the evidence supporting both criteria — the Methods design statement, the outcome list — is the same text the extraction reads immediately afterward, so a separate pass pays the article's full context cost twice and produces a second archival artifact whose verdict can drift from the extraction that follows it. Keeping the screen inside the subagent means one context, one archived request/response, one internally consistent row. This mirrors the observational design's placement of `IsObservational` (§1.1 step 2). It differs in stakes: `IsObservational` was pure corpus curation, whereas criterion (b) is an inclusion criterion for the evidence base and the verdict gates the analytic outputs — hence the mandatory note and the documented downstream filter below.

**Fields** (specified in `clinical_codebook.md` §4.2):

| Field | Type | Domain |
|---|---|---|
| `EligibleYN` | enum | `Y` / `N` |
| `EligibilityFailedCriterion` | enum | `not_clinical_trial` / `no_sud_outcome` / `both` / `NA` (`NA` iff `EligibleYN = Y`) |
| `EligibilityNote` | text | Free text naming which criterion failed and why. **Mandatory** whenever `EligibleYN = N`; `"NA"` when `Y`. |

**Relation to `Clincial Trial YN`.** That variable is the model's coding of the article's design; criterion (a) is the eligibility judgment built on it. They must not contradict each other, and a disagreement is a signal worth surfacing rather than averaging over:

| Situation | Disposition |
|---|---|
| `Clincial Trial YN = 1` and `EligibilityFailedCriterion ∈ {not_clinical_trial, both}` | **BLOCK** — direct self-contradiction within one row |
| `Clincial Trial YN = 0` and `EligibilityFailedCriterion ∈ {NA, no_sud_outcome}` | **BLOCK** — same contradiction, other direction |
| `Clincial Trial YN ∈ {3, "."}` with criterion (a) passing | **WARN** — design undeterminable yet the screen reached a verdict; a human reads the note |
| `EligibleYN = N` with empty / `"."` / `"NA"` `EligibilityNote` | **BLOCK** — decision 9 makes the note mandatory |
| `EligibleYN = N` at all | **WARN**, listed by `StudyID` with the note quoted |

**Nothing is dropped at ingestion.** Ineligible articles are fully extracted, coded, and retained in the master table with the flag and note attached — the "extract every field regardless, flag for human review" discipline the observational pipeline applies to `IsObservational = N`.

**Ineligible studies are excluded from the analytic figures and tables, through exactly one filter.** The manuscript's claim is about the clinical-trial evidence base for SUD outcomes; a non-trial or a trial with no SUD outcome on the forest plot misrepresents that base, and a study with no SUD outcome has no effect size for `EFFECT_SIZE_EXTRACTIONS` to key on in the first place. The filter is a single function, `_lib.analytic_frame(df)`, applied **once** in `clean_dataset.py` immediately after loading the master and **before** `extract_effect_size_fields()` — so ineligible studies never reach the config-key lookup and cannot raise a spurious `KeyError`. Because `data/<Condition>_Dataset_Cleaned.xlsx` is the sole input to all four downstream scripts, filtering there covers every figure and table with no logic scattered anywhere else. A reviewer flips one module-level constant, `_lib.INCLUDE_INELIGIBLE = True`, and reruns `run_pipeline.py` to see the alternative.

### 5.2 `MethodologyDescribedYN`'s 14-criterion checklist

The binary stays in `data`, unchanged, because `BINARY_COLS`, Table 2, and Table 3 consume it. The per-criterion detail goes in the `rationale` half as a **structured object with fourteen fixed keys**:

```json
"MethodologyDescribedYN": {
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

Gate: `n_met` must equal the count of `"Y"` values, and `MethodologyDescribedYN = 1` iff `n_met ≥ 13`. Both are blocking — they are arithmetic, not judgment.

**What it buys.** (1) A reviewer can see *which* criterion failed instead of a bare `0`, which is the difference between an auditable composite and an unauditable one. (2) A per-criterion secondary analysis — "which CONSORT-style elements are missing from the pre-1980 literature" — becomes available without re-extracting. (3) A cross-field consistency check: criteria `harms`, `funding_coi`, and `comparator` ask about the same underlying facts as `HarmsAssessed`, `Funding/COI YN`, and `Comparator`. Only the contradictory direction is checked, and only as a **warning**: criterion `harms = N` while `HarmsAssessed = 1` cannot both be true. The reverse is legitimate and is *not* flagged — the checklist asks whether an element was *described*, and "no blinding was used" describes blinding while `BlindingYN = 0`. Conflating those two questions would produce false failures on exactly the well-reported studies.

### 5.3 The Tier-1 effect-size fields and who authors the config entries

**`Outcome`, `SD`, `PVal`, and `SampleSize_NFinal` warrant stricter rules than the rest of the codebook** (constraint 3) because they alone determine forest-plot position: `Outcome` drives `metric`/`measure` via `EFFECT_SIZE_EXTRACTIONS`, `measure` and `SampleSize_NFinal` are the two arguments to `_lib.compute()`, and `SampleSize_NFinal` additionally sets marker size through `variance_g()` and CI width through `se_g`. An error in any of them renders as a confident, correctly-styled marker in the wrong place. Concretely, the codebook (`clinical_codebook.md` §4.3) tightens them as follows: `Outcome` is the effect size for the study's **stated primary outcome**, not the largest reported one; `SD` must carry **degrees of freedom in parentheses** for any statistic that has them, because `convert_to_d()` requires `df_error` for `F` and 1 df for `chi2`; `PVal` is never converted from `"NS"` to a number; and `SampleSize_NFinal` must be the denominator of the analysis `Outcome` came from, including when that is a subgroup. **A `rationale.article` entry is mandatory for all four fields on every article**, not only when the call is non-obvious — the only fields in the codebook with that requirement.

**Config authorship.** These are hand-coded methodological judgments about effect-size conversion. The model proposes them in `rationale.config_proposal`; the merge step partitions the proposals into three dispositions and writes them to `clinical_trials/outputs/config_proposals/<condition>.py`, each entry annotated:

| Disposition | Rule | Human sign-off |
|---|---|---|
| **Auto-ratified** | Proposed `confidence = clean` | No |
| **Carried forward** | The study has an entry in the frozen `scripts/_config_<condition>.py` **and** the proposal's `method` and `confidence` both match it. The old entry's `note` and `direction` are kept verbatim — the existing hand-written text is the authority. | No |
| **Pending** | Everything else: `approx` or `excluded` proposals for studies with no frozen entry (the four new alcohol studies, by construction), or any proposal whose `method` or `confidence` diverges from the frozen entry. Divergences are emitted as an old-vs-proposed diff. | **Yes** |

`apply_config_proposals.py` merges the first two categories into `scripts/_config_<condition>.py` and leaves pending ones out; the gate then blocks the rebuild while any *eligible* study lacks a ratified entry, reporting them as a **named list of `(surname, year)` tuples** rather than the bare `KeyError` that `extract_effect_size_fields()` raises today.

**The auto-apply hazard, stated plainly.** A model-declared `clean` that is wrong — calling a within-subjects `t` a between-groups conversion, say — reaches the forest plot without human review. Three mitigations, all in the gate: `confidence = clean` is accepted only for the seven methods `_lib.convert_to_d()` implements (`d`, `g`, `eta_p`, `F`, `chi2`, `OR`, `RR`) and is rejected on any other method string; `method = "F"` without a numeric `df_error` is rejected; and every auto-ratified entry is listed in `validation_report.txt` and `rationale_log.md`, so the residue is visible after the fact even though it did not block. The residual risk — a plausible-but-wrong `clean` on a supported method — is real and is the price of the throughput; the old/new comparison's Tier-1 standard (`archived/migration/clinical_old_new_mapping.md` §5) is the backstop for the 44 studies that have an old counterpart, and the four new studies have none.

---

## 6. Output schema, file layout, and the plot-frame adapter

### 6.1 Schema

**Two linked tables plus logs.** Field-level types and valid values are in `clinical_codebook.md`; this is the structural summary.

**`clinical_master` (one row per article).** The 56 frozen columns minus two, plus added fields.

*Dropped (2):* `url or link to pdf` and `Study Design Type`, per the PI's instruction that both are unnecessary. Supporting evidence for the latter: it holds the constant value `"Clinical Trial"` in **all 44** frozen rows across all three files, so it carries zero information. Consequences are enumerated in §9 and in `archived/migration/clinical_old_new_mapping.md` §2.

*Carried verbatim (54):* `Citation/Title`, `Condition`, and the 52 codebook variables under their exact existing names, including `Clincial Trial YN`, `Funding/COI YN`, `Retention (%)`, `Followup in months`, `Implementation Outcome`, `Double+Blind`, `Pos Result Y/N`. The Smoking file's legacy `Retention` / `StudyDesignType` spellings disappear with the merge to one table (decision 2). `Condition` is canonicalized to `Alcohol` / `Smoking` / `Opioid` — note that the frozen Opioid file stores `"Opioids"` (plural), which is a **value** normalization, not a column rename, and is recorded as such in the migration document.

*Added (18):* `StudyID`; `EligibleYN`, `EligibilityFailedCriterion`, `EligibilityNote`; `SafetyReported`, `AnyAEReported`, `NumDistinctAEs`, `NParticipantsWithAE`, `AE_denominator`, `ArmScope`, `WorstSeverity`; `text_source`, `text_format`; `Model`, `PromptVersion`, `RubricVersion`, `Temperature`; `SourcePDF`. The seven AE-gate fields are imported as a block rather than cherry-picked: importing the severity rubric without its gate fields leaves the `ae_events` table uninterpretable — no denominator, no arm scope, no way to distinguish a real zero from silence.

**`ae_events` (one row per distinct AE):** `AE_ID`, `StudyID` (FK), `AE_type`, `Description`, `NAffected`, `Onset`, `Severity`, `SeverityIndeterminate`, `SeveritySource`, `InterventionRequired`, `MeetsFDASerious`.

### 6.2 File layout

```
clinical_trials/
  prompts/
    clinical_extraction_prompt_v1_1.md      # pinned, versioned; embeds codebook + rubric
    severity_rubric_v1.md                 # identical text to observational v1
  inputs/
    pdfs/{alcohol,opioids,smoking}/       # 37 + 7 + 4 = 48 source PDFs (existing)
    text/{StudyID}.md | {StudyID}.txt     # converted, one per article
    manifest.csv                          # §1.3 schema
    expected_missing.csv                  # human-authored overrides for the block rule
  raw_responses/
    {StudyID}_request.json                # immutable archival artifacts
    {StudyID}_response.json
  outputs/
    clinical_master.csv                   # SOURCE OF TRUTH, one row per article
    clinical_master.xlsx                  # human-readable export, identical content
    ae_events.csv
    rationale_log.md
    human_review_queue.csv                # SeverityIndeterminate=Y + ineligible + pending config
    config_proposals/{alcohol,smoking,opioid}.py
    validation_report.txt
    rebuild_gate_report.txt
```

`reconciliation_report.txt` and the `baselines/` snapshot were part of the one-time
migration and now live under `archived/` — see §9.

**CSV as the source of truth, XLSX as an export.** CSV diffs in git, survives round-tripping without Excel's silent type coercion, and makes the old/new comparison a text diff where possible. The frozen old files stay `.xlsx` because they are frozen. Nothing in `data/` is written by the extraction layer; `data/` continues to hold the frozen inputs and the `*_Cleaned.xlsx` outputs at their existing paths (decision 7).

### 6.3 The adapter — this is the pipeline's output contract

**The plot scripts consume one narrow frame, and that frame is the contract.** One row per study:

| Column | Meaning |
|---|---|
| `study` | Display label, `"Surname Year"` |
| `Year` | Publication year (secondary sort key within substance) |
| `N` | Sample size, printed in the row label |
| `substance` | One of the `SUBSTANCE_COLORS` / `SUBSTANCE_ORDER_UNIFIED` keys — drives color, grouping, legend |
| `metric`, `measure`, `method`, `note` | Effect-size provenance, carried into the results table |
| `confidence` | `clean` / `approx` / `excluded` — drives filled vs. hollow markers and the `*` / `†` tag |
| `d`, `g`, `var_g`, `se_g`, `ci_lo`, `ci_hi` | Point estimate, inverse-variance marker size, CI whiskers, printed stats |

Tier 2 adds `category` (as `tier2_category`) and `computed_or` on the same frame. **`excluded` rows and rows with null `g` must still be produced** — `_build_layout()` filters them out for the plot, and the results tables keep them for traceability.

**Which module owns the mapping: `scripts/_lib.py`, via the existing pair `clean()` → `build_results()`.** Neither is rewritten. The master schema's job is to satisfy exactly what they already read:

- `clean()` reads `Citation/Title`, `Year`, `Outcome`, every name in `BINARY_COLS`, every name in `NUMERIC_COLS`, `Country_USvsNonUS`, `Age_Median`, `BaseStatus`.
- `build_results()` reads `Citation/Title`, `Year`, `SampleSize_NFinal`, `metric`, `measure`, and every name in `SUBSTANCE_COLS` (through `primary_substance()`).

Carrying the 54 columns verbatim satisfies both. Two notes: the `Retention` → `Retention (%)` and `StudyDesignType` → `Study Design Type` rename branches at the top of `clean()` become dead code once the master emits canonical spellings and `Study Design Type` is gone — they are flagged here as dead, not deleted. And `_lib.analytic_frame()` (§5.1) is a new function in the same module, applied by `clean_dataset.py` before `clean()`'s effect-size step.

**No rendering code is changed to satisfy this contract.** The one rendering change proposed anywhere in this design is `methqual_bar_plot.py` (§6.4), and it is a data-source change, not a styling one.

### 6.4 Master-table plumbing (problem 4)

All five entry points keep their `--condition` flag and their current output paths. The change is one line of input handling each.

| Script | Change | Output path |
|---|---|---|
| `clean_dataset.py` | `cfg.INPUT_FILE` becomes `clinical_trials/outputs/clinical_master.csv`; after load, filter `df[df['Condition'] == cfg.CONDITION_LABEL]`, then apply `_lib.analytic_frame()`, then `_lib.clean()` as today | `data/<Condition>_Dataset_Cleaned.xlsx` — **unchanged** |
| `tier1_hedges_g.py` | None. Reads the cleaned per-condition file | `tables/<C>_Tier1_HedgesG.xlsx`, `figures/<C>_Tier1_ForestPlot.png` — **unchanged** |
| `tier2_qualitative.py` | None | `tables/<C>_Tier2_Qualitative.xlsx`, `figures/<C>_Tier2_CatPlot.png` — **unchanged** |
| `descriptive_analyses.py` | None. Reads the cleaned per-condition file | `tables/<C>_Descriptive_Analyses.docx` — **unchanged** |
| `unified_forest_plot.py`, `unified_cat_plot.py` | None. Both load the per-condition cleaned files | `figures/Unified_*.png` — **unchanged** |
| `run_pipeline.py` | Add a preceding master-freshness check (fail fast if `clinical_master.csv` is missing or the gate last failed); add `methqual_bar_plot.py` to the per-condition sequence | — |
| `methqual_bar_plot.py` | **Rendering change.** Its `PRE1980` / `POST2010` percentages are hardcoded literal arrays copied out of Table 2, and the script is not wired into `run_pipeline.py`, so re-extraction would silently leave `figures/Alcohol_MethQual_BarPlot.png` displaying stale numbers. Replace the two arrays with the same `methodology_value()` computation Table 2 performs on the cleaned frame. **Visual property affected: bar heights only** — no change to geometry, colors, fonts, ordering, labels, legend, or axis. Unavoidable because the alternative is a published figure that contradicts the table beside it. | `figures/Alcohol_MethQual_BarPlot.png` — **unchanged** |

`CONDITION_LABEL` (`Alcohol` / `Smoking` / `Opioid`) is added to each `_config_<condition>.py` alongside the existing `CONDITION_NAME`.

**Substances outside the existing set** (constraint 1). The nine keys `Psilocybin`, `LSD`, `Mescaline`, `Ayahuasca`, `Ibogaine`, `OtherPsychedelic`, `MDMA`, `Ketamine`, `Cannabis` and `primary_substance()`'s precedence order are unchanged. A new substance in the expanded corpus routes to `OtherPsychedelic = 1` by default — that is what the column is for. Promoting one to its own key is a human decision touching seven places: the extraction schema, `_lib.BINARY_COLS`, `_lib.SUBSTANCE_COLS` (position sets `primary_substance()` precedence), `_lib._SUBSTANCE_CLASS_MAP`, `_lib.SUBSTANCE_COLORS`, `unified_forest_plot.py`'s `SUBSTANCE_ORDER_UNIFIED` / `SUBSTANCE_DISPLAY` / `SUBSTANCE_COLORS`, and a `Substance Category` row in `descriptive_analyses.py`'s `USPSTF_INDICATORS`. Until all seven are done the label renders in fallback grey `#444` at the bottom of the ordering. Because it introduces a new color and a new plot group, promoting a substance **is** a styling change and must go through the §9 visual-regression gate as a declared, human-authorized difference.

---

## 7. Input-fidelity handling

The corpus spans 1958–2026; thirteen of the alcohol studies are pre-1980 scanned PDFs requiring OCR, and two-column layouts and embedded tables extract poorly even for modern PDFs. Handling is inherited from `observational_studies_system_design.md` §7 — verify extracted text against the source PDF for the oldest articles, instruct the model to flag garbled or truncated input in its rationale and code affected fields not-reported rather than guess, record `text_source` (and here `text_format`) per article so downstream analysis can stratify on extraction quality.

**The anti-fabrication rule carries over verbatim and applies with extra weight here.** Ligature and punctuation artifacts (a broken font encoding rendering "fi" as "\_") are fine to read through when the intended word is unambiguous. But if a **number** looks wrong, is internally inconsistent with another number in the same article, or the model finds itself inferring a substitution rule to make two figures agree — stop. Report the number exactly as printed, or code it not-reported, and flag the inconsistency in `rationale`. **Never construct a decoding theory for garbled or internally inconsistent numbers.** A fabricated decode is worse than an honest "not reported."

Where the observational pipeline weighted this toward AE counts and descriptions, the clinical pipeline weights it toward **`Outcome`, `SD`, `PVal`, and `SampleSize_NFinal`**, for the reason in §5.3: those four are the only fields whose corruption renders as a plausible, correctly-styled marker rather than as a visible gap. A garbled Tier-1 field is coded `"."`, which routes the study to `confidence = excluded` and Tier 2 — a visible downgrade — rather than to a wrong point estimate.

---

## 8. Validation gate

A deterministic post-step (`clinical_trials/scripts/merge_validate.py`, mirroring `observational_studies/scripts/merge_validate.py`). **Blocking failures prevent any output table from being written** — only `validation_report.txt` is produced, so a partially-invalid dataset is never silently published. Warnings are written to the report and do not block.

**Blocking**

| # | Check |
|---|---|
| 1 | **Type/enum** per field against `clinical_codebook.md` §4–§5. Binaries are numeric `1`/`0`/`3`/`"."`; QC/provenance enums are `Y`/`N`-style strings. No `true`/`false`, no free text where an enum is specified. |
| 2 | **Column set** exactly matches the 54 carried + 18 added names, spelled verbatim including `Clincial Trial YN`. |
| 3 | **Eligibility consistency** — the four blocking rows of the §5.1 table, including the mandatory `EligibilityNote`. |
| 4 | **Harms/safety consistency** — `SafetyReported = Y` ⟺ `HarmsAssessed = 1` (§4). |
| 5 | **AE gate consistency** — imported unchanged from `observational_codebook.md` §7: `SafetyReported = N` ⇒ AE fields `NA` and zero `ae_events` rows; `AnyAEReported = N` ⇒ `NumDistinctAEs = 0`, `WorstSeverity = None`, zero rows; `AnyAEReported = Y` ⇒ ≥1 row or `NumDistinctAEs = "Not numbered"`; `WorstSeverity` = max `Severity`; referential integrity of `ae_events.StudyID`; every `SeverityIndeterminate = Y` present in the human-review queue. |
| 6 | **Checklist arithmetic** — `n_met` equals the count of `"Y"` in the 14 criteria, and `MethodologyDescribedYN = 1` iff `n_met ≥ 13` (§5.2). |
| 7 | **Provenance completeness** — `Model`, `PromptVersion`, `RubricVersion`, `Temperature`, `text_source`, `text_format`, `SourcePDF` non-empty on every row. |
| 8 | **Text-conversion provenance** — every `StudyID` has a converted file at the extension implied by `text_format`, and its SHA-256 matches the one archived in `{StudyID}_request.json`. |
| 9 | **Identity** — `first_author_surname(Citation/Title)` equals the frozen manifest `surname`; `(surname, Year)` is unique across the master (§1.3). |
| 10 | **Corpus reconciliation** — the three blocking directions in §1.3. |
| 11 | **Config-key existence** — every *eligible* study has entries in `EFFECT_SIZE_EXTRACTIONS` and `CONVERSION_RULES`, and every Tier-1-excluded eligible study has a `TIER2_RATINGS` entry. Reported as a named list of `(surname, year)` tuples, never as a bare `KeyError`. |
| 12 | **Config proposal discipline** — `confidence = clean` only on the seven methods `convert_to_d()` supports; `method = "F"` requires numeric `df_error` (§5.3). |
| 13 | **Plot-frame conformance** — `build_results()` on each condition's cleaned frame yields exactly the §6.3 columns; `confidence ∈ {clean, approx, excluded}`; `substance ∈ SUBSTANCE_COLS ∪ {"Unknown"}`; `study` matches `^.+ \d{4}$`; `excluded` and null-`g` rows are present rather than dropped. |
| 14 | **Visual regression** — every difference between a rebuilt artifact and its baseline is attributable to a changed study row (§9). |

**Warning (non-blocking, listed in the report for human review)**

- `EligibleYN = N` on any article, with the note quoted.
- `Clincial Trial YN ∈ {3, "."}` while criterion (a) passed.
- Checklist-vs-binary contradictions in the checked direction only (§5.2).
- `text_format = text` (Markdown fidelity check failed) or `text_source = OCR`, with the failing check named.
- A pre-1980 article claiming `SeveritySource = author` on the basis of a CTCAE grade (§3).
- Any study whose config entry was **auto-ratified** rather than human-ratified (§5.3).
- Manifest rows with no frozen old counterpart — expected for the four new alcohol studies.
- A `substance` value falling outside `SUBSTANCE_ORDER_UNIFIED` and therefore rendering in fallback grey.

---

## 9. Rebuild, visual regression, and the old/new comparison

> **Status: executed and closed.** This section documents the one-time transition from the
> frozen hand extraction to the automated master. It ran, it passed, and its scripts,
> baseline snapshot, and reports now live in [archived/migration/](archived/migration/)
> and [archived/baselines/](archived/baselines/) — the paths below are as they were at the
> time, not as they are now. Nothing here is part of the routine rebuild; `run_pipeline.py`
> does not call it. It is retained as the record of how the redesign was shown not to have
> changed the evidence base.

### 9.1 Baseline capture — a gate step, before any re-extraction

Copy the currently committed artifacts into `clinical_trials/baselines/`, recording the source commit SHA in `baselines/BASELINE.txt`: nine PNGs (`Alcohol_MethQual_BarPlot`, three `*_Tier1_ForestPlot`, three `*_Tier2_CatPlot`, `Unified_Tier1_ForestPlot`, `Unified_Tier2_CatPlot`), four DOCX (three `*_Descriptive_Analyses`, `Aggregate Data`), and six XLSX (three `*_Tier1_HedgesG`, three `*_Tier2_Qualitative`). **This must happen before the first subagent is dispatched.** After re-extraction the old artifacts are unreproducible, because the frozen inputs alone no longer regenerate them once `clean_dataset.py` points at the master.

### 9.2 How a reviewer tells a data change from a styling regression

Decision 5 guarantees the study set will shift, so "the figure changed" is uninformative on its own. The check makes the distinction mechanical:

1. **Derive the expected row-set diff from the tables, not the images.** Compare `baselines/<C>_Tier1_HedgesG.xlsx` against the rebuilt one, keyed on `study`. This yields three lists: studies added, studies removed, and studies whose `g` / `ci_lo` / `ci_hi` / `confidence` / `substance` / `N` changed. That diff is the *only* licensed explanation for any pixel difference.
2. **Check the geometry against the row count.** Forest-plot height is `max(5.0, 0.45 × n_rows + 2.0)` inches where `n_rows = n_studies + n_substance_headers`; the Tier 2 plot uses `max(5.0, 0.42 × n_rows + 2.5)`. If the rebuilt PNG's pixel height equals the value predicted from the new row count at the same DPI, the layout engine is unchanged. A height that does **not** match the prediction is a styling regression even if the row count changed.
3. **Pixel-compare the row-count-independent bands.** The title band, the legend band, the column-header row, and the x-axis label strip cannot be affected by any study row. Render baseline and rebuild at identical DPI, align on the top-left origin, and compare those bands: **any nonzero difference there is a styling regression and blocks.** The x-axis *tick range* is the one exception, since `x_min`/`x_max` derive from the CI extremes — a tick-range change is data-attributable only if the new extremes in the results table explain it, and is otherwise a regression.
4. **Pixel-compare the unchanged rows.** For any study present in both with identical `g`, `ci_lo`, `ci_hi`, `confidence`, `substance`, and `N`, its rendered row must be pixel-identical after vertical alignment. A difference there is a styling regression by construction, because nothing in its data changed.
5. **DOCX cell-by-cell via python-docx.** Split every difference into a **value** difference (cell text) and a **format** difference (shading hex, bold, italic, font name, point size, column widths, table row/column count, caption text). **Any format difference blocks.** Value differences must each map to an entry in the row-set diff or to a documented schema change.

**Rule: every difference must be explained by an entry in the row-set diff. An unexplained difference blocks.** The report lists differences in three columns — *explained by added/removed study*, *explained by changed value*, *unexplained* — and the third column must be empty.

**Two differences are known in advance and are declared, not discovered.** First, `figures/Alcohol_MethQual_BarPlot.png` will change in bar height, because §6.4 rewires it from stale literals to the live data; that is the intended effect of the fix and is licensed by the Table 2 diff. Second, Table 3 of each `*_Descriptive_Analyses.docx` contains the indicator row "Study design type reported", whose column no longer exists; `uspstf_value()` returns `NaN` for a missing column and `heat_color(NaN)` returns the existing grey `F2F2F2`, so the cell renders `—` on existing styling with no code change. Since the dropped column held the constant `"Clinical Trial"` in all 44 rows, the indicator was trivially 100% and carried no information — but the row count in the heading ("52 Indicators × 6 Domains") is now off by one, and whether to retire the row and retitle the table is a human's call, flagged as an open question rather than decided here.

### 9.3 Old/new comparison

The final gate step, specified in full in `archived/migration/clinical_old_new_mapping.md`: a deterministic per-study, per-field agreement check between the frozen `data/<Condition>_Dataset.xlsx` files and the new master, with a disagreement taxonomy separating expected differences from errors, a tighter standard for the four Tier-1 fields, and explicit acceptance criteria. It is the evidence for the claim that the redesign did not change the evidence — the claim §1.4 says the frozen files can honestly support, and the only one they can.
