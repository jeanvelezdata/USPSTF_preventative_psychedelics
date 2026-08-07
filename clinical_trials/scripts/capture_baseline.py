"""Copy the currently committed analysis artifacts into baselines/ (design §9.1).

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/capture_baseline.py

This MUST run before the first extraction subagent is dispatched. After
re-extraction the old artifacts are unreproducible, because the frozen
data/<Condition>_Dataset.xlsx files alone no longer regenerate them once
clean_dataset.py points at clinical_master.csv.

Copies the nine PNGs, four DOCX and six XLSX named in §9.1 into
clinical_trials/baselines/, and writes BASELINE.txt recording the source
commit SHA, whether the working tree was dirty, and a SHA-256 per file.
visual_regression.py reads BASELINE.txt to know what it is comparing against.

Refuses to overwrite an existing baseline unless --force is passed: a
baseline captured after re-extraction is worthless, and silently replacing
one is the way that happens.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_BASE = Path(__file__).parent.parent          # clinical_trials/
_ROOT = _BASE.parent                          # repo root
BASELINE_DIR = _BASE / 'baselines'

# §9.1 inventory: 9 PNG + 4 DOCX + 6 XLSX, repo-relative.
BASELINE_ARTIFACTS: list[str] = [
    'figures/Alcohol_MethQual_BarPlot.png',
    'figures/Alcohol_Tier1_ForestPlot.png',
    'figures/Smoking_Tier1_ForestPlot.png',
    'figures/Opioid_Tier1_ForestPlot.png',
    'figures/Alcohol_Tier2_CatPlot.png',
    'figures/Smoking_Tier2_CatPlot.png',
    'figures/Opioid_Tier2_CatPlot.png',
    'figures/Unified_Tier1_ForestPlot.png',
    'figures/Unified_Tier2_CatPlot.png',
    'tables/Alcohol_Descriptive_Analyses.docx',
    'tables/Smoking_Descriptive_Analyses.docx',
    'tables/Opioid_Descriptive_Analyses.docx',
    'tables/Aggregate Data.docx',
    'tables/Alcohol_Tier1_HedgesG.xlsx',
    'tables/Smoking_Tier1_HedgesG.xlsx',
    'tables/Opioid_Tier1_HedgesG.xlsx',
    'tables/Alcohol_Tier2_Qualitative.xlsx',
    'tables/Smoking_Tier2_Qualitative.xlsx',
    'tables/Opioid_Tier2_Qualitative.xlsx',
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    try:
        out = subprocess.run(['git', *args], cwd=_ROOT, capture_output=True, text=True)
        return out.stdout.strip() if out.returncode == 0 else ''
    except FileNotFoundError:
        return ''


def main() -> None:
    parser = argparse.ArgumentParser(description='Capture the pre-extraction artifact baseline.')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite an existing baseline. A baseline captured after '
                             're-extraction is worthless; only pass this deliberately.')
    args = parser.parse_args()

    marker = BASELINE_DIR / 'BASELINE.txt'
    if marker.exists() and not args.force:
        print(f"ERROR: a baseline already exists at {marker}.\n"
              f"       Re-capturing after extraction would compare the rebuild against itself.\n"
              f"       Pass --force only if you are certain the current artifacts are still "
              f"pre-extraction.", file=sys.stderr)
        sys.exit(1)

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    sha = git('rev-parse', 'HEAD') or '(no git metadata available)'
    dirty_paths = [ln for ln in git('status', '--porcelain').splitlines() if ln.strip()]

    lines = [
        'Clinical-Trial Extraction — Artifact Baseline',
        '=' * 44,
        '',
        f'Captured (UTC):  {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
        f'Source commit:   {sha}',
        f'Working tree:    {"DIRTY" if dirty_paths else "clean"}',
    ]
    if dirty_paths:
        lines.append('')
        lines.append('  Uncommitted paths at capture time (baseline reflects the working tree,')
        lines.append('  not the commit above, for any path listed here):')
        for p in dirty_paths:
            lines.append(f'    {p}')
    lines += ['', 'Artifacts (SHA-256 of the baseline copy):', '']

    missing: list[str] = []
    for rel in BASELINE_ARTIFACTS:
        src = _ROOT / rel
        if not src.exists():
            missing.append(rel)
            lines.append(f'  MISSING  {rel}')
            continue
        dest = BASELINE_DIR / Path(rel).name
        shutil.copy2(src, dest)
        lines.append(f'  {sha256(dest)}  {rel}')
        print(f'  copied {rel}')

    lines.append('')
    lines.append(f'Copied {len(BASELINE_ARTIFACTS) - len(missing)} of {len(BASELINE_ARTIFACTS)} artifacts.')
    marker.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f"\nBaseline written: {marker}")
    if missing:
        print(f"WARNING — {len(missing)} artifact(s) absent and not baselined:", file=sys.stderr)
        for rel in missing:
            print(f"  - {rel}", file=sys.stderr)
        print("visual_regression.py will report these as unbaselined rather than as regressions.",
              file=sys.stderr)


if __name__ == '__main__':
    main()
