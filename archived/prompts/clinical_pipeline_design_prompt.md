## Role

You are an experienced systematic-review methodologist with expertise in
epidemiology, biostatistics, and psychedelic clinical-trial research, working as
the architect of a research data pipeline. You are writing design documents, not
code. No implementation happens in this pass.

---

## Task

This repository contains two extraction pipelines:

- **Clinical trials (older).** A 56-column, one-row-per-study extraction split
  across three per-condition files in `data/`, produced by hand-pasting
  `opus_extraction_prompt.md` into a chat one article at a time. No manifest, no
  checkpointing, no archived requests/responses, no rationale capture, no
  validation gate.
- **Observational studies (newer).** A checkpointed, subagent-per-article,
  provenance-archiving pipeline specified by
  `observational_studies_system_design.md` + `observational_codebook.md` and
  implemented under `observational_studies/`.

**Rewrite the clinical-trial pipeline's PDF ingestion and coding layer to follow
the observational architecture.** Produce three documents at the repo root:

1. `clinical_system_design.md` — architecture, workflow, schema, file layout,
   input-fidelity handling, validation gate, and the adapter to the existing
   plotting layer. Mirror the structure and section ordering of
   `observational_studies_system_design.md`.
2. `clinical_codebook.md` — field-by-field conventions. Mirror the structure of
   `observational_codebook.md`.
3. `clinical_old_new_mapping.md` — the old↔new comparison contract (see
   "Deliverable 3" below).

The variable list stays the clinical-trial codebook already in use. The one
addition is the **CTCAE v5.0 → 3-band severity rubric with FDA-seriousness
cross-walk** from the observational pipeline, brought over so clinical-trial
adverse events are graded on the same scale.

---

## Read first (in this order)

| File | Read for |
|---|---|
| `observational_studies_system_design.md` | The architecture to mirror: subagent-per-article isolation, manifest checkpointing, two-part JSON response contract, provenance archival, deterministic merge + validation gate, input-fidelity handling. |
| `observational_codebook.md` | The codebook format to mirror, and the authoritative severity rubric (§5) you are importing. |
| `observational_studies/prompts/ae_extraction_prompt_v1.md` | What a pinned, dispatch-ready per-article prompt looks like — the `{{PLACEHOLDER}}` convention, the anti-fabrication rules, the enum-discipline language. Your design docs must be specific enough that the equivalent clinical prompt can be written from them. |
| `opus_extraction_prompt.md` | The 51 clinical variables, their types, and their exact coding rules. This content is preserved. |
| `scripts/_lib.py` | `build_results()`, `_build_layout()`, `_draw_ci_row()`, `_legend()`, `SUBSTANCE_COLORS`, `BINARY_COLS`, `primary_substance()`, `clean()`, `first_author_surname()` — read before deciding anything about the schema. |
| `scripts/tier1_hedges_g.py`, `scripts/unified_forest_plot.py`, `scripts/tier2_qualitative.py`, `scripts/unified_cat_plot.py` | The rendering layer whose output you must preserve, and the exact frame it consumes. |
| `scripts/clean_dataset.py`, `scripts/descriptive_analyses.py`, `run_pipeline.py` | The per-condition entry points that must keep producing their current outputs from a single master input. |
| `scripts/_config_alcohol.py` (and `_smoking`, `_opioid`) | `EFFECT_SIZE_EXTRACTIONS`, `CONVERSION_RULES`, `TIER2_RATINGS` — the `(surname, year)`-keyed lookups a new study must have entries in. |
| `data/Alcohol_Dataset.xlsx` | The authoritative current column list. Confirm all 56 names yourself. |
| `clinical_trials/inputs/pdfs/{alcohol,opioids,smoking}/` | The source corpus: 37 + 7 + 4 = 48 PDFs. |
| `observational_studies/scripts/merge_validate.py`, `preprocess_pdfs.py` | The implemented shape of the merge/validate and PDF→text steps. |
| `CLAUDE.md` §10 | Pipeline overview and conventions. |

Verify claims against these files. Do not assert a column name, function name, or
file path you have not read.

---

## Settled decisions — implement these, do not revisit or re-argue

