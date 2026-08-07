"""Reproduce all outputs from the clinical master table in one command.

Usage:
    python run_pipeline.py

Preconditions (checked before anything runs):
    0. clinical_trials/outputs/clinical_master.csv exists, its validation gate
       last passed, and gate_rebuild.py's config-key and plot-frame checks pass.

Steps executed (per available condition):
    1. clean_dataset.py --condition <c>          -> data/<C>_Dataset_Cleaned.xlsx
    2. tier1_hedges_g.py --condition <c>         -> tables/<C>_Tier1_HedgesG.xlsx
                                                    figures/<C>_Tier1_ForestPlot.png
    3. tier2_qualitative.py --condition <c>      -> tables/<C>_Tier2_Qualitative.xlsx
                                                    figures/<C>_Tier2_CatPlot.png
    4. descriptive_analyses.py --condition <c>   -> tables/<C>_Descriptive_Analyses.docx

Then once, for alcohol:
    5. methqual_bar_plot.py                      -> figures/Alcohol_MethQual_BarPlot.png

methqual_bar_plot.py is in the sequence because its percentages are now
computed from the cleaned frame rather than hardcoded; leaving it out is what
let the figure go stale against Table 2 in the first place.

Conditions that lack a populated config or have no rows in the master are
skipped with a printed warning rather than aborting the pipeline.
"""

import subprocess
import sys
from pathlib import Path

PYTHON  = sys.executable
_BASE   = Path(__file__).parent
SCRIPTS = _BASE / 'scripts'

CONDITIONS = ['alcohol', 'smoking', 'opioid']

MASTER      = _BASE / 'clinical_trials' / 'outputs' / 'clinical_master.csv'
VALIDATION  = _BASE / 'clinical_trials' / 'outputs' / 'validation_report.txt'
GATE_SCRIPT = _BASE / 'clinical_trials' / 'scripts' / 'gate_rebuild.py'


def run(script: Path, *args: str) -> bool:
    """Run a script with optional args. Return True on success."""
    cmd = [PYTHON, str(script)] + list(args)
    print(f"\n=== {script.name} {' '.join(args)} ===", flush=True)
    if subprocess.run(cmd).returncode != 0:
        print(f'  WARNING: {script.name} exited non-zero — skipping.', flush=True)
        return False
    return True


def check_master_fresh() -> None:
    """Fail fast rather than rebuilding figures from a stale or invalid master."""
    if not MASTER.exists():
        sys.exit(f'ERROR: {MASTER} not found.\n'
                 f'       Build it with clinical_trials/scripts/merge_validate.py.')
    if not VALIDATION.exists():
        sys.exit(f'ERROR: {VALIDATION} not found — the validation gate has never run.\n'
                 f'       Run clinical_trials/scripts/merge_validate.py.')
    report = VALIDATION.read_text(encoding='utf-8')
    if 'VALIDATION PASSED' not in report:
        sys.exit(f'ERROR: the last validation gate run FAILED. See {VALIDATION}.\n'
                 f'       Rebuilding from a master that failed the gate would publish\n'
                 f'       a partially-invalid dataset.')
    if VALIDATION.stat().st_mtime < MASTER.stat().st_mtime:
        sys.exit(f'ERROR: {MASTER.name} is newer than {VALIDATION.name} — it changed after\n'
                 f'       the gate last passed. Re-run merge_validate.py.')


check_master_fresh()
if not run(GATE_SCRIPT):
    sys.exit('ERROR: gate_rebuild.py failed (design §8 checks 11 and 13). '
             'Rebuild aborted.')

for condition in CONDITIONS:
    if run(SCRIPTS / 'clean_dataset.py', '--condition', condition):
        if run(SCRIPTS / 'tier1_hedges_g.py', '--condition', condition):
            run(SCRIPTS / 'tier2_qualitative.py', '--condition', condition)
        run(SCRIPTS / 'descriptive_analyses.py', '--condition', condition)

run(SCRIPTS / 'methqual_bar_plot.py')

print('\nDone. All available outputs written.', flush=True)
print('Next gate: clinical_trials/scripts/visual_regression.py, then old_new_compare.py.',
      flush=True)
