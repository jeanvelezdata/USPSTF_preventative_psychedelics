"""Reproduce all outputs from raw data files in one command.

Usage:
    python run_pipeline.py

Steps executed (per available condition):
    1. clean_dataset.py --condition <c>   -> data/<C>_Dataset_Cleaned.xlsx
    2. tier1_hedges_g.py --condition <c>  -> tables/<C>_Tier1_HedgesG.xlsx
                                             figures/<C>_Tier1_ForestPlot.png
    3. descriptive_analyses.py            -> tables/Alcohol_Descriptive_Analyses.docx
                                            (alcohol-only; full combined tables in Task 7)

Conditions that lack a populated config or raw data file are skipped with a
printed warning rather than aborting the pipeline.
"""

import subprocess
import sys
from pathlib import Path

PYTHON  = sys.executable
SCRIPTS = Path(__file__).parent / 'scripts'

CONDITIONS = ['alcohol', 'smoking', 'opioid']


def run(script: str, *args: str) -> bool:
    """Run a script with optional args. Return True on success, False on failure."""
    cmd = [PYTHON, str(SCRIPTS / script)] + list(args)
    label = ' '.join(Path(c).name if i == 1 else c for i, c in enumerate(cmd))
    print(f'\n=== {label} ===', flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f'  WARNING: {script} exited with code {result.returncode} — skipping.', flush=True)
        return False
    return True


# ── Per-condition steps ───────────────────────────────────────────────────────
for condition in CONDITIONS:
    ok = run('clean_dataset.py', '--condition', condition)
    if ok:
        run('tier1_hedges_g.py', '--condition', condition)

# ── Alcohol-only descriptive tables (Task 7 will generalise this) ─────────────
print('\n=== descriptive_analyses.py ===', flush=True)
subprocess.run([PYTHON, str(SCRIPTS / 'descriptive_analyses.py')])

print('\nDone. All available outputs written.', flush=True)