These were decided by the principal investigator. Treat them as given. If one
creates a genuine problem, implement it and note the problem in your closing
report rather than silently substituting your own choice.

1. **One master dataset, not three per-condition files.** The store is a single
   study-level table with `Condition` (Alcohol / Smoking / Opioid) as a column.
   The observational dataset stays standalone — no join, no shared key.
2. **Column names carry over verbatim**, including the existing misspelling
   `Clincial Trial YN` and the punctuation in `Funding/COI YN`, `Citation/Title`,
   `url or link to pdf`, `Retention (%)`, `Followup in months`,
   `Implementation Outcome`. Newly added fields are additions, documented in
   deliverable 3; nothing existing is renamed. Emit the canonical `Retention (%)`
   and `Study Design Type` spellings (the Smoking file's legacy `Retention` /
   `StudyDesignType` variants disappear with the merge to one table).
3. **Binary variables stay numeric `1` / `0` / `3` / `"."`.** Do not adopt the
   observational pipeline's `"Y"` / `"N"` / `"NA"` enums for these. This keeps
   `_lib.recode_binary()`, `BINARY_COLS`, and `descriptive_analyses.py` working
   untouched, and makes old-vs-new comparison an exact diff with no value
   translation. State this divergence from the observational codebook explicitly,
   with the reason.
4. **The comparison target is old clinical vs new clinical** — the same studies
   under the old ad-hoc extraction versus the new automated one, to validate that
   the redesign did not change the evidence. Deliverable 3 serves this, not a
   clinical-vs-observational comparison.
5. **All studies are re-extracted under the new pipeline.** The three existing
   `data/<Condition>_Dataset.xlsx` files are frozen in place as the old-pipeline
   reference for deliverable 3. They are read-only from here on; the new pipeline
   writes elsewhere.
6. **AE severity lives in a linked `ae_events` table**, one row per distinct AE,
   keyed to the study row — the observational structure. The existing
   `HarmsAssessed` binary is preserved verbatim per decision 2; add the
   observational `SafetyReported` gate alongside it and define the consistency
   rule between the two.
7. **All current output artifacts keep their existing paths and filenames** —
   `data/<Condition>_Dataset_Cleaned.xlsx`, `figures/<Condition>_Tier1_ForestPlot.png`,
   `tables/<Condition>_Descriptive_Analyses.docx`, the unified figures, and the
   rest. The per-condition scripts and their `--condition` flag survive; they now
   filter the master table by `Condition` instead of opening one of three files.
8. **Convert PDFs to Markdown (`.md`) if the toolchain supports it, falling back
   to plain text (`.txt`) as the observational pipeline does.** Markdown is
   preferred because it preserves the structure this codebook depends on —
   headings that locate the Methods and Adverse Events sections, and table
   markup that keeps effect-size and AE tables from collapsing into
   whitespace-mangled prose. Specify the fallback rule per article, record which
   format each article used (extending the `text_source` provenance field), and
   state the fidelity check that decides whether a Markdown conversion is good
   enough to keep or must fall back.
9. **Screen every article for eligibility after conversion, extract every article
   regardless.** Eligibility has two criteria, both required: (a) the article
   reports a **clinical trial**, and (b) it reports an **outcome related to
   substance use disorder**. Record the verdict in an eligibility flag and, for
   every ineligible article, a required free-text note naming which criterion
   failed and why. Nothing is dropped at ingestion — ineligible articles are
   fully extracted, coded, and retained in the master table with the flag and
   note attached. This replaces a separate `IsObservational`-style design check:
   criterion (a) *is* the design check.

---

## The hard constraint: figures must stay aesthetically identical

Everything upstream of rendering — the extraction schema, the data store,
`clean_dataset.py`, the per-condition config dicts, even `build_results()` — may
be redesigned. The set of studies appearing in the forest plot and category plot
may legitimately change, since re-extraction may add, drop, or recode studies.
The corpus itself is larger than the current dataset (48 PDFs vs 44 extracted
rows), so new rows are expected.

What must not change is how the figures *look*: panel geometry, grouping and sort
order, colors, marker semantics, typography, reference lines, headers, legend
content and placement, axis labels, captions, and the docx table styling. A reader
comparing an old and new figure should see the same design with possibly different
rows.

