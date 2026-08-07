"""Apply ratified config proposals to scripts/_config_<condition>.py (design §5.3).

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/apply_config_proposals.py --dry-run
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/apply_config_proposals.py --condition alcohol
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/apply_config_proposals.py

Reads outputs/config_proposals/<condition>.py, written by merge_validate.py
with a `_disposition` on every entry, and merges the auto-ratified and
carried-forward entries into scripts/_config_<condition>.py. Pending entries
are left out and printed for a human; gate_rebuild.py then blocks the rebuild
while any *eligible* study lacks a ratified entry.

Three dispositions:

  auto-ratified    proposed confidence=clean. Applied without human review.
                   The residual risk is a plausible-but-wrong `clean` on a
                   supported method — merge_validate.py lists every one of
                   these in validation_report.txt so the residue is visible
                   after the fact even though it did not block.
  carried-forward  the study has a frozen entry and the proposal's method and
                   confidence both match it. The frozen entry's `note` and
                   `direction` are kept verbatim: the existing hand-written
                   text is the authority, and a model paraphrase of it is a
                   loss, not a gain.
  pending          everything else. Needs a human.

Writes the three tables back in the frozen files' own format so the diff is
readable. The original is copied to <name>.py.bak before any write.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import shutil
import sys
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).parent
_BASE    = _SCRIPTS.parent
_ROOT    = _BASE.parent
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_ROOT / 'scripts'))

# Model notes quote statistics containing μ, χ, η and similar. The Windows
# console defaults to cp1252 and raises on them, which would abort a report
# that is otherwise fine — substitute rather than crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

import _lib as lib  # noqa: E402

PROPOSAL_DIR = _BASE / 'outputs' / 'config_proposals'
CONFIG_DIR   = _ROOT / 'scripts'
MASTER       = _BASE / 'outputs' / 'clinical_master.csv'

CONDITIONS = ('alcohol', 'smoking', 'opioid')
CONDITION_LABEL = {'alcohol': 'Alcohol', 'smoking': 'Smoking', 'opioid': 'Opioid'}

APPLIED = ('auto-ratified', 'carried-forward')


def load_proposals(condition: str) -> dict:
    path = PROPOSAL_DIR / f'{condition}.py'
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location(f'_proposals_{condition}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, 'PROPOSALS', {})


def load_frozen(condition: str):
    return importlib.import_module(f'_config_{condition}')


def fmt_key(key: tuple) -> str:
    return f'({key[0]!r:>18}, {key[1]}):'


def render_extractions(entries: dict[tuple, dict]) -> list[str]:
    lines = ['EFFECT_SIZE_EXTRACTIONS: dict = {']
    for key in sorted(entries, key=lambda k: (k[0], k[1])):
        e = entries[key]
        lines.append(f'    {fmt_key(key)} ({e["metric"]!r}, {e["measure"]!r}, {e["note"]!r}),')
    lines += ['}', '']
    return lines


def render_rules(entries: dict[tuple, dict]) -> list[str]:
    lines = ['CONVERSION_RULES: dict = {']
    for key in sorted(entries, key=lambda k: (k[0], k[1])):
        e = entries[key]
        parts = [f"'method': {e['method']!r}"]
        if e.get('df_error') is not None:
            parts.append(f"'df_error': {e['df_error']!r}")
        parts.append(f"'confidence': {e['confidence']!r}")
        if e.get('direction') not in (None, 1):
            parts.append(f"'direction': {e['direction']!r}")
        if e.get('note'):
            parts.append(f"'note': {e['note']!r}")
        lines.append(f'    {fmt_key(key)} {{{", ".join(parts)}}},')
    lines += ['}', '']
    return lines


def render_tier2(entries: dict[tuple, dict]) -> list[str]:
    lines = ['TIER2_RATINGS: dict = {']
    for key in sorted(entries, key=lambda k: (k[0], k[1])):
        e = entries[key]
        lines.append(f'    {fmt_key(key)} {{')
        lines.append(f"        'category': {e['category']!r},")
        lines.append(f"        'basis':    {e['basis']!r},")
        if e.get('computed_or') is not None:
            lines.append(f"        'computed_or': {e['computed_or']!r},")
        lines.append('    },')
    lines += ['}', '']
    return lines


def merge_condition(condition: str, dry_run: bool) -> tuple[int, int, list[str]]:
    """Returns (n_applied, n_pending, pending_descriptions)."""
    proposals = load_proposals(condition)
    if not proposals:
        return 0, 0, []
    frozen = load_frozen(condition)

    extractions = dict(getattr(frozen, 'EFFECT_SIZE_EXTRACTIONS', {}))
    rules       = dict(getattr(frozen, 'CONVERSION_RULES', {}))
    tier2       = dict(getattr(frozen, 'TIER2_RATINGS', {}))

    n_applied = 0
    pending: list[str] = []

    for key, p in proposals.items():
        disp = p.get('_disposition', 'pending')
        if disp not in APPLIED:
            pending.append(f"{key[0]} {key[1]}: method={p.get('method')!r} "
                           f"confidence={p.get('confidence')!r} — {p.get('note', '')}")
            continue

        old_rule = rules.get(key, {})
        # Carried forward: the frozen note and direction are the authority.
        note      = old_rule.get('note', p.get('note', '')) if disp == 'carried-forward' \
            else p.get('note', '')
        direction = old_rule.get('direction', p.get('direction', 1)) if disp == 'carried-forward' \
            else p.get('direction', 1)

        # An OR/RR proposal routinely records the two-group proportions in
        # `measure` and the ratio the method actually converts in
        # `computed_or`. Promote the number, and keep the proportions in the
        # note so the source figures are not lost.
        measure = p.get('measure')
        proportions_note = ''
        if p.get('method') in ('OR', 'RR') and p.get('computed_or') is not None:
            try:
                float(str(measure).strip())
            except (TypeError, ValueError):
                proportions_note = f' [from {measure}]'
                measure = p['computed_or']

        extractions[key] = {
            'metric':  p.get('metric'),
            'measure': measure,
            'note':    extractions.get(key, (None, None, ''))[2]
                       if disp == 'carried-forward' and key in extractions
                       else (p.get('note') or ''),
        }
        rules[key] = {
            'method':     p.get('method'),
            'df_error':   p.get('df_error'),
            'confidence': p.get('confidence'),
            'direction':  direction,
            'note':       note + proportions_note,
        }
        if p.get('confidence') == 'excluded' and p.get('tier2_category'):
            tier2[key] = {
                'category':    p['tier2_category'],
                'basis':       p.get('tier2_basis', ''),
                'computed_or': p.get('computed_or'),
            }
        n_applied += 1

    # Frozen entries not touched by a proposal keep their tuple form.
    normalised_extractions = {}
    for key, val in extractions.items():
        if isinstance(val, tuple):
            normalised_extractions[key] = {'metric': val[0], 'measure': val[1], 'note': val[2]}
        else:
            normalised_extractions[key] = val

    if dry_run:
        return n_applied, len(pending), pending

    path = CONFIG_DIR / f'_config_{condition}.py'
    shutil.copy2(path, path.with_suffix('.py.bak'))
    label = CONDITION_LABEL[condition]
    out = [
        f'"""Per-condition configuration for {condition} psychedelic trials."""',
        '',
        f"CONDITION_NAME = {condition!r}",
        f"CONDITION_LABEL = {label!r}   # value of the master's Condition column",
        "INPUT_FILE = 'clinical_trials/outputs/clinical_master.csv'",
        '',
        '# ── Effect-size extraction table ' + '─' * 46,
        '# Keyed by (first_author_surname, year). One entry per study.',
        '# (metric, measure, note) — measure is numeric where possible; "X vs Y"',
        '# string for irreducible two-group comparisons.',
        '',
    ]
    out += render_extractions(normalised_extractions)
    out += ['# ── Conversion rules ' + '─' * 58,
            '# Keyed by (first_author_surname, year).',
            "# direction defaults to +1; set -1 when the metric's natural sign is",
            '# opposite to the favoured treatment direction.',
            '']
    out += render_rules(rules)
    out += ['# ── Tier 2 qualitative ratings ' + '─' * 48,
            '# Keyed by (first_author_surname, year). Studies excluded from Tier 1.',
            '']
    out += render_tier2(tier2)
    path.write_text('\n'.join(out), encoding='utf-8')
    return n_applied, len(pending), pending


def eligible_keys(condition: str) -> set[tuple]:
    """(surname, year) of every eligible study of this condition in the master."""
    if not MASTER.exists():
        return set()
    sys.path.insert(0, str(_ROOT / 'scripts'))
    from _lib import first_author_surname
    df = pd.read_csv(MASTER, dtype=str, keep_default_na=False)
    df = df[(df['Condition'] == CONDITION_LABEL[condition]) & (df['EligibleYN'] == 'Y')]
    return {(first_author_surname(r['Citation/Title']), int(float(r['Year'])))
            for _, r in df.iterrows()}


def main() -> None:
    parser = argparse.ArgumentParser(description='Apply ratified config proposals.')
    parser.add_argument('--condition', choices=CONDITIONS,
                        help='Apply one condition only (default: all).')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be applied without writing.')
    args = parser.parse_args()

    targets = [args.condition] if args.condition else list(CONDITIONS)
    total_pending = 0

    for condition in targets:
        n_applied, n_pending, pending = merge_condition(condition, args.dry_run)
        verb = 'would apply' if args.dry_run else 'applied'
        print(f'\n{condition}: {verb} {n_applied} entr(ies), {n_pending} pending.')
        if pending:
            print('  PENDING — need a human decision before the rebuild:')
            for p in pending:
                print(f'    - {p}')
        total_pending += n_pending

        missing = eligible_keys(condition) - set(load_proposals(condition))
        if missing:
            print(f'  NO PROPOSAL AT ALL for {len(missing)} eligible stud(ies): '
                  f'{sorted(missing)}')

    if not args.dry_run:
        print('\nBackups written alongside each config as _config_<condition>.py.bak.')
    if total_pending:
        print(f'\n{total_pending} pending proposal(s) remain. gate_rebuild.py will block the '
              f'rebuild while any eligible study lacks a ratified entry.')
    del lib


if __name__ == '__main__':
    main()
