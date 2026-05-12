"""Reproduce all outputs from raw data files in one command.

Usage:
    python run_pipeline.py

Steps executed (per available condition):
    1. clean_dataset.py --condition <c>          -> data/<C>_Dataset_Cleaned.xlsx
    2. tier1_hedges_g.py --condition <c>         -> tables/<C>_Tier1_HedgesG.xlsx
                                                    figures/<C>_Tier1_ForestPlot.png
    3. tier2_qualitative.py --condition <c>      -> tables/<C>_Tier2_Qualitative.xlsx
                                                    figures/<C>_Tier2_CatPlot.png
    4. descriptive_analyses.py --condition <c>   -> tables/<C>_Descriptive_Analyses.docx

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


for condition in CONDITIONS:
    ok = run('clean_dataset.py', '--condition', condition)
    if ok:
        tier1_ok = run('tier1_hedges_g.py', '--condition', condition)
        if tier1_ok:
            run('tier2_qualitative.py', '--condition', condition)
        run('descriptive_analyses.py', '--condition', condition)

print('\nDone. All available outputs written.', flush=True)