**The safe way to guarantee that is to leave the rendering code untouched and
redesign only what feeds it.** The plot scripts consume one narrow, well-defined
frame — one row per study, with these columns and semantics:

| Column | Meaning |
|---|---|
| `study` | Display label, `"Surname Year"` |
| `Year` | Publication year (secondary sort key within substance) |
| `N` | Sample size, printed in the row label |
| `substance` | One of the `SUBSTANCE_COLORS` / `SUBSTANCE_ORDER_UNIFIED` keys — drives color, grouping, and legend |
| `metric`, `measure`, `method`, `note` | Effect-size provenance, carried into the results table |
| `confidence` | `clean` / `approx` / `excluded` — drives filled vs. hollow markers and the `*` / `†` tag |
| `d`, `g`, `var_g`, `se_g`, `ci_lo`, `ci_hi` | Point estimate, inverse-variance marker size, CI whiskers, printed stats |

Tier 2 adds `category` (and `computed_or`) on the same frame. `excluded` rows and
rows with null `g` must still be produced — the plots filter them out, and the
results tables keep them for traceability.

Treat that frame as the pipeline's output contract and say so explicitly in the
design document. If you propose changing any rendering code, state what visual
property is affected and why the change is unavoidable; "cleaner code" is not
sufficient reason.

**Verification.** Specify a visual-regression check: archive the current committed
PNGs and DOCXs as reference baselines *before* any re-extraction, then after the
rebuild compare new against baseline and confirm every difference is attributable
to a changed study row, not to changed styling. Name this as a gate step, not a
suggestion. Because decision 5 guarantees the study set will shift, this check is
the only thing separating a legitimate data change from an accidental styling
regression — say how a reviewer tells them apart.

---

## Constraints that survive

1. **`substance` values must remain drawn from the existing keys** — `Psilocybin`,
   `LSD`, `Mescaline`, `Ayahuasca`, `Ibogaine`, `OtherPsychedelic`, `MDMA`,
   `Ketamine`, `Cannabis`. These key `SUBSTANCE_COLORS`, `SUBSTANCE_DISPLAY`, and
   display order; a new label renders in fallback grey at the bottom of the
   ordering. The ten substance binaries and `primary_substance()` stay as they are.
   If the expanded corpus introduces a substance outside this set, say what must be
   added and where.
2. **`study` labels stay `"Surname Year"`**, and `(surname, Year)` remains the
   lookup key into `scripts/_config_<condition>.py`. A missing key currently raises
   `KeyError` at clean time. `first_author_surname()` splits `Citation/Title` on the
   first `,` or `;`, so the extracted citation must begin with the first author's
   surname. At least four new studies are guaranteed (the dropped alcohol PDFs), so
   this failure mode is a certainty, not a risk: specify how the identity scheme
   resolves to those keys, how the gate reports every study lacking
   `EFFECT_SIZE_EXTRACTIONS` / `CONVERSION_RULES` / `TIER2_RATINGS` entries as a
   named list rather than a bare `KeyError`, and who authors the missing entries.
   These are hand-coded methodological judgments about effect-size conversion — say
   plainly whether the extraction model may propose them and a human ratifies, or
   whether a human writes them outright, and where that hand-off sits in the
   workflow.
3. **`Outcome`, `SD`, `PVal`, and `SampleSize_NFinal` feed the Tier 1 conversion.**
   They drive `metric` / `measure` and therefore every point estimate on the forest
   plot. They warrant stricter extraction rules and mandatory rationale entries than
   the rest of the codebook. Say so, and say how.
4. **The `confidence` taxonomy stays `clean` / `approx` / `excluded`**, with the
   same meanings — it is marker semantics, not just metadata.

---

## Problems you must solve in the design (specify, don't defer)

1. **Corpus reconciliation.** 48 PDFs versus 44 rows in the current Excel files.
   Opioid (7) and smoking (4) match exactly. The entire gap is alcohol — 37 PDFs
   versus 33 rows — because four alcohol PDFs were dropped during the initial
   hand extraction. Those four are **in scope now**: they get converted,
   screened, extracted, and coded like everything else. Specify how the manifest
   is built, how each PDF is matched to an existing row or identified as new, how
   unmatched items in either direction are surfaced, and which direction blocks
   the run. Note the source folder is named `opioids` while the condition label
   is `Opioid`. This reconciliation is the input to deliverable 3.
