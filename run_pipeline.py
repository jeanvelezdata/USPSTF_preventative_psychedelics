"""Reproduce all outputs from the raw data file in one command.

Usage:
    python run_pipeline.py

Steps executed:
    1. clean_alcohol_dataset.py  -> data/Alcohol_Dataset_Cleaned.xlsx
    2. descriptive_analyses.py   -> tables/Alcohol_Descriptive_Analyses.docx
    3. tier1_hedges_g.py         -> tables/Alcohol_Tier1_HedgesG.xlsx
                                    figures/Alcohol_Tier1_ForestPlot.png
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent / 'scripts'
PIPELINE = [
    'clean_alcohol_dataset.py',
    'descriptive_analyses.py',
    'tier1_hedges_g.py',
]

for script in PIPELINE:
    print(f'\n=== {script} ===')
    subprocess.run([sys.executable, str(SCRIPTS / script)], check=True)

print('\nDone. All outputs written.')
