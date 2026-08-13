"""Old vs new clinical dataset comparison (clinical_old_new_mapping.md).

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/old_new_compare.py

The final gate step. A deterministic per-study, per-field agreement check
between the frozen data/<Condition>_Dataset.xlsx files and the new master, with
a disagreement taxonomy separating expected differences from errors. It is the
evidence for the one claim the frozen files can honestly support: that the
redesign did not change the evidence.

Comparison runs on the RAW frozen files against the RAW master, before
_lib.clean(). Cleaning applies transformations (3 -> 'Does not apply', '.' ->
NaN, COUNTRY_MAP, ordered categoricals, the Age_Median remap) that would mask
real disagreements and manufacture artefactual ones.

Output: outputs/old_new_comparison_report.md.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_SCRIPTS = Path(__file__).parent
_BASE    = _SCRIPTS.parent
_ROOT    = _BASE.parent
sys.path.insert(0, str(_ROOT / 'scripts'))               # for _config_<condition>


def _load_analysis_lib():
    """Load the repo-root analysis library by path — both pipelines have a
    module named _lib, and import order must not decide which one wins."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('_analysis_lib', _ROOT / 'scripts' / '_lib.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = _load_analysis_lib()

MASTER = _BASE / 'outputs' / 'clinical_master.csv'
REPORT = _BASE / 'outputs' / 'old_new_comparison_report.md'
RATIONALE = _BASE / 'outputs' / 'rationale_log.md'
RECON = _BASE / 'outputs' / 'reconciliation_report.txt'

FROZEN = {
    'Alcohol': _ROOT / 'data' / 'Alcohol_Dataset.xlsx',
    'Smoking': _ROOT / 'data' / 'Smoking_Dataset.xlsx',
    'Opioid':  _ROOT / 'data' / 'Opioid_Dataset.xlsx',
}
CONFIG = {'Alcohol': 'alcohol', 'Smoking': 'smoking', 'Opioid': 'opioid'}

# §2.2 value normalizations applied before diffing.
CONDITION_NORM = {'Opioids': 'Opioid'}
COUNTRY_NORM = {'USA': 'US'}

PERCENT_COLS = ['Retention (%)', 'PercentFem', 'RaceEthnicity_BIPOCPercent']
ENUM_COLS = ['BaseStatus', 'Age_Median', 'Country_USvsNonUS', 'Condition']
INTEGER_COLS = ['Year', 'SampleSize_NFinal']
TEXT_COLS = ['Citation/Title', 'InterventionDescription']
TIER1_TEXT = ['Outcome', 'SD', 'PVal']

DROPPED = ['url or link to pdf', 'Study Design Type', 'StudyDesignType']

PERCENT_TOL = 1.0
MONTHS_TOL = 0.5
FOLLOWUP_BINS = [1, 3, 6, 12, 24]
G_TOL = 0.05

# Old values that are invalid under the old codebook — class X3 when the new
# value is inside the documented domain (mapping doc §6).
VALID_AGE = {'<30', '30-50', '50+'}
VALID_BASE = {'Severe', 'Moderate', 'Mild'}