2. **Eligibility screening (decision 9).** Specify the screen as a workflow step:
   where it runs relative to extraction, what evidence in the converted text
   supports each verdict, the flag's field name and value domain, and the note
   field that is mandatory whenever the verdict is ineligible. Define how the flag
   relates to the existing `Clincial Trial YN` codebook variable — that variable is
   the model's coding of the article's design, criterion (a) is the eligibility
   judgment built on it, and a disagreement between them is a signal worth
   surfacing. State which validation-gate failures block and which only warn, and
   decide (and justify) whether an ineligible study is excluded from the analytic
   figures and tables while remaining in the master dataset. Whatever you choose,
   that exclusion must be a single documented filter a reviewer can flip, not
   logic scattered across scripts. Preserve the "extract every field regardless,
   flag for human review" discipline throughout.
3. **`MethodologyDescribedYN`'s 14-criterion checklist.** A composite judgment
   collapsed to one binary, currently unauditable. Keep the binary in the `data`
   half; capture the per-criterion detail in the `rationale` half. Specify the
   structure and say what it buys.
4. **Master-table plumbing.** Say exactly how `clean_dataset.py`,
   `tier1_hedges_g.py`, `tier2_qualitative.py`, `descriptive_analyses.py`, and
   `run_pipeline.py` read one master table while keeping their `--condition` flag
   and their current output paths (decision 7). Name the file paths and formats for
   the master store and the `ae_events` table.

---

## Content requirements

**`clinical_system_design.md`** covers, at minimum:

- Scope, and the relationship to the observational dataset (separate, no shared key).
- Execution environment: Claude Code on a subscription with token limits — the same
  two consequences the observational design derives (checkpointing, explicit
  archival) apply.
- Architecture: one subagent per article, batch size, and the isolation argument for
  why articles are not batched into a single call. Do not restate the observational
  rationale verbatim; state where the clinical case differs — 51 variables per
  article rather than 8 is a materially larger extraction, with implications for
  per-call context and error modes.
- Workflow: convert (PDF → `.md`, `.txt` fallback) → screen for eligibility →
  dispatch → checkpoint → merge/validate → rebuild figures → old/new comparison,
  with the manifest schema and resume-from-manifest behavior. Give the conversion
  step its own treatment per decision 8: the tool or library chosen, the
  Markdown-vs-text fallback rule, what structure Markdown is expected to preserve
  and why it matters for this codebook specifically, and the per-article fidelity
  check. Say whether eligibility screening is a separate pass over the converted
  text or the opening step of the extraction subagent, and justify the choice on
  context-isolation grounds.
- Response contract: the two-part `{"data": …, "rationale": …}` object, adapted to
  the flat clinical row plus the AE array.
- Output schema, folder layout, and **the adapter section**: how the master schema
  maps onto the plot frame above, and which module owns that mapping.
- Input-fidelity handling for the pre-1980 scanned corpus, carrying over the
  anti-fabrication rule about never inventing a decode for inconsistent numbers.
- Validation gate: type/enum checks, gate-consistency rules, provenance
  completeness, config-key existence, plot-frame conformance, eligibility-note
  completeness (every ineligible article carries a note), text-conversion
  provenance, and the visual-regression check — stating which failures block and
  which warn.
- Provenance and reproducibility, including the same honest caveat that temperature
  0 gives archived-verbatim provenance, not bit-identical reproducibility. Address
  head-on that the frozen old-pipeline rows have no archived request/response, and
  what the dataset's provenance claim can therefore honestly be.

**`clinical_codebook.md`** covers, at minimum:

- Purpose, design principles, cross-references.
- Crosswalk: source variable → stored field(s) → table.
- Missingness conventions in the clinical pipeline's own terms (`1`/`0`/`3`/`"."`
  for binaries; `"."` / `"NA - reason"` for the rest), with the divergence from the
  observational conventions called out and justified per decision 3.
