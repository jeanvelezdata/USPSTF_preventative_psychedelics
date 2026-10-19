# USPSTF Evidentiary-Gap Analysis: Psychedelic Interventions for Substance Use Disorders

Systematic evidence review of psychedelic-assisted therapies (psilocybin, LSD, MDMA, ketamine, ayahuasca, ibogaine, mescaline, and others) as treatments for **alcohol use disorder**, **tobacco/nicotine use disorder**, and **opioid use disorder**. The goal is to characterize the existing evidence against USPSTF-style evidentiary standards, identify methodological and coverage gaps, and produce standardized effect sizes (Hedges' g) where that conversion is defensible.

The manuscript is [USPSTF Manuscript and Outline_USPS.md](USPSTF%20Manuscript%20and%20Outline_USPS.md). This repo generates every table and figure in it; the prose is written by the human author.

## Current status

| Condition | Eligible trials | Year range | Tier 1 convertible | Tier 2 (qualitative) |
|---|---|---|---|---|
| Alcohol | 32 | 1958–2025 | 14 | 18 |
| Smoking | 4  | 2014–2026 | 1  | 3  |
| Opioid  | 6  | 1973–2016 | 1  | 5  |

Plus **33 observational studies** (103 adverse-event / challenging-experience records) contributing the safety and net-benefit picture. Total corpus behind Table S1: **75 studies**.

"Tier 1 convertible" means a clean or approximate Hedges' g could be computed from the reported statistics; everything else is classified qualitatively in Tier 2. Random-effects pooling across all Tier 1 estimates gives **g = 0.46 (95% CI 0.22–0.70), I² = 67%** — see [tables/Tier1_PooledMeta.txt](tables/Tier1_PooledMeta.txt).

## Stack

- Python 3.12, with pandas, numpy, openpyxl, python-docx, matplotlib, PyMuPDF
- Python runtime on this machine: `C:/Users/jeanv/miniforge3/python.exe` — use this path explicitly; the `python` / `py` shims resolve to the Microsoft Store stub and do nothing

```
C:/Users/jeanv/miniforge3/python.exe -m pip install -r requirements.txt
```

To reproduce published results, install the pinned versions instead:

```
C:/Users/jeanv/miniforge3/python.exe -m pip install -r requirements-lock.txt
```

## Reproducing the manuscript's tables and figures

One command from the project root:

```
C:/Users/jeanv/miniforge3/python.exe run_pipeline.py
```

It refuses to run unless `clinical_trials/outputs/clinical_master.csv` exists, its validation gate last **passed**, and the master has not been touched since — rebuilding figures from an unvalidated master is the failure mode it exists to prevent. It then runs, per condition (`alcohol`, `smoking`, `opioid`):

`clean_dataset.py` → `tier1_hedges_g.py` → `tier2_qualitative.py` → `descriptive_analyses.py`

and then, once across conditions: `methqual_bar_plot.py`, `unified_forest_plot.py`, `unified_cat_plot.py`, `table3_gapmap.py`, `table4_ae_safety.py`, `pooled_meta.py`, `table_s1_references.py`.

A condition with no rows in the master or an unpopulated config is skipped with a warning rather than aborting the run.

> If a step fails with `PermissionError` on a `.docx`, the file is open in Word (or locked by OneDrive sync). Close it and re-run.

Individual stages accept `--condition alcohol|smoking|opioid`:

```
C:/Users/jeanv/miniforge3/python.exe scripts/clean_dataset.py --condition alcohol
```

## Layout

```
USPSTF/
├── USPSTF Manuscript and Outline_USPS.md   # the manuscript
├── run_pipeline.py                         # rebuilds every table and figure
├── clinical_adjudication.md                # human adjudication, re-applied on every merge
│
├── clinical_trials/          # extraction pipeline: clinical trials  -> clinical_master.csv
├── observational_studies/    # extraction pipeline: observational    -> articles.csv
├── scripts/                  # analysis: master tables -> tables/ + figures/
├── data/                     # frozen hand extraction + cleaned analysis frames
├── tables/                   # generated manuscript tables
├── figures/                  # generated manuscript figures
└── archived/                 # historical material, not needed to reproduce
```

The two extraction pipelines share a shape: `inputs/` (manifest + article text) → `prompts/` (pinned prompt + rubric) → `raw_responses/` (per-article request/response JSON) → `scripts/merge_validate.py` → `outputs/`.

### scripts/ — analysis

| Script | Produces |
|---|---|
| `_lib.py`, `_config_{alcohol,smoking,opioid}.py` | Shared helpers; per-condition `EFFECT_SIZE_EXTRACTIONS`, `CONVERSION_RULES`, `TIER2_RATINGS`. Not run directly. |
| `clean_dataset.py` | `data/<C>_Dataset_Cleaned.xlsx` |
| `tier1_hedges_g.py` | `tables/<C>_Tier1_HedgesG.xlsx`, `figures/<C>_Tier1_ForestPlot.png` |
| `tier2_qualitative.py` | `tables/<C>_Tier2_Qualitative.xlsx`, `figures/<C>_Tier2_CatPlot.png` |
| `descriptive_analyses.py` | `tables/<C>_Descriptive_Analyses.docx` (five tables) |
| `unified_forest_plot.py` | `figures/Unified_Tier1_ForestPlot.png`, `figures/Unified_Tier1_ForestPlot.pdf` |
| `unified_cat_plot.py` | `figures/Unified_Tier2_CatPlot.png`, `figures/Unified_Tier2_CatPlot.pdf` |
| `methqual_bar_plot.py` | `figures/Alcohol_MethQual_BarPlot.png` |
| `table3_gapmap.py` | `tables/Table3_USPSTF_GapMap_bySubstance.docx` |
| `table4_ae_safety.py` | `tables/Table4_AE_Safety_Summary.docx` |
| `pooled_meta.py` | `tables/Tier1_PooledMeta.txt` |
| `table_s1_references.py` | `tables/TableS1_References.docx` |

### data/

`<Condition>_Dataset_Cleaned.xlsx` are analysis frames, regenerated by `clean_dataset.py` from `clinical_master.csv`.

`<Condition>_Dataset.xlsx` are the **frozen original hand extraction**. They are no longer the analysis input, but they are not archived: `clinical_trials/scripts/reconcile_manifest.py` still checks the live corpus against them so that a study which was in the evidence base cannot silently vanish. Treat them as read-only.

## Reproducing the extraction itself

Only needed if you are adding articles or re-running extraction; the committed `outputs/` are sufficient to rebuild the manuscript.

**Source PDFs are not tracked in git** (~150 MB of publisher files). They remain on disk under `clinical_trials/inputs/pdfs/` and `observational_studies/inputs/pdfs/`, and the reconciliation gate blocks if a manifest row's PDF is missing — so extraction can only be re-run on a machine that has them. The converted article text in `inputs/text/` *is* tracked, so everything downstream of PDF conversion is reproducible from a clean clone.

**Clinical trials** (`clinical_trials/`, spec: [clinical_system_design.md](clinical_system_design.md), fields: [clinical_codebook.md](clinical_codebook.md)):

1. `scripts/convert_pdfs.py` — PDF → Markdown, one file per article in `inputs/text/`.
2. `scripts/reconcile_manifest.py` — derives StudyIDs, reconciles the corpus against the frozen files.
3. `scripts/make_requests.py` — writes the immutable `raw_responses/{StudyID}_request.json` provenance record (pinned prompt/rubric version, text SHA-256, model, sampling parameters).
4. **Dispatch.** LLM-driven, not a script: one subagent per manifest row, each reading `prompts/clinical_extraction_prompt_v1_1.md` and its own `inputs/text/{StudyID}.md`, returning the two-part `{data, rationale}` JSON contract. Checkpoint each as `raw_responses/{StudyID}_response.json`.
5. `scripts/merge_validate.py` — merges, re-applies `clinical_adjudication.md`, runs the validation gate, writes `outputs/`.
6. `scripts/apply_config_proposals.py` — applies ratified effect-size proposals into `scripts/_config_<condition>.py`.

**Observational studies** (`observational_studies/`, spec: [observational_studies_system_design.md](observational_studies_system_design.md), fields: [observational_codebook.md](observational_codebook.md)): same shape, with `scripts/preprocess_pdfs.py` (PyMuPDF, Tesseract OCR fallback) in place of steps 1–3, and human curation decisions recorded in `overrides.json`.

A validation failure **blocks** the merge — no CSVs are rewritten, so a bad run cannot overwrite a good `outputs/`.

**Never hand-edit `outputs/`, and never edit a raw response JSON.** Those are the verbatim extraction record. Every human decision that changes the published tables goes in `clinical_adjudication.md` (clinical) or `overrides.json` (observational), with a reason, so `outputs/` stays reproducible from `raw_responses/` plus those two files alone.

## Codebook conventions

- `.` in the raw Excel = "not reported" → NaN.
- Binary columns: 0 = No, 1 = Yes, 3 = "Does not apply", NaN = not reported.
- `BINARY_COLS` in `scripts/_lib.py` lists every column where 3 means "Does not apply"; continuous columns (e.g. `Followup in months`) are excluded because 3 = 3 months there.
- Missing/not-reported counts as **not met** in the USPSTF gap tables (strict interpretation).
- Adding a study requires matching entries in `EFFECT_SIZE_EXTRACTIONS` and `CONVERSION_RULES` in the relevant `_config_<condition>.py`; missing entries raise `KeyError`.
- Tier 1 conversion priority: Cohen's d / Hedges' g > partial η² > F/t/χ² with df > OR/RR > two-group proportions > single proportions > narrative-only.

## Adding a new condition

1. Populate `scripts/_config_<condition>.py` with one entry per study in `EFFECT_SIZE_EXTRACTIONS`, `CONVERSION_RULES`, and `TIER2_RATINGS`.
2. Add the condition to `CONDITION_META` and `AVAILABLE_CONDITIONS` in `scripts/descriptive_analyses.py`.
3. Add it to `CONDITIONS` in `run_pipeline.py`.

## Reproducibility statement

Published results were generated with Python 3.12.12 (miniforge3) on Windows 11 (build 10.0.26200) using the versions pinned in `requirements-lock.txt`. Installing those versions and running `run_pipeline.py` reproduces every table and figure, modulo OS-level font rendering in the `.docx` outputs.

## License

MIT — see [LICENSE](LICENSE).
