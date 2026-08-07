"""Derive StudyIDs, reconcile the corpus against the frozen files (design §1.3).

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/reconcile_manifest.py
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/reconcile_manifest.py --no-rename

Run after convert_pdfs.py and after the citation/year metadata pass. For each
manifest row it derives `surname` (frozen here, never re-derived from model
output), `StudyID` = "{surname} {year}", and `old_row_match` against the frozen
data/<Condition>_Dataset.xlsx; renames each converted text file from its
PDF-stem name to {StudyID}.{ext}; and writes outputs/reconciliation_report.txt.

Blocking dispositions (§1.3) — exit code 1, report still written:

  * a PDF present with no manifest row        (article silently absent)
  * a manifest row with no PDF                (dangling reference)
  * a frozen old row matching no manifest row (data loss; overridable only by
                                               a human-authored expected_missing.csv entry)
  * a duplicate (surname, year) across rows   (the config dicts key on this
                                               tuple and cannot disambiguate)

Warning: a manifest row whose (surname, year) matches no frozen old row —
expected for the four previously dropped alcohol studies. The corpus is a
superset of the frozen files by design.

The report is the input to clinical_old_new_mapping.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).parent
_BASE    = _SCRIPTS.parent
_ROOT    = _BASE.parent


def _load_analysis_lib():
    """Load the repo-root analysis library by path — both pipelines have a
    module named _lib, and import order must not decide which one wins."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('_analysis_lib', _ROOT / 'scripts' / '_lib.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


first_author_surname = _load_analysis_lib().first_author_surname

PDF_DIR     = _BASE / 'inputs' / 'pdfs'
TEXT_DIR    = _BASE / 'inputs' / 'text'
MANIFEST    = _BASE / 'inputs' / 'manifest.csv'
EXPECTED    = _BASE / 'inputs' / 'expected_missing.csv'
OUT_DIR     = _BASE / 'outputs'
REPORT      = OUT_DIR / 'reconciliation_report.txt'

FROZEN = {
    'Alcohol': _ROOT / 'data' / 'Alcohol_Dataset.xlsx',
    'Smoking': _ROOT / 'data' / 'Smoking_Dataset.xlsx',
    'Opioid':  _ROOT / 'data' / 'Opioid_Dataset.xlsx',
}

CONDITION_BY_FOLDER = {'alcohol': 'Alcohol', 'opioids': 'Opioid', 'smoking': 'Smoking'}


def text_stem(rel_path: str) -> str:
    """Mirror of convert_pdfs.text_stem — the pre-rename converted-file name."""
    folder, name = rel_path.split('/', 1)
    return f'{folder}__{Path(name).stem}'


def frozen_keys() -> dict[str, set[tuple[str, int]]]:
    """(surname, year) tuples present in each frozen file."""
    keys: dict[str, set[tuple[str, int]]] = {}
    for label, path in FROZEN.items():
        if not path.exists():
            keys[label] = set()
            continue
        df = pd.read_excel(path)
        keys[label] = {
            (first_author_surname(r['Citation/Title']), int(r['Year']))
            for _, r in df.iterrows()
            if pd.notna(r.get('Citation/Title')) and pd.notna(r.get('Year'))
        }
    return keys


def load_expected_missing() -> dict[tuple[str, int], str]:
    """Human-authored overrides for the old-row-missing block rule."""
    if not EXPECTED.exists():
        return {}
    df = pd.read_csv(EXPECTED, dtype=str, keep_default_na=False)
    out = {}
    for _, r in df.iterrows():
        try:
            out[(r['surname'].strip(), int(r['year']))] = r.get('reason', '').strip()
        except (KeyError, ValueError):
            continue
    return out


def scan_pdf_paths() -> set[str]:
    found = set()
    for folder in CONDITION_BY_FOLDER:
        for pdf in (PDF_DIR / folder).glob('*.pdf'):
            found.add(f'{folder}/{pdf.name}')
    return found