- Field-by-field spec for all 56 existing columns plus every added field: type,
  valid values, coding rule. Carry the definitions from `opus_extraction_prompt.md`
  forward; sharpen any that are ambiguous, and flag what you sharpened.
- **The eligibility fields** (decision 9): the flag and its mandatory note, with
  worked examples of each ineligibility class — not a clinical trial, no
  substance-use-disorder outcome, both — and guidance for the boundary cases this
  corpus will actually produce: single-arm open-label studies, secondary analyses
  of trial data, trials whose only SUD outcome is a secondary endpoint.
  New QC and provenance fields use the observational pipeline's `Y`/`N` enum
  convention rather than the numeric codes; they are **not** added to `BINARY_COLS`
  and `recode_binary()` never touches them. State this rule once, explicitly, so
  the mixed convention within one table is a documented choice rather than an
  inconsistency.
- The `ae_events` table field spec.
- The severity rubric, reproduced authoritatively: CTCAE grade → 3-band collapse,
  FDA seriousness criteria, PAT-context operational band definitions, the Grade-3
  tiebreak, severity-source precedence, and the under-specified-AE default with its
  `SeverityIndeterminate` flag. Keep the PAT adaptation principle. Note where the
  clinical-trial context differs from the observational one — trial protocols more
  often carry author-assigned CTCAE grades and explicit SAE flags, which changes how
  often `SeveritySource = author` applies.
- The validation gate, restated at field level.

**Deliverable 3 — `clinical_old_new_mapping.md`** is the contract that makes the
old and new datasets comparable. It covers:

- **Field crosswalk.** Every column in the frozen `data/<Condition>_Dataset.xlsx`
  files mapped to its counterpart in the master table. Per decision 2 most are
  identity mappings — say so once and then enumerate only the exceptions: added
  fields, the `Retention` / `StudyDesignType` spelling normalization, the loss of
  per-file separation in favor of the `Condition` column, and anything else that is
  not a straight pass-through.
- **Row identity.** How an old row is matched to its new counterpart — the join key,
  how it is derived on both sides, and how ties and near-misses are handled.
- **Comparison procedure.** A deterministic per-study, per-field agreement check:
  what counts as agreement for each type (exact for binaries and enums, tolerance
  for continuous fields — state the tolerance and justify it, semantic rather than
  string comparison for free text), and what report it emits.
- **Expected-disagreement taxonomy.** Classes of difference that are *not* errors:
  the four previously dropped alcohol studies, which have no old counterpart by
  construction; an old row the new eligibility screen flags ineligible, which is a
  finding about the old dataset rather than a migration defect; corrected old
  miscodes; fields the old process left blank that the new one fills; genuine
  judgment differences on ambiguous articles. Distinguish these from classes that
  *are* errors and must be investigated — a flipped binary, a changed sample size,
  a changed effect size. Report counts per class, so the reviewer sees the shape of
  the disagreement rather than a flat list.
- **Effect-size fields specifically.** `Outcome`, `SD`, `PVal`, `SampleSize_NFinal`
  determine forest-plot positions. Specify a tighter agreement standard for these
  and state what magnitude of disagreement blocks acceptance of the new dataset.
- **Acceptance criteria.** What agreement level constitutes a successful migration,
  and what the reviewer does with the residue.

---

## Style

Match the register of the two observational documents: dense, declarative, tables
where tables carry the content, prose where reasoning carries it. Every design
choice states its reason. No filler, no hedging, no marketing tone. Where the
observational design made a choice you are inheriting, say so and cite the section
rather than re-arguing it. Where you diverge, say why in one sentence.

Length guide: `clinical_system_design.md` roughly the size of its observational
counterpart; `clinical_codebook.md` necessarily longer, since 56-plus fields need
individual specs; `clinical_old_new_mapping.md` as short as the content allows.

---

## Deliverable

Write the three files to the repo root. Then report, in at most fifteen lines:

- How you resolved each of the four problems in "Problems you must solve."
- Any rendering code you propose to change, with the visual property affected. If
  none, say none.
- Any settled decision that created a real problem, and the problem.
- Anything you could not verify from the files, left as an open question for the
  human reviewer.

Do not write, modify, or scaffold any code, script, or prompt file in this pass.
