"""Pre-rebuild gate — design §8 checks 11 and 13.

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/gate_rebuild.py

Run by run_pipeline.py before any figure or table is rebuilt. These two checks
live here rather than in merge_validate.py because both need the *ratified*
config, which merge_validate.py only proposes — blocking the merge on them
would deadlock.

Check 11 — config-key existence. Every *eligible* study has entries in
EFFECT_SIZE_EXTRACTIONS and CONVERSION_RULES, and every Tier-1-excluded
eligible study has a TIER2_RATINGS entry. Reported as a named list of
(surname, year) tuples, never as the bare KeyError that
extract_effect_size_fields() raises today.

Check 13 — plot-frame conformance. build_results() on each condition's frame
yields exactly the §6.3 columns; confidence is one of clean/approx/excluded;
substance is a SUBSTANCE_COLS key or 'Unknown'; study matches "Surname Year";
and excluded / null-g rows are still present rather than dropped — the plot
filters them, the results tables keep them for traceability.

The frame is built here from clinical_master.csv directly rather than read from
data/<Condition>_Dataset_Cleaned.xlsx, so this gate does not depend on the very
rebuild it is gating.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).parent
_BASE    = _SCRIPTS.parent
_ROOT    = _BASE.parent
sys.path.insert(0, str(_ROOT / 'scripts'))

import _lib as lib  # noqa: E402  (repo-root analysis lib)

MASTER = _BASE / 'outputs' / 'clinical_master.csv'
REPORT = _BASE / 'outputs' / 'rebuild_gate_report.txt'

CONDITIONS = {'alcohol': 'Alcohol', 'smoking': 'Smoking', 'opioid': 'Opioid'}

# design §6.3 — the plot scripts' input contract.
PLOT_FRAME_COLUMNS = [
    'study', 'Year', 'N', 'substance', 'metric', 'measure', 'method',
    'confidence', 'note', 'd', 'g', 'var_g', 'se_g', 'ci_lo', 'ci_hi',
]

_STUDY_LABEL = re.compile(r'^.+ \d{4}$')


def condition_frame(condition: str, label: str) -> pd.DataFrame | None:
    df = pd.read_csv(MASTER)
    df = df[df['Condition'] == label].reset_index(drop=True)
    return lib.analytic_frame(df) if len(df) else None


def check_config_keys(condition: str, df: pd.DataFrame) -> list[str]:
    """Check 11."""
    cfg = importlib.import_module(f'_config_{condition}')
    issues: list[str] = []

    keys = [(lib.first_author_surname(r['Citation/Title']), int(r['Year']))
            for _, r in df.iterrows()]

    missing_extraction = [k for k in keys if k not in cfg.EFFECT_SIZE_EXTRACTIONS]
    missing_rule       = [k for k in keys if k not in cfg.CONVERSION_RULES]
    if missing_extraction:
        issues.append(f'{len(missing_extraction)} eligible stud(ies) have no '
                      f'EFFECT_SIZE_EXTRACTIONS entry: {sorted(missing_extraction)}')
    if missing_rule:
        issues.append(f'{len(missing_rule)} eligible stud(ies) have no CONVERSION_RULES '
                      f'entry: {sorted(missing_rule)}')

    tier2 = getattr(cfg, 'TIER2_RATINGS', {})
    excluded = [k for k in keys
                if cfg.CONVERSION_RULES.get(k, {}).get('confidence') == 'excluded']
    missing_tier2 = [k for k in excluded if k not in tier2]
    if missing_tier2:
        issues.append(f'{len(missing_tier2)} Tier-1-excluded eligible stud(ies) have no '
                      f'TIER2_RATINGS entry: {sorted(missing_tier2)}')
    return issues


def check_plot_frame(condition: str, df: pd.DataFrame) -> list[str]:
    """Check 13."""
    cfg = importlib.import_module(f'_config_{condition}')
    issues: list[str] = []
    try:
        cleaned = lib.clean(df, cfg)
    except KeyError as e:
        return [f'lib.clean() raised KeyError before the plot frame could be built: {e}']

    results = lib.build_results(cleaned, cfg.CONVERSION_RULES)

    if list(results.columns) != PLOT_FRAME_COLUMNS:
        issues.append(f'build_results() columns {list(results.columns)} do not match the '
                      f'§6.3 contract {PLOT_FRAME_COLUMNS}')
        return issues

    if len(results) != len(cleaned):
        issues.append(f'build_results() returned {len(results)} rows for {len(cleaned)} '
                      f'studies — excluded and null-g rows must be produced, not dropped')

    bad_conf = sorted(set(results['confidence'].dropna()) - set(lib_confidences()))
    if bad_conf:
        issues.append(f'confidence values outside {{clean, approx, excluded}}: {bad_conf}')

    allowed_sub = set(lib.SUBSTANCE_COLS) | {'Unknown'}
    bad_sub = sorted(set(results['substance'].dropna()) - allowed_sub)
    if bad_sub:
        issues.append(f'substance values outside SUBSTANCE_COLS u {{Unknown}}: {bad_sub}')

    bad_label = [s for s in results['study'] if not _STUDY_LABEL.match(str(s))]
    if bad_label:
        issues.append(f'study labels not matching "Surname Year": {bad_label}')

    return issues


def lib_confidences() -> tuple[str, ...]:
    return ('clean', 'approx', 'excluded')


def main() -> None:
    if not MASTER.exists():
        print(f'ERROR: {MASTER} not found. Run merge_validate.py first.', file=sys.stderr)
        sys.exit(1)

    all_issues: list[str] = []
    lines = ['Clinical-Trial Rebuild Gate — design §8 checks 11 and 13', '=' * 56, '']

    for condition, label in CONDITIONS.items():
        df = condition_frame(condition, label)
        if df is None or df.empty:
            lines.append(f'{label}: no eligible rows in the master — skipped.')
            continue
        issues = check_config_keys(condition, df) + check_plot_frame(condition, df)
        lines.append(f'{label}: {len(df)} eligible stud(ies), '
                     f'{len(issues)} issue(s).')
        for issue in issues:
            lines.append(f'  - {issue}')
            all_issues.append(f'[{label}] {issue}')

    lines.append('')
    lines.append('GATE FAILED — rebuild blocked.' if all_issues else 'GATE PASSED.')
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print('\n'.join(lines))
    print(f'\nReport written: {REPORT}')
    if all_issues:
        sys.exit(1)


if __name__ == '__main__':
    main()
