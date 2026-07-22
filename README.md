# USPSTF Evidentiary-Gap Analysis: Psychedelic Interventions for Substance Use Disorders

Systematic evidence review of psychedelic-assisted therapies (psilocybin, LSD, MDMA, ketamine, ayahuasca, ibogaine, mescaline, cannabis, and others) as treatments for **alcohol use disorder (AUD)**, **tobacco/nicotine use disorder**, and **opioid use disorder (OUD)**. The goal is to characterize the existing trial evidence against USPSTF-style evidentiary standards, identify methodological and coverage gaps, and produce standardized effect sizes (Hedges' g) for studies where that conversion is defensible.

The repo produces the **Results section only** (tables and figures) of a manuscript; all prose is written by the human author.

## Current status

| Condition | Studies extracted | Year range | Tier 1 convertible | Tier 2 (excluded from Tier 1) |
|---|---|---|---|---|
| Alcohol | 33 | 1958–2025 | 13 | 20 |
| Smoking | 4 | 2014–2026 | 1 | 3 |
| Opioid | 7 | 1973–2016 | 2 | 5 |

For alcohol, the era split is Pre-1980 (n=13) vs. 2010+ (n=20), with no studies in the 1980–2009 gap. "Tier 1 convertible" means a clean or approximate Hedges' g could be computed from the reported statistics; everything else is classified qualitatively in Tier 2 (see [Analysis pipeline](#analysis-pipeline) below).

## Stack

- Language: Python 3.12
- Key libraries: pandas, numpy, openpyxl, python-docx, matplotlib
- Python runtime on this machine: `C:/Users/jeanv/miniforge3/python.exe` — use this path explicitly; the `python` / `py` shims resolve to the Microsoft Store stub and do nothing

### Install

```
C:/Users/jeanv/miniforge3/python.exe -m pip install -r requirements.txt
```

For a byte-for-byte reproduction of published results, install the pinned versions instead:

```
C:/Users/jeanv/miniforge3/python.exe -m pip install -r requirements-lock.txt
```

## Running the pipeline

Run everything from the project root with one command:

```
C:/Users/jeanv/miniforge3/python.exe run_pipeline.py
```

This runs, per condition (`alcohol`, `smoking`, `opioid`), in order: `clean_dataset.py` → `tier1_hedges_g.py` → `tier2_qualitative.py` → `descriptive_analyses.py`. A condition is skipped with a printed warning (not an abort) if its raw data file or config is missing/unpopulated.

Individual stages can also be run directly, all accepting `--condition alcohol|smoking|opioid`:

```
C:/Users/jeanv/miniforge3/python.exe scripts/clean_dataset.py --condition <c>
C:/Users/jeanv/miniforge3/python.exe scripts/tier1_hedges_g.py --condition <c>
C:/Users/jeanv/miniforge3/python.exe scripts/tier2_qualitative.py --condition <c>
C:/Users/jeanv/miniforge3/python.exe scripts/descriptive_analyses.py --condition <c>
```

Three additional standalone scripts build cross-condition/summary figures and are **not** part of `run_pipeline.py` — run them manually after the pipeline, once outputs for all three conditions exist:

```
C:/Users/jeanv/miniforge3/python.exe scripts/unified_forest_plot.py   # figures/Unified_Tier1_ForestPlot.png
C:/Users/jeanv/miniforge3/python.exe scripts/unified_cat_plot.py      # figures/Unified_Tier2_CatPlot.png
C:/Users/jeanv/miniforge3/python.exe scripts/methqual_bar_plot.py     # figures/Alcohol_MethQual_BarPlot.png
```

`unified_forest_plot.py` and `unified_cat_plot.py` combine every condition's Tier 1 / Tier 2 results into a single figure, grouped by condition then substance. `methqual_bar_plot.py` is alcohol-specific and plots Table 2 (Methodological Quality, Pre-1980 vs. 2010+) as a bar chart; its percentages are hardcoded from `tables/Alcohol_Descriptive_Analyses.docx` and must be updated by hand if that table changes.

## Layout

```
USPSTF/
├── aedemographics_extraction/         # standalone AE/demographics extraction pipeline — see below
├── data/
│   ├── Alcohol_Dataset.xlsx           # raw extraction (source of truth)
│   ├── Alcohol_Dataset_Cleaned.xlsx   # output of clean_dataset.py --condition alcohol
│   ├── Smoking_Dataset.xlsx           # raw extraction (source of truth)
│   ├── Smoking_Dataset_Cleaned.xlsx   # output of clean_dataset.py --condition smoking
│   ├── Opioid_Dataset.xlsx            # raw extraction (source of truth)
│   └── Opioid_Dataset_Cleaned.xlsx    # output of clean_dataset.py --condition opioid
├── figures/
│   ├── Alcohol_Tier1_ForestPlot.png   # tier1_hedges_g.py --condition alcohol
│   ├── Alcohol_Tier2_CatPlot.png      # tier2_qualitative.py --condition alcohol
│   ├── Alcohol_MethQual_BarPlot.png   # methqual_bar_plot.py (standalone, alcohol only)
│   ├── Smoking_Tier1_ForestPlot.png   # tier1_hedges_g.py --condition smoking
│   ├── Smoking_Tier2_CatPlot.png      # tier2_qualitative.py --condition smoking
│   ├── Opioid_Tier1_ForestPlot.png    # tier1_hedges_g.py --condition opioid
│   ├── Opioid_Tier2_CatPlot.png       # tier2_qualitative.py --condition opioid
│   ├── Unified_Tier1_ForestPlot.png   # unified_forest_plot.py (standalone, all conditions)
│   └── Unified_Tier2_CatPlot.png      # unified_cat_plot.py (standalone, all conditions)
├── tables/
│   ├── Alcohol_Descriptive_Analyses.docx  # descriptive_analyses.py --condition alcohol
│   ├── Alcohol_Tier1_HedgesG.xlsx         # tier1_hedges_g.py --condition alcohol
│   ├── Alcohol_Tier2_Qualitative.xlsx     # tier2_qualitative.py --condition alcohol
│   ├── Smoking_Descriptive_Analyses.docx  # descriptive_analyses.py --condition smoking
│   ├── Smoking_Tier1_HedgesG.xlsx         # tier1_hedges_g.py --condition smoking
│   ├── Smoking_Tier2_Qualitative.xlsx     # tier2_qualitative.py --condition smoking
│   ├── Opioid_Descriptive_Analyses.docx   # descriptive_analyses.py --condition opioid
│   ├── Opioid_Tier1_HedgesG.xlsx          # tier1_hedges_g.py --condition opioid
│   └── Opioid_Tier2_Qualitative.xlsx      # tier2_qualitative.py --condition opioid
├── scripts/
│   ├── _lib.py                    # shared constants and helpers (do not run directly)
│   ├── _config_alcohol.py         # alcohol EFFECT_SIZE_EXTRACTIONS + CONVERSION_RULES + TIER2_RATINGS
│   ├── _config_smoking.py         # smoking EFFECT_SIZE_EXTRACTIONS + CONVERSION_RULES + TIER2_RATINGS
│   ├── _config_opioid.py          # opioid EFFECT_SIZE_EXTRACTIONS + CONVERSION_RULES + TIER2_RATINGS
│   ├── clean_dataset.py           # condition-agnostic cleaner (--condition flag)
│   ├── descriptive_analyses.py    # five descriptive tables per condition (--condition flag)
│   ├── tier1_hedges_g.py          # Hedges' g conversion + forest plot (--condition flag)
│   ├── tier2_qualitative.py       # qualitative classification + category plot (--condition flag)
│   ├── unified_forest_plot.py     # cross-condition Tier 1 forest plot (standalone)
│   ├── unified_cat_plot.py        # cross-condition Tier 2 category plot (standalone)
│   └── methqual_bar_plot.py       # alcohol Methodological Quality bar chart (standalone)
├── run_pipeline.py                    # runs all conditions; skips unpopulated ones
├── requirements.txt                   # minimum version bounds
├── requirements-lock.txt              # exact versions used for published results
├── Draft Text and Outline_USPS.docx   # manuscript draft
├── PROJECT_PLAN.md                    # task-by-task engineering plan
└── CLAUDE.md                          # agent operating instructions
```

## Analysis pipeline

**Step 1 — `clean_dataset.py --condition <c>`**
Input: `data/<Condition>_Dataset.xlsx`. Output: `data/<Condition>_Dataset_Cleaned.xlsx`. Normalizes column-name variants across datasets, strips whitespace, replaces `.` with NaN, coerces numeric columns, recodes binary columns (0/1 preserved, 3 → "Does not apply"), converts `BaseStatus` to an ordered categorical, and extracts the effect-size `metric`/`measure` via `EFFECT_SIZE_EXTRACTIONS` in the per-condition config.

**Step 2a — `descriptive_analyses.py --condition <c>`**
Output: `tables/<Condition>_Descriptive_Analyses.docx`. Five Word tables: (1) Study Characteristics by era, (2) Methodological Quality by era, (3) USPSTF Gap Heat Map (52 indicators × 6 domains, heat-colored), (4) Outcome Domains by era, (5) Follow-up Duration Distribution. Missing/not-reported is treated as not met (strict USPSTF gap interpretation).

**Step 2b — `tier1_hedges_g.py --condition <c>`**
Outputs: `tables/<Condition>_Tier1_HedgesG.xlsx` + `figures/<Condition>_Tier1_ForestPlot.png`. Converts per-study effect sizes to Hedges' g using `CONVERSION_RULES` from the per-condition config. Supported methods: Cohen's d, Hedges' g (pass-through), F (1 df numerator), partial η², χ² (1 df), OR, RR. Studies with multi-df F, within-subjects designs, single-arm rates, or no usable statistic are marked `confidence = excluded` and retained in the table for traceability. Forest plot groups by substance, sorted by year; filled squares = clean conversion, hollow squares = approximate.

**Step 2c — `tier2_qualitative.py --condition <c>`**
Outputs: `tables/<Condition>_Tier2_Qualitative.xlsx` + `figures/<Condition>_Tier2_CatPlot.png`. Classifies studies excluded from Tier 1 into qualitative categories using `TIER2_RATINGS` from the per-condition config: negative, null, small_positive, moderate_positive, large_positive, single_arm_positive, unclassifiable. Computes OR from two-group proportions where applicable.

## Results summary

- **Alcohol** (33 studies, 1958–2025): 13 studies convert cleanly/approximately to Hedges' g, ranging from g = −0.81 to g = +1.23 (median g = 0.52, favoring the psychedelic arm). The remaining 20 studies — mostly pre-1980 uncontrolled or single-arm designs — are classified qualitatively in Tier 2. Methodological quality is markedly higher in the 2010+ era than pre-1980 (e.g., double-blinding: 50% vs. 15%; validated outcome scales: 100% vs. 31%; power reported: 35% vs. 0%) — see `figures/Alcohol_MethQual_BarPlot.png` and Table 2 of `tables/Alcohol_Descriptive_Analyses.docx`.
- **Opioid** (7 studies, 1973–2016): 2 studies convert to Hedges' g (g = 0.46 and g = 1.37); the remaining 5 are Tier 2.
- **Smoking** (4 studies, 2014–2026): 1 study converts to Hedges' g (g = 0.99); the remaining 3 are Tier 2.
- Across all three conditions, no studies fall in the 1980–2009 gap.

Full per-study effect sizes, conversion confidence, and USPSTF gap indicators are in the `tables/*_Tier1_HedgesG.xlsx`, `tables/*_Tier2_Qualitative.xlsx`, and `tables/*_Descriptive_Analyses.docx` files. Cross-condition figures are `figures/Unified_Tier1_ForestPlot.png` and `figures/Unified_Tier2_CatPlot.png` (generated by the standalone scripts above, not by `run_pipeline.py`).

## AE / demographics extraction pipeline (standalone)

A second, independent pipeline lives under `aedemographics_extraction/` and is **not** part of `run_pipeline.py` or the alcohol/smoking/opioid analysis above — it does not read or write anything in `data/`, `tables/`, or `figures/`. It extracts structured adverse-event and demographic data from primary observational articles using one LLM subagent per article, then merges and validates the results deterministically. See `observational_studies_system_design.md` (architecture) and `observational_codebook.md` (field/schema reference) for the full spec.

### Layout

```
aedemographics_extraction/
├── inputs/
│   ├── pdfs/              # source article PDFs (place new articles here)
│   ├── text/               # {StudyID}.txt, output of preprocess_pdfs.py
│   └── manifest.csv         # StudyID, filename, citation, year, text_source, done
├── prompts/
│   ├── ae_extraction_prompt_v1.md   # pinned extraction prompt (read in full by every subagent)
│   └── severity_rubric_v1.md        # severity classification rubric, embedded in the prompt
├── raw_responses/
│   ├── {StudyID}_request.json    # dispatch provenance (prompt/rubric version, model, timestamp, ...)
│   ├── {StudyID}_response.json   # subagent's two-part {data, rationale} JSON
│   └── {StudyID}_excluded.txt    # articles excluded from dispatch (non-primary/non-observational), with reason
├── outputs/
│   ├── articles.csv              # one row per article
│   ├── ae_events.csv             # one row per adverse event / challenging experience
│   ├── human_review_queue.csv    # SeverityIndeterminate=Y events, for manual review
│   ├── rationale_log.md          # per-field extraction rationale, per article
│   └── validation_report.txt     # pass/fail + non-blocking warnings from the last merge
└── scripts/
    ├── _lib.py             # schema constants, enums, validators (do not run directly)
    ├── preprocess_pdfs.py  # PDF -> text (PyMuPDF, OCR fallback via Tesseract)
    └── merge_validate.py   # merges raw_responses/ -> outputs/, runs the validation gate
```

### Reproducing the extraction

1. **Add source PDFs.** Drop article PDFs into `aedemographics_extraction/inputs/pdfs/`.
2. **Preprocess to text:**
   ```
   C:/Users/jeanv/miniforge3/python.exe aedemographics_extraction/scripts/preprocess_pdfs.py
   ```
   Extracts text via PyMuPDF; falls back to Tesseract OCR for scanned/image-only PDFs (`conda install -c conda-forge tesseract` — the OCR engine is not pip-installable, only the `pytesseract` wrapper is). Idempotent: re-running only processes PDFs not already marked `done=Y` in `inputs/manifest.csv`, and prunes manifest rows for PDFs that were removed. Citation and year cannot be derived from the PDF alone and must be filled in `manifest.csv` by hand before dispatch.
3. **Dispatch extraction.** This step is LLM-driven, not a script. In Claude Code, ask the agent to dispatch one subagent per manifest row. Each subagent independently reads `prompts/ae_extraction_prompt_v1.md` and its own article's `inputs/text/{StudyID}.txt`, then returns the two-part `{data, rationale}` JSON contract defined in `observational_studies_system_design.md` §2 — no prose, no markdown fences. The orchestrating agent should spot-verify high-stakes claims (deaths, hospitalizations, other safety events) against the source text before checkpointing, then write `raw_responses/{StudyID}_request.json` (provenance) and `raw_responses/{StudyID}_response.json` (parsed output) per article. Articles that turn out not to be primary observational studies (reviews, non-clinical pieces) get a `raw_responses/{StudyID}_excluded.txt` instead, with a reason, so they aren't re-litigated on a future run.
4. **Merge and validate:**
   ```
   C:/Users/jeanv/miniforge3/python.exe aedemographics_extraction/scripts/merge_validate.py
   ```
   Reads every `raw_responses/*_response.json`, runs the full validation gate (type/enum checks, `SafetyReported`/`AnyAEReported`/`WorstSeverity` gate-consistency rules, provenance completeness — design doc §8), and writes `outputs/validation_report.txt`. Any validation failure **blocks** the merge — no CSVs are (re)written, so a bad run can never silently overwrite a good `outputs/` directory. On a clean pass, `articles.csv`, `ae_events.csv`, `human_review_queue.csv`, and `rationale_log.md` are all (re)written.

   `--raw-dir` and `--out-dir` (default `raw_responses/` and `outputs/`) can point at alternate directories to validate a fixture or trial set without touching the real corpus.

### Current status

39 primary observational articles extracted and validated (of 48 source PDFs → 3 duplicates removed → 9 excluded as non-primary/review articles), yielding 130 AE/challenging-experience events, 44 of which are flagged `SeverityIndeterminate=Y` in `human_review_queue.csv` for manual review. One non-blocking design warning is currently open — `Faillace 1970`'s `IsObservational=N` classification is a borderline call (see `outputs/validation_report.txt`) worth a second look before publication.

### Adding a new article

1. Drop the PDF into `inputs/pdfs/` and run `preprocess_pdfs.py`.
2. Fill in `citation` and `year` for the new row in `inputs/manifest.csv`.
3. Dispatch a subagent for that article (see step 3 above) and checkpoint its `_request.json` / `_response.json`.
4. Re-run `merge_validate.py`.

## Adding a new condition

1. Populate `scripts/_config_<condition>.py`: add one entry per study to `EFFECT_SIZE_EXTRACTIONS`, `CONVERSION_RULES`, and `TIER2_RATINGS`.
2. Place the raw Excel file at `data/<Condition>_Dataset.xlsx`.
3. Add the condition to `CONDITION_META` and `AVAILABLE_CONDITIONS` in `scripts/descriptive_analyses.py`.
4. Add the condition to the `CONDITIONS` list in `run_pipeline.py`.
5. Run `run_pipeline.py` — it picks up the new condition automatically.

## Codebook conventions

- `.` in the raw Excel = "not reported" → NaN.
- Binary columns: 0 = No, 1 = Yes, 3 = "Does not apply", NaN = not reported.
- `BINARY_COLS` in `_lib.py` lists every column where 3 means "Does not apply"; continuous columns (e.g., `Followup in months`) are excluded because 3 = 3 months there.
- Adding a new study requires a matching entry in `EFFECT_SIZE_EXTRACTIONS` and `CONVERSION_RULES` in the relevant `_config_<condition>.py`; missing entries raise `KeyError`.
- Tier 1 conversion priority: Cohen's d / Hedges' g > partial η² > F/t/χ² with df > OR/RR > two-group proportions > single proportions > narrative-only.
- The Smoking dataset uses `Retention` (not `Retention (%)`) and `StudyDesignType` (not `Study Design Type`); `_lib.py:clean()` normalizes these automatically.

## Reproducibility statement

Published results were generated with Python 3.12.12 (miniforge3) on Windows 11 (build 10.0.26200), using the exact package versions pinned in `requirements-lock.txt`. Installing those versions and running `run_pipeline.py` should reproduce every table and figure, modulo OS-level font rendering in the `.docx` outputs.

## License

MIT — see [LICENSE](LICENSE).