def norm(value, column: str):
    """Normalize a raw cell for comparison. '.' and NaN both mean not reported."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    s = str(value).strip()
    if s in ('', '.', 'nan'):
        return None
    if column == 'Condition':
        return CONDITION_NORM.get(s, s)
    if column == 'Country_USvsNonUS':
        return COUNTRY_NORM.get(s, s)
    return s


def as_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def crosses(old: float, new: float, boundary: float) -> bool:
    return (old < boundary) != (new < boundary)


def agrees(column: str, old, new) -> tuple[bool, str]:
    """Per-type agreement rule (mapping doc §4). Returns (agree, reason)."""
    o, n = norm(old, column), norm(new, column)
    if o is None and n is None:
        return True, ''
    if o is None:
        return False, 'old blank, new filled'
    if n is None:
        return False, 'old filled, new blank'

    if column in PERCENT_COLS:
        fo, fn = as_float(o), as_float(n)
        if fo is None or fn is None:
            return o == n, ''
        if column == 'Retention (%)' and crosses(fo, fn, 80):
            return False, 'crosses the 80% threshold, which flips a Table 2/3 cell'
        return abs(fo - fn) <= PERCENT_TOL, f'|delta| = {abs(fo - fn):.2f} pp'

    if column == 'Followup in months':
        fo, fn = as_float(o), as_float(n)
        if fo is None or fn is None:
            return o == n, ''
        for b in FOLLOWUP_BINS:
            if crosses(fo, fn, b):
                return False, f'crosses the Table 5 bin boundary at {b} months'
        return abs(fo - fn) <= MONTHS_TOL, f'|delta| = {abs(fo - fn):.2f} months'

    if column in INTEGER_COLS:
        fo, fn = as_float(o), as_float(n)
        if fo is not None and fn is not None:
            return fo == fn, ''
        return o == n, ''

    if column in TEXT_COLS:
        # Semantic, not string. Automated comparison can only flag candidates;
        # the report says so and a human reads them.
        return _text_similar(o, n), 'free text — flagged for human reading, not auto-adjudicated'

    fo, fn = as_float(o), as_float(n)
    if fo is not None and fn is not None:
        return fo == fn, ''
    return o == n, ''


def _text_similar(a: str, b: str) -> bool:
    ta = {w.lower().strip('.,;:()') for w in a.split() if len(w) > 3}
    tb = {w.lower().strip('.,;:()') for w in b.split() if len(w) > 3}
    if not ta or not tb:
        return a == b
    return len(ta & tb) / max(len(ta), len(tb)) >= 0.5


def classify(column: str, old, new, has_rationale: bool, binary_cols: set[str]) -> str:
    """Assign one class from the §6 taxonomy."""
    o, n = norm(old, column), norm(new, column)

    if column == 'Age_Median' and o is not None and o not in VALID_AGE and n in VALID_AGE:
        return 'X3'
    if column == 'BaseStatus' and o is not None and o not in VALID_BASE and n in VALID_BASE:
        return 'X3'
    # A free-text field holding a bare number is outside its documented
    # domain. InterventionDescription is the literal `1` in ALL 44 frozen rows
    # across all three files: the hand extraction recorded a yes/no binary
    # where the codebook specifies a <=30-word description. Old value invalid
    # under its own codebook, new value valid — the definition of X3.
    if column in TEXT_COLS and o is not None and n is not None \
            and as_float(o) is not None and as_float(n) is None:
        return 'X3'
    if o is None and n is not None:
        return 'X4'

    if column in binary_cols:
        fo, fn = as_float(o), as_float(n)
        if fo in (0, 1) and fn in (0, 1) and fo != fn:
            return 'X5' if has_rationale else 'E2'
    if column == 'SampleSize_NFinal':
        return 'E3'
    return 'X5' if has_rationale else 'E4'


def load_rationale_fields() -> dict[str, set[str]]:
    """StudyID -> set of fields with a rationale entry, parsed from the log."""
    if not RATIONALE.exists():
        return {}
    out: dict[str, set[str]] = {}
    current = None
    for line in RATIONALE.read_text(encoding='utf-8').splitlines():
        if line.startswith('## '):
            current = line[3:].strip()
            out[current] = set()
        elif line.startswith('- **') and current:
            out[current].add(line.split('**')[1])
    return out


def tier1_block(condition: str, old_raw: pd.DataFrame,
                new_raw: pd.DataFrame) -> tuple[list[str], list[str]]:
    """§5 — compare the quantity the Tier-1 fields produce, not their text."""
    cfg = importlib.import_module(f'_config_{CONFIG[condition]}')
    lines, blockers = [], []
    try:
        old_res = analysis.build_results(analysis.clean(old_raw, cfg), cfg.CONVERSION_RULES)
        new_res = analysis.build_results(analysis.clean(new_raw, cfg), cfg.CONVERSION_RULES)
    except KeyError as e:
        return [f'  could not build both plot frames: {e}'], [f'[{condition}] Tier-1 block: {e}']

    old_res = old_res.set_index('study')
    new_res = new_res.set_index('study')
    for study in sorted(set(old_res.index) & set(new_res.index)):
        o, n = old_res.loc[study], new_res.loc[study]
        notes = []

        def same(a, b) -> bool:
            """Both-missing counts as agreement. A study excluded from Tier 1
            on both sides has method NaN on both sides, and NaN != NaN would
            report every such study as a metric-family escalation."""
            if pd.isna(a) and pd.isna(b):
                return True
            return a == b

        if not same(o['method'], n['method']):
            notes.append(f"metric family {o['method']!r} -> {n['method']!r} (escalate)")
        if not same(o['confidence'], n['confidence']):
            notes.append(f"confidence {o['confidence']!r} -> {n['confidence']!r} (escalate)")
        if o['N'] != n['N']:
            msg = f"SampleSize_NFinal {o['N']} -> {n['N']} (BLOCK)"
            notes.append(msg)
            blockers.append(f'[{condition}/{study}] {msg}')
        if pd.notna(o['g']) and pd.notna(n['g']):
            dg = abs(float(o['g']) - float(n['g']))
            if np.sign(o['g']) != np.sign(n['g']):
                msg = f"sign flip on g: {o['g']:.3f} -> {n['g']:.3f} (BLOCK)"
                notes.append(msg)
                blockers.append(f'[{condition}/{study}] {msg}')
            elif dg > G_TOL:
                msg = f"|delta g| = {dg:.3f} > {G_TOL} ({o['g']:.3f} -> {n['g']:.3f}) (BLOCK)"
                notes.append(msg)
                blockers.append(f'[{condition}/{study}] {msg}')
        if notes:
            lines.append(f'  - **{study}**: ' + '; '.join(notes))
    if not lines:
        lines.append('  No Tier-1 differences on any matched study.')
    return lines, blockers


def main() -> None:
    if not MASTER.exists():
        print(f'ERROR: {MASTER} not found. Run merge_validate.py first.', file=sys.stderr)
        sys.exit(1)

    master = pd.read_csv(MASTER, dtype=object, keep_default_na=False)
    rationales = load_rationale_fields()
    binary_cols = set(analysis.BINARY_COLS)

    lines = ['# Old ↔ New Clinical Dataset Comparison', '',
             'Deterministic per-study, per-field agreement check between the frozen hand',
             'extraction and the new automated master. Comparison runs on RAW values on',
             'both sides, before `_lib.clean()`. Generated by `old_new_compare.py`.', '']

    class_counts: dict[str, int] = {}
    all_blockers: list[str] = []
    field_stats: dict[str, list[int]] = {}
    per_study_rows: list[str] = []

    for condition, path in FROZEN.items():
        if not path.exists():
            continue
        old = pd.read_excel(path, dtype=object)
        old = old.rename(columns={'Retention': 'Retention (%)'})
        new = master[master['Condition'] == condition].copy()

        # Index on a tuple key via explicit dicts: DataFrame.loc[tuple] is
        # read as (row, column), not as a single tuple-valued label.
        old_by_key = {(analysis.first_author_surname(r['Citation/Title']), int(r['Year'])): r
                      for _, r in old.iterrows()}
        new_by_key = {(analysis.first_author_surname(r['Citation/Title']),
                       int(float(r['Year']))): r for _, r in new.iterrows()}

        matched   = sorted(set(old_by_key) & set(new_by_key))
        old_only  = sorted(set(old_by_key) - set(new_by_key))
        new_only  = sorted(set(new_by_key) - set(old_by_key))

        lines += [f'## {condition}', '',
                  f'- matched: **{len(matched)}**',
                  f'- old-only (class E1 — data loss): **{len(old_only)}** {old_only or ""}',
                  f'- new-only (class X1 if listed in the reconciliation report): '
                  f'**{len(new_only)}** {new_only or ""}', '']
        for key in old_only:
            all_blockers.append(f'[{condition}] E1: frozen row {key} has no new counterpart')

        comparable = [c for c in old.columns
                      if c in new.columns and c not in DROPPED and not c.startswith('_')]

        for key in matched:
            sid = f'{key[0]} {key[1]}'
            o_row, n_row = old_by_key[key], new_by_key[key]
            has_rat = rationales.get(sid, set())

            for col in comparable:
                stats = field_stats.setdefault(col, [0, 0])
                stats[0] += 1
                ok, why = agrees(col, o_row[col], n_row[col])
                if ok:
                    continue
                stats[1] += 1
                cls = classify(col, o_row[col], n_row[col], col in has_rat, binary_cols)
                class_counts[cls] = class_counts.get(cls, 0) + 1
                rationale_note = ''
                if col in has_rat:
                    rationale_note = ' _(rationale recorded)_'
                per_study_rows.append(
                    f'| {sid} | {col} | `{norm(o_row[col], col)}` | `{norm(n_row[col], col)}` '
                    f'| **{cls}** | {why}{rationale_note} |')
                if cls in ('E2', 'E3', 'E4'):
                    all_blockers.append(f'[{condition}/{sid}] {cls} on {col}: '
                                        f'{norm(o_row[col], col)!r} -> '
                                        f'{norm(n_row[col], col)!r}')

            if n_row.get('EligibleYN') == 'N':
                class_counts['X2'] = class_counts.get('X2', 0) + 1
                lines.append(f'- **X2** — `{sid}` is in the frozen evidence base but the new '
                             f'eligibility screen rejects it: {n_row.get("EligibilityNote")}')

            # SafetyReported vs old HarmsAssessed, the one added field that is compared.
            sr = n_row.get('SafetyReported')
            ha = as_float(norm(o_row.get('HarmsAssessed'), 'HarmsAssessed'))
            if sr in ('Y', 'N') and ha is not None:
                if (sr == 'Y') != (ha == 1):
                    class_counts['E4'] = class_counts.get('E4', 0) + 1
                    per_study_rows.append(
                        f'| {sid} | SafetyReported vs old HarmsAssessed | `{ha}` | `{sr}` '
                        f'| **E4** | harms recoding |')

        lines.append('')
        lines.append('### Tier-1 block (§5)')
        lines.append('')
        t1_lines, t1_blockers = tier1_block(condition, old.reset_index(drop=True),
                                            new.reset_index(drop=True))
        lines += t1_lines
        all_blockers += t1_blockers
        lines.append('')

    lines += ['## Per-field agreement', '',
              '| Field | compared | disagree | agreement |', '|---|---|---|---|']
    for col, (n_cmp, n_dis) in sorted(field_stats.items()):
        rate = 100.0 * (n_cmp - n_dis) / n_cmp if n_cmp else float('nan')
        lines.append(f'| {col} | {n_cmp} | {n_dis} | {rate:.1f}% |')
    lines.append('')

    total = sum(v[0] for v in field_stats.values())
    disag = sum(v[1] for v in field_stats.values())
    overall = 100.0 * (total - disag) / total if total else float('nan')
    lines += ['## Class counts (§6)', '',
              '| Class | Meaning | Count |', '|---|---|---|']
    meaning = {
        'X1': 'No old counterpart by construction',
        'X2': 'Old row flagged ineligible by the new screen',
        'X3': 'Corrected old miscode',
        'X4': 'Old blank, new filled',
        'X5': 'Genuine judgment difference, rationale recorded',
        'E1': 'Matched old row missing from the new master',
        'E2': 'Flipped binary with no rationale',
        'E3': 'Changed sample size or effect size',
        'E4': 'Unexplained disagreement',
    }
    for cls in ('X1', 'X2', 'X3', 'X4', 'X5', 'E1', 'E2', 'E3', 'E4'):
        lines.append(f'| {cls} | {meaning[cls]} | {class_counts.get(cls, 0)} |')
    lines += ['',
              f'**Overall exact agreement on comparable cells: {overall:.1f}%** '
              f'({total - disag}/{total}).',
              '',
              'Advisory, not a gate. Below roughly 90% the disagreement is unlikely to be',
              'independent judgment calls and is more likely a corpus-wide convention shift —',
              'diagnose the convention and re-run rather than adjudicating cells one at a time.',
              '']

    lines += ['## Per-study disagreements', '',
              '| Study | Field | Old | New | Class | Note |', '|---|---|---|---|---|---|']
    lines += per_study_rows or ['| — | — | — | — | — | no disagreements |']
    lines.append('')

    lines += ['## Verdict', '']
    if all_blockers:
        lines.append(f'**FAIL — {len(all_blockers)} unresolved error(s).** '
                     f'Acceptance criteria 1-4 (mapping doc §7) are not met.')
        lines.append('')
        lines += [f'- {b}' for b in all_blockers]
    else:
        lines.append('**PASS — zero unresolved E1/E2/E3/E4.** Every difference is either an '
                     'expected class or carries a recorded rationale.')
    lines.append('')

    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Comparison written: {REPORT}')
    print(f'Overall exact agreement: {overall:.1f}%  |  blockers: {len(all_blockers)}')
    for b in all_blockers[:25]:
        print(f'  - {b}')
    if len(all_blockers) > 25:
        print(f'  … and {len(all_blockers) - 25} more (full list in the report).')
    if all_blockers:
        sys.exit(1)


if __name__ == '__main__':
    main()
