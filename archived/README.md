# archived/

Historical material. **Nothing here is needed to reproduce the manuscript**, and
none of the scripts here run in place — they were written against the repository
layout as it stood before this reorganization and reference paths that have since
moved. They are kept because they are the evidence trail for how the current
dataset was built and validated, not because they are runnable.

The live pipeline is described in the root [README.md](../README.md).

## baselines/

Snapshot of every analysis artifact as it stood immediately *before* the
automated re-extraction: nine PNGs, four DOCX, six XLSX, plus `BASELINE.txt`
recording the source commit. Captured by `migration/capture_baseline.py`, and the
comparison target for `migration/visual_regression.py`.

These are stale by construction. The current figures and tables in
[figures/](../figures/) and [tables/](../tables/) supersede them.

## migration/

The one-time transition from the frozen hand extraction
(`data/<Condition>_Dataset.xlsx`) to the automated master
(`clinical_trials/outputs/clinical_master.csv`).

| File | What it was |
|---|---|
| `clinical_old_new_mapping.md` | The contract making the two extractions comparable, and the procedure for turning the comparison into evidence that the redesign did not change the evidence base. |
| `capture_baseline.py` | Copied the pre-rebuild artifacts into `baselines/`. Ran once, before the first extraction. |
| `old_new_compare.py` | Deterministic per-study, per-field agreement check between the frozen files and the new master. |
| `old_new_comparison_report.md` | Its output — the disagreement table that was then adjudicated. |
| `visual_regression.py` | Checked rebuilt figures against `baselines/`, separating data changes from styling regressions. |
| `visual_regression_report.txt` | Its output. |
| `reconciliation_report.txt` | Corpus reconciliation output from an earlier run of the (still live) `clinical_trials/scripts/reconcile_manifest.py`. |

The adjudication that resolved `old_new_comparison_report.md` is **not** here. It
lives at [clinical_adjudication.md](../clinical_adjudication.md) in the root and is
still load-bearing: `clinical_trials/scripts/apply_adjudication.py` parses it on
every merge, so the human corrections are re-applied rather than baked into the
data. It was named `output.md` until this reorganization.

## manuscript/

| File | What it was |
|---|---|
| `Draft Text and Outline_USPS.docx` | The Word draft, superseded by [USPSTF Manuscript and Outline_USPS.md](../USPSTF%20Manuscript%20and%20Outline_USPS.md). |
| `corrections.md` | Line-by-line plan for removing Prior 2014 from the manuscript. Fully applied. |
| `Aggregate Data.docx` | Early hand-assembled aggregate table, superseded by the generated tables. |

## prompts/

| File | What it was |
|---|---|
| `opus_extraction_prompt.md` | The original single-prompt extraction spec, superseded by the versioned prompts in `clinical_trials/prompts/` and `observational_studies/prompts/`. |
| `clinical_pipeline_design_prompt.md` | The brief that produced `clinical_system_design.md` and `observational_studies_system_design.md`. |
