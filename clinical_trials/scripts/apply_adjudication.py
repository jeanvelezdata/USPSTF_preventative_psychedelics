"""Apply the human adjudication in output.md back into clinical_master.csv.

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/apply_adjudication.py --dry-run
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/apply_adjudication.py

output.md is the authority. This script parses it rather than carrying a
hand-copied list, so re-running after the adjudication is revised picks the
revision up instead of silently applying stale values.

Only rows decided `Old` are written. The other three decisions are no-ops by
definition: `New` and `Equivalent` mean the master already holds a defensible
value, and `Unclear` means the source text does not resolve the disagreement —
overwriting on `Unclear` would substitute one unsupported value for another.
Those are logged as skips so the residue stays visible.

One class of `Old` win is deliberately NOT applied: `Age_Median`. Old carries a
precise mean (51) where the master carries the bracket the schema defines
(`50+`). Nothing downstream reads the precise value —
descriptive_analyses.py counts studies per bracket and reports coverage — so
writing 51 back would fail the closed-enum validator to buy a precision no
analysis consumes. These are logged as `skipped-schema`.

Every write is checked against ARTICLE_VALIDATORS before the file is touched;
a single violation aborts the run with nothing written. The original is copied
to clinical_master.csv.bak, and the per-cell provenance goes to
outputs/adjudication_applied.csv.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).parent
_BASE    = _SCRIPTS.parent
_ROOT    = _BASE.parent
sys.path.insert(0, str(_SCRIPTS))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

import _lib as lib  # noqa: E402

ADJUDICATION = _ROOT / 'output.md'
MASTER_CSV   = _BASE / 'outputs' / 'clinical_master.csv'
MASTER_XLSX  = _BASE / 'outputs' / 'clinical_master.xlsx'
LOG          = _BASE / 'outputs' / 'adjudication_applied.csv'

DECISIONS = ('Old', 'New', 'Equivalent', 'Unclear')

# Rows whose Field label is not a master column.
FIELD_ALIASES = {
    # The adjudication compared the new SafetyReported gate against the old
    # HarmsAssessed binary, so the row is labelled with both names.
    'SafetyReported vs old HarmsAssessed': 'SafetyReported',
}

# Old is coded 1/0; SafetyReported is Y/N.
VALUE_MAPS = {
    'SafetyReported': {'1': 'Y', '1.0': 'Y', '0': 'N', '0.0': 'N'},
}

# Old-wins that are schema artefacts rather than extraction errors.
SKIP_FIELDS = {'Age_Median': 'bracket is what the analysis consumes; '
                             'precise mean is not read anywhere'}

# Rows that are not field-value disagreements at all.
SKIP_ROWS = {('Denson 1970', 'Eligibility (X2)')}


def parse_adjudication(path: Path) -> list[dict]:
    rows = []
    section = None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            section = line[3:].strip()
        if not line.startswith('| '):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) != 6 or cells[4] not in DECISIONS:
            continue
        rows.append({
            'condition': section,
            'study':     cells[0],
            'field':     cells[1],
            'old':       cells[2].strip('`').strip(),
            'new':       cells[3].strip('`').strip(),
            'decision':  cells[4],
            'rationale': cells[5],
        })
    return rows


def target_value(field: str, old: str) -> str:
    """Old's value in the master's own encoding."""
    if old in ('None', ''):
        return lib.NOT_REPORTED
    return VALUE_MAPS.get(field, {}).get(old, old)


def apply_to_frame(df: pd.DataFrame,
                   rows: list[dict] | None = None) -> tuple[list[dict], list[dict], list[str]]:
    """Write every `Old` decision into `df` in place.

    Returns (applied, skipped, errors). `df` is left untouched when errors is
    non-empty, so a caller can abort on a stale or malformed adjudication
    rather than write a half-corrected master.

    merge_validate.py calls this on the freshly merged frame so that
    re-running the merge does not silently revert the human decisions in
    output.md. That makes the adjudication a durable layer on top of the raw
    extraction rather than a one-shot edit.
    """
    if rows is None:
        rows = parse_adjudication(ADJUDICATION) if ADJUDICATION.exists() else []

    index = {sid: i for i, sid in enumerate(df['StudyID'])}
    applied, skipped, errors = [], [], []
    staged = []

    for r in rows:
        if r['decision'] != 'Old':
            continue
        study, field = r['study'], r['field']
        if (study, field) in SKIP_ROWS:
            skipped.append({**r, 'reason': 'not a field-value disagreement'})
            continue
        if field in SKIP_FIELDS:
            skipped.append({**r, 'reason': f'schema artefact — {SKIP_FIELDS[field]}'})
            continue

        column = FIELD_ALIASES.get(field, field)
        if column not in df.columns:
            errors.append(f'{study}: no master column for field {field!r}')
            continue
        if study not in index:
            errors.append(f'{study}: no master row with this StudyID')
            continue

        value = target_value(column, r['old'])
        validator = lib.ARTICLE_VALIDATORS.get(column)
        if validator and not validator(value):
            errors.append(f'{study}.{column}: {value!r} fails its validator')
            continue

        i = index[study]
        before = str(df.at[i, column])
        if before == value:
            skipped.append({**r, 'reason': "master already holds Old's value"})
            continue
        staged.append((i, column, value))
        applied.append({'StudyID': study, 'Condition': r['condition'], 'column': column,
                        'from': before, 'to': value, 'rationale': r['rationale']})

    if errors:
        return [], skipped, errors
    for i, column, value in staged:
        df.at[i, column] = value
    return applied, skipped, errors


def main() -> None:
    ap = argparse.ArgumentParser(description='Apply output.md adjudication to the master.')
    ap.add_argument('--dry-run', action='store_true', help='Report without writing.')
    args = ap.parse_args()

    if not ADJUDICATION.exists():
        sys.exit(f'FATAL: {ADJUDICATION} not found.')

    rows = parse_adjudication(ADJUDICATION)
    print(f'Parsed {len(rows)} adjudicated rows from {ADJUDICATION.name}.')
    by_decision = pd.Series([r['decision'] for r in rows]).value_counts()
    print('  ' + '  '.join(f'{k}={v}' for k, v in by_decision.items()))

    df = pd.read_csv(MASTER_CSV, dtype=str, keep_default_na=False)
    applied, skipped, errors = apply_to_frame(df, rows)

    if errors:
        print(f'\nFAIL — {len(errors)} correction(s) could not be applied. Nothing written.')
        for e in errors:
            print(f'  - {e}')
        sys.exit(1)

    print(f'\n{len(applied)} correction(s) {"would be " if args.dry_run else ""}applied; '
          f'{len(skipped)} skipped.')
    by_col = pd.Series([a['column'] for a in applied]).value_counts()
    print('\nBy column:')
    for col, n in by_col.items():
        print(f'  {n:3}  {col}')

    if args.dry_run:
        print('\nDry run — no files written.')
        return

    shutil.copy2(MASTER_CSV, MASTER_CSV.with_suffix('.csv.bak'))
    df.to_csv(MASTER_CSV, index=False, encoding='utf-8')
    df.to_excel(MASTER_XLSX, index=False)

    log = pd.DataFrame(applied)
    log.to_csv(LOG, index=False, encoding='utf-8')

    print(f'\nWrote {MASTER_CSV.name} ({len(df)} rows), {MASTER_XLSX.name}, and {LOG.name}.')
    print(f'Backup at {MASTER_CSV.with_suffix(".csv.bak").name}.')
    print('\nRebuild the artifacts next:')
    print('  C:/Users/jeanv/miniforge3/python.exe run_pipeline.py')


if __name__ == '__main__':
    main()
