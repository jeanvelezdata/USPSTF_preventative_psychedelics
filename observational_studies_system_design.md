# System Design — Adverse-Event / Demographics Extraction

**Scope.** A narrow codebook (adverse events / challenging experiences + basic demographics) applied to 44 articles, producing a **standalone dataset** analyzed separately from the main 52-variable USPSTF pipeline. It does not join that pipeline.

**Codebook.** Seven extracted items, from the eight-item source list in `opus_extraction_prompt_observational.md` (item 5, "% positive outcomes," is intentionally excluded — see §5). Field-by-field conventions live in the companion `observational_codebook.md`; this document covers architecture, workflow, schema, and the severity rubric.

**Execution environment.** Claude Code on a Claude subscription with token limits (no Anthropic API key). This shapes two design requirements the rest of the document builds on: the run must be **checkpointed** so a token-limit interruption resumes rather than restarts, and **archival artifacts must be written explicitly** because nothing in an orchestrated run archives itself.

---

## 1. Architecture — one subagent per article, checkpointed

Each article is extracted by its own Claude Code Task-tool subagent, dispatched in batches of ~6 for failure isolation. The subagent boundary is the core design choice: it gives every article a **clean, isolated context**, which is what a per-study safety judgment requires. A single main-agent loop over the corpus would accumulate every prior article in context and produce cross-article contamination — severity anchoring (one severe AE inflating a neighbor's grade), demographic bleed, and AE-count confusion. For the same reason, **multiple articles per call is rejected**: packing several articles behind delimiters reintroduces exactly that contamination to save call count the task does not need saved.

Scale is small — the whole job is roughly 0.5–1.0M input + ~0.1M output tokens — so cost and latency are non-issues; isolation and auditability drive the design, not throughput.

### 1.1 Workflow

1. **Preprocess (scripted, deterministic).** Convert each source PDF to text, one `.txt` per article. Record a `text_source` value (`born-digital` / `OCR` / `manual`) per article — see §7.
2. **Dispatch.** For each not-yet-done article, spawn one subagent with that article's text plus the pinned codebook/rubric prompt. Before extracting anything else, the subagent verifies the article is an observational study (as opposed to an RCT or other controlled experimental design) and records this in `IsObservational` — a corpus-curation sanity check, since this corpus is intended to be all-observational. A `"N"` does not stop extraction; the subagent still extracts every other field and explains its call in `rationale`, so a human reviewer has the full record to decide whether the article belongs in the dataset. The subagent returns the two-part object (§2) for that one article.
3. **Checkpoint on return.** As each subagent completes, immediately write its `{StudyID}_request` context, `{StudyID}_response.json`, and rationale to disk, and mark the `StudyID` done in the manifest. An interrupted session **resumes from the manifest**, re-dispatching only unfinished articles. This same discipline is the audit trail.
4. **Merge + validate (separate, deterministic step).** Once all articles are done, assemble `articles.csv` + `ae_events.csv`, split the rationale halves into `rationale_log.md`, and run the validation gate (§8). Keep this outside the subagents so it re-runs without re-extracting.

Bump `RubricVersion` on every rubric change so archived responses stay traceable to the rubric that produced them; a rubric revision means re-running the affected articles (cheap at this scale).

### 1.2 Provenance and reproducibility

Archive, per article: the pinned prompt + rubric version, the exact input text seen, the model's rationale, model name/version and parameters (temperature 0), and the raw response. The checkpoint step (1.1 #3) produces all of these.

Note for the methods appendix: even at temperature 0, LLM output is not guaranteed bit-identical across runs or model minor-versions. The defensible claim is *"every request and response is archived verbatim"* (provenance), not *"re-running reproduces identical codes"* (determinism).

---

## 2. Response contract — two-part object

Each subagent returns a **single JSON object** with two halves and nothing else (no prose, no markdown fences):

```json
{ "data": { … extracted fields … }, "rationale": { … keyed non-obvious calls … } }
```

Both halves are valid JSON. The `data` half is machine-validated against the schema (§6) and gate (§8); the `rationale` half is split off at merge into `rationale_log.md`. This makes the rationale a first-class, per-article artifact — essential for the severity item, where "why Mild vs. Moderate" must be recorded for every judgment.

---

## 3. Severity rubric

A fixed three-level scale grounded in **CTCAE v5.0** severity grading collapsed to three bands, cross-walked with **FDA seriousness criteria**, adapted so that expected, protocol-anticipated transient effects of psychedelic dosing do not automatically inflate severity. The authoritative, implementation-ready version — including the explicit CTCAE-grade → 3-band collapse table and the enumerated FDA seriousness criteria — is in `observational_codebook.md`; this is the design summary.

**Core adaptation principle.** In psychedelic-assisted therapy, intense in-session anxiety, fear, perceptual distortion, and challenging-experience phenomenology (Barrett CEQ sense) are *expected* and are graded **by their consequences and intervention need, not by subjective intensity during dosing.** A high CEQ score alone → Mild, unless accompanied by intervention need or persistence.

| Level | Anchor | Operational criteria (PAT context) |
|---|---|---|
| **Mild** | CTCAE Grade 1 | Transient, expected, self-limiting; no or minimal intervention; resolves within/shortly after the session; no functional impairment beyond the acute dosing period. E.g., transient anxiety, nausea, headache, transient mild BP/HR elevation, perceptual distortion, challenging-experience phenomenology resolved with reassurance and no pharmacological rescue. **Expected acute drug effects default here** unless they escalate. |
| **Moderate** | CTCAE Grade 2, and Grade 3 meeting **no** FDA seriousness criterion | Requires active intervention (e.g., benzodiazepine rescue, antihypertensive, antiemetic) **or** causes functional impairment persisting beyond the dosing day (persisting anxiety, low mood, sleep disturbance lasting days to a few weeks) — but meets **no** FDA seriousness criterion. |
| **Severe** | CTCAE Grade 4–5, **or any** grade meeting an FDA seriousness criterion | Any event meeting an FDA "serious" criterion — death, life-threatening event, inpatient hospitalization or prolongation, persistent/significant disability, congenital anomaly, or a medically important event requiring intervention to prevent one of these. In PAT: suicidal behavior/attempt, psychosis or prolonged psychotic reaction, seizure, serious cardiovascular event, hospitalization, HPPD, or any author-labeled **serious adverse event (SAE)**. |

**Grade-3 tiebreak.** A CTCAE Grade 3 event is **Moderate by default, Severe only if it meets an FDA seriousness criterion.** FDA-seriousness is the single tiebreaker between the top two bands, so no event falls in two rows.

**Severity source precedence.** When authors assign a CTCAE grade or SAE flag, use theirs (`SeveritySource = author`); otherwise apply the rubric (`SeveritySource = rubric`).

**Under-specified AEs.** When an AE is reported with too little detail to grade: grade on whatever intervention/outcome/seriousness signals are present; absent any signal, default **Mild** and set `SeverityIndeterminate = Y`. This is a deliberate safety-direction choice — defaulting such events to Severe would overstate harm as much as ignoring them understates it. The middle path: default Mild, but (a) flag every such grade, (b) route all flagged rows to human review before publication, and (c) keep the flag usable as a filter so a sensitivity analysis can recompute rates with indeterminate events excluded or escalated. Never absorb an ungradeable event silently into a point estimate.

**Verify before manuscript.** Confirm the exact CTCAE v5.0 anchor text and FDA seriousness wording verbatim against the source documents before the rubric enters the manuscript methods.

---

## 4. Adverse-event data model

**AE-level long format.** One row per distinct AE with its own severity, plus an article-level `WorstSeverity` rollup. This preserves the severity distribution; an article-level-only "worst severity" discards it.

**Three-state AE presence (must not collapse).** These are distinct and separately coded:
- *Article states no AEs occurred* → real 0.
- *AEs reported but not counted* → "Not numbered".
- *Article silent on AE/safety entirely* → not reported.

A `SafetyReported` (Y/N) gate separates "no AEs" from "didn't look" — without it, no AE rate can be computed.

**AE vs. challenging experience.** Each AE row carries an `AE_type` flag (`AE` / `challenging_experience` / `both`). CEQ-style challenging experiences are often expected and in-session, not clinical AEs; counting them unflagged inflates apparent AE burden.

**Counting unit.** Primary count is **distinct AE types** (`NumDistinctAEs`); **participants-with-≥1-AE** (`NParticipantsWithAE`) is a companion when reported. ("12 participants reported headache" = 1 type / 12 affected — different numbers.)

**AE denominator.** An AE count needs the population it applies to, frequently the *safety/enrolled* population rather than the *final analyzed* `N`. `AE_denominator` captures it; without it no defensible per-study AE rate exists.

**Arm scope.** A safety comparison usually wants the active-psychedelic arm. `ArmScope` records whether `N` / AE counts / demographics are restricted to the psychedelic arm(s) or pooled — a pooled denominator silently dilutes an AE rate.

---

## 5. Demographics and excluded items

- **% female (item 8).** Convention is % female (AFAB if identity not reported), with the reported gender category label stored in a companion field so non-binary/other reporting is not lost.
- **BIPOC / Indigenous (items 6, 7).** BIPOC = all non-white. Indigenous is a subset of BIPOC — reported separately (`PctIndigenous`) **and** counted within `PctBIPOC`. Hispanic/Latino ethnicity crosses racial categories and is reported inconsistently; capture as reported and note in rationale.
- **% positive outcomes (item 5) — excluded.** Under-defined for a safety codebook (positive by which outcome, whose threshold?) and the weakest fit for a safety/demographics dataset. Not stored.

---

## 6. Output schema and file layout

**Two linked tables plus a rationale log.** Field-level types and valid values are in `observational_codebook.md`; this is the structural summary.

**`articles` (one row per article):** `StudyID`, `Citation`, `Title`, `Year`, `Corpus/Prefix`, `Condition` (Alcohol/Smoking/Opioid — the disorder targeted), `Substance` (the psychedelic/dissociative substance(s) administered as treatment), `IsObservational` (Y/N — subagent-verified corpus-curation check, §1.1; extraction proceeds either way), `N`, `PctFemale` (+ `GenderCategory`), `PctBIPOC`, `PctIndigenous`, `SafetyReported` (Y/N), `AnyAEReported` (Y/N/NA), `NumDistinctAEs` (integer / "Not numbered" / NA), `NParticipantsWithAE` (integer / NA), `AE_denominator` (+ `ArmScope`), `WorstSeverity` (Mild/Moderate/Severe rollup, "None" if real 0, NA if not assessed), `text_source` (born-digital/OCR/manual), `Model`, `PromptVersion`, `RubricVersion`, `Temperature`.

**`ae_events` (one row per distinct AE):** `AE_ID`, `StudyID` (FK), `AE_type` (AE/challenging_experience/both), `Description` (free text), `Onset` (in-session/post-session-acute/delayed/unknown), `Severity` (Mild/Moderate/Severe), `SeverityIndeterminate` (Y/N), `SeveritySource` (author/rubric), `InterventionRequired` (Y/N), `MeetsFDASerious` (Y/N), `Rationale`.

**`rationale_log`** — consolidated per-article and per-AE non-obvious decisions, built by splitting the `rationale` half out of each response.

**Identity.** `StudyID` is a simple, human-readable primary key — `Surname Year` (with a disambiguating suffix like `Surname Year b` for collisions) or a sequential corpus ID. No cross-dataset key normalization is needed, since this dataset stands alone.

**Folder layout** (structure only — scripts built in the implementation pass):

```
aedemographics_extraction/
  prompts/
    ae_extraction_prompt_v1.md      # pinned, versioned; embeds the rubric
    severity_rubric_v1.md           # or embedded in the prompt; version-pinned either way
  inputs/
    pdfs/                           # 44 source PDFs
    text/                           # deterministic PDF->text, one .txt per article
    manifest.csv                    # StudyID <-> filename <-> citation <-> year <-> text_source <-> done?
  raw_responses/
    {StudyID}_request.json          # immutable archival artifacts
    {StudyID}_response.json
  outputs/
    articles.csv                    # -> exported to .xlsx
    ae_events.csv
    rationale_log.md
    validation_report.txt           # schema-gate + gate-consistency results
```

---

## 7. Input-fidelity handling

The corpus spans 1958–2026; the pre-1980 articles are scanned PDFs requiring OCR, and two-column layouts and embedded tables extract poorly even for modern PDFs. For a safety extraction this is a first-order risk — an OCR error in an AE description or event count silently corrupts the exact variable the codebook exists to capture. Handling:

- Verify extracted text against the source PDF for the oldest articles before extraction; OCR (and spot-check) where the PDF is image-only.
- Instruct the model to **flag garbled or truncated input** in its rationale and code affected fields not-reported rather than guess.
- Record `text_source` per article so downstream analysis can stratify on extraction quality.

---

## 8. Validation gate

A deterministic post-step; failures block merge and are written to `validation_report.txt`:

- **Type/enum check** per article against the codebook. `Severity`, `AE_type`, `Onset`, `SeveritySource`, `WorstSeverity`, `ArmScope` values are drawn only from their allowed sets.
- **Gate-consistency rules** (these make the safety data interpretable):
  - `SafetyReported = N` ⇒ `AnyAEReported = NA`, `NumDistinctAEs = NA`, `WorstSeverity = NA`, zero `ae_events` rows.
  - `AnyAEReported = N` (real 0) ⇒ `NumDistinctAEs = 0`, `WorstSeverity = None`, zero `ae_events` rows.
  - `AnyAEReported = Y` ⇒ ≥1 `ae_events` row **or** `NumDistinctAEs = "Not numbered"`.
  - `WorstSeverity` = max `Severity` across the article's `ae_events` rows.
  - `PctIndigenous ≤ PctBIPOC` when both are numeric.
  - Every `ae_events.StudyID` exists in `articles.StudyID` (referential integrity).
  - Every `SeverityIndeterminate = Y` row appears in the human-review queue.
- **Provenance completeness:** `Model`, `PromptVersion`, `RubricVersion`, `Temperature`, `text_source` non-empty for every article.
- **Design warning (non-blocking):** any article with `IsObservational = N` is listed in `validation_report.txt` for human review. Unlike the checks above, this does not block merge — it is a corpus-curation flag, not a data-integrity failure.