def reconcile(manifest: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    """Return (blocking, warnings, info) lines. Does not mutate the manifest."""
    blocking: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    # Metadata completeness — everything downstream depends on it.
    for _, r in manifest.iterrows():
        if not str(r['citation']).strip():
            blocking.append(f"[{r['pdf_path']}] citation is empty — the metadata pass is incomplete")
        if not str(r['year']).strip():
            blocking.append(f"[{r['pdf_path']}] year is empty — the metadata pass is incomplete")
    if blocking:
        return blocking, warnings, info

    # Direction 1: PDF on disk with no manifest row.
    on_disk = scan_pdf_paths()
    in_manifest = set(manifest['pdf_path'])
    for rel in sorted(on_disk - in_manifest):
        blocking.append(f'[{rel}] PDF present with no manifest row — article would be '
                        f'silently absent from the dataset')

    # Direction 2: manifest row with no PDF.
    for rel in sorted(in_manifest - on_disk):
        blocking.append(f'[{rel}] manifest row with no PDF — dangling reference')

    # Direction 3: duplicate (surname, year).
    dupes = manifest[manifest.duplicated(subset=['surname', 'year'], keep=False)]
    for key, grp in dupes.groupby(['surname', 'year']):
        ids = ', '.join(grp['pdf_path'])
        blocking.append(f'[{key[0]} {key[1]}] duplicate (surname, year) across {len(grp)} rows '
                        f'({ids}) — the config dicts key on this tuple and cannot disambiguate. '
                        f'A human must decide how to key them.')

    # Direction 4: frozen old row with no manifest counterpart.
    frozen = frozen_keys()
    expected_missing = load_expected_missing()
    for label, keys in frozen.items():
        new_keys = {
            (r['surname'], int(r['year']))
            for _, r in manifest[manifest['Condition'] == label].iterrows()
        }
        for key in sorted(keys - new_keys):
            if key in expected_missing:
                info.append(f'[{key[0]} {key[1]}] ({label}) frozen row absent from the new corpus '
                            f'— accepted via expected_missing.csv: {expected_missing[key]}')
            else:
                blocking.append(f'[{key[0]} {key[1]}] ({label}) frozen row matches no manifest row '
                                f'— DATA LOSS: a study that was in the evidence base has vanished. '
                                f'Add an expected_missing.csv entry with a reason to override.')

    # Direction 5 (warning): manifest row with no frozen counterpart.
    for _, r in manifest.iterrows():
        key = (r['surname'], int(r['year']))
        if key not in frozen.get(r['Condition'], set()):
            warnings.append(f"[{r['StudyID']}] ({r['Condition']}) no frozen old counterpart — "
                            f"expected for the previously dropped alcohol studies; the corpus "
                            f"is a superset by design")

    # Near-miss: same surname, year off by one. Never auto-merged.
    for _, r in manifest.iterrows():
        keys = frozen.get(r['Condition'], set())
        if (r['surname'], int(r['year'])) in keys:
            continue
        for off in (-1, 1):
            if (r['surname'], int(r['year']) + off) in keys:
                warnings.append(
                    f"[{r['StudyID']}] NEAR-MISS: frozen file has ({r['surname']}, "
                    f"{int(r['year']) + off}) — online-first vs issue year, or two different "
                    f"papers. Requires human confirmation; never auto-merged.")

    # Conversion completeness.
    for _, r in manifest.iterrows():
        if not r['text_format']:
            blocking.append(f"[{r['pdf_path']}] not converted (text_format empty) — "
                            f"{r['fidelity_note'] or 'no reason recorded'}")

    return blocking, warnings, info


def main() -> None:
    parser = argparse.ArgumentParser(description='Derive StudyIDs and reconcile the corpus.')
    parser.add_argument('--no-rename', action='store_true',
                        help='Report only; do not rename converted text files.')
    args = parser.parse_args()

    if not MANIFEST.exists():
        print(f'ERROR: {MANIFEST} not found. Run convert_pdfs.py first.', file=sys.stderr)
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(MANIFEST, dtype=str, keep_default_na=False)

    # Derive the identity columns. The surname token is frozen here and is
    # never re-derived from model output; the gate asserts the model's
    # Citation/Title reproduces it.
    for i, r in manifest.iterrows():
        citation = str(r['citation']).strip()
        yr = str(r['year']).strip()
        if not citation or not yr:
            continue
        surname = first_author_surname(citation)
        manifest.at[i, 'surname'] = surname
        manifest.at[i, 'StudyID'] = f'{surname} {yr}'

    frozen = frozen_keys()
    for i, r in manifest.iterrows():
        if not r['surname'] or not str(r['year']).strip():
            continue
        key = (r['surname'], int(r['year']))
        manifest.at[i, 'old_row_match'] = (
            f'{key[0]} {key[1]}' if key in frozen.get(r['Condition'], set()) else 'NEW'
        )

    blocking, warnings, info = reconcile(manifest)

    renamed = 0
    if not blocking and not args.no_rename:
        for _, r in manifest.iterrows():
            ext = '.md' if r['text_format'] == 'markdown' else '.txt'
            src = TEXT_DIR / f"{text_stem(r['pdf_path'])}{ext}"
            dest = TEXT_DIR / f"{r['StudyID']}{ext}"
            if src.exists() and src != dest:
                if dest.exists():
                    dest.unlink()
                src.rename(dest)
                renamed += 1

    manifest.to_csv(MANIFEST, index=False)

    lines = ['Clinical-Trial Corpus — Reconciliation Report', '=' * 44, '']
    per_condition = manifest['Condition'].value_counts().to_dict()
    lines.append(f'Manifest rows: {len(manifest)}  ' +
                 '  '.join(f'{k}={v}' for k, v in sorted(per_condition.items())))
    for label, keys in sorted(frozen.items()):
        matched = sum(1 for _, r in manifest[manifest['Condition'] == label].iterrows()
                      if r['old_row_match'] not in ('', 'NEW'))
        new = sum(1 for _, r in manifest[manifest['Condition'] == label].iterrows()
                  if r['old_row_match'] == 'NEW')
        lines.append(f'  {label:8s} frozen={len(keys):3d}  matched={matched:3d}  new={new:3d}')
    lines.append('')

    if blocking:
        lines.append(f'BLOCKING — {len(blocking)} issue(s). Reconciliation failed.')
        lines.append('')
        lines += [f'  - {b}' for b in blocking]
        lines.append('')
    else:
        lines.append('BLOCKING — none. Corpus reconciled.')
        lines.append('')

    if warnings:
        lines.append(f'WARNINGS — {len(warnings)} (non-blocking):')
        lines.append('')
        lines += [f'  - {w}' for w in warnings]
        lines.append('')
    if info:
        lines.append(f'ACCEPTED OMISSIONS — {len(info)}:')
        lines.append('')
        lines += [f'  - {m}' for m in info]
        lines.append('')

    lines.append('New-corpus studies with no frozen counterpart (class X1 in the migration):')
    new_only = manifest[manifest['old_row_match'] == 'NEW']
    if len(new_only):
        for _, r in new_only.iterrows():
            lines.append(f"  {r['StudyID']:28s} {r['Condition']:8s} {r['pdf_path']}")
    else:
        lines.append('  (none)')
    lines.append('')

    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print('\n'.join(lines))
    if renamed:
        print(f'Renamed {renamed} converted text file(s) to {{StudyID}}.{{ext}}.')
    print(f'Report written: {REPORT}')
    if blocking:
        sys.exit(1)


if __name__ == '__main__':
    main()
