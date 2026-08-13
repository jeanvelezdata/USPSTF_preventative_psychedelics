"""Merge subagent responses into the AE/demographics output tables and run
the validation gate.

Usage:
    C:/Users/jeanv/miniforge3/python.exe observational_studies/scripts/merge_validate.py
    C:/Users/jeanv/miniforge3/python.exe observational_studies/scripts/merge_validate.py --raw-dir raw_responses --out-dir outputs

Reads every {StudyID}_response.json in --raw-dir (the two-part {data,
rationale} object each subagent returns per the response contract in
observational_studies_system_design.md §2 / observational_codebook.md §6),
applies the human curation decisions in --overrides, runs the full validation
gate (type/enum checks, gate-consistency rules, provenance completeness —
design doc §8, codebook §7), and writes validation_report.txt to --out-dir.

Failures BLOCK the merge: if any validation issue is found, no
articles.csv / ae_events_observational.csv / rationale_log.md /
human_review_queue.csv is written — only the report, so the run can be
re-checked without silently publishing a partially-invalid dataset. On a
clean pass, all four are written to --out-dir.

Raw response JSONs are never edited — they are the verbatim extraction
record. Exclusions, condition assignments, and field-level human overrides
live in overrides.json instead, so the published tables reproduce from
raw_responses/ + overrides.json alone.

--raw-dir and --out-dir default to raw_responses/ and outputs/ relative to
this pipeline's root; pass alternate paths to validate a fixture set without
touching the real (currently empty) raw_responses/ / outputs/ directories.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import _lib as lib

_BASE = _SCRIPTS.parent


# ── Loading ──────────────────────────────────────────────────────────────

def load_responses(raw_dir: Path) -> tuple[list[dict], list[dict], dict, dict, list[str]]:
    """Parse every {StudyID}_response.json in raw_dir.

    Returns (articles, ae_events, rationale_by_study_article,
    rationale_by_study_ae_events, load_failures).
    """
    articles: list[dict] = []
    ae_events: list[dict] = []
    rationale_article: dict[str, dict] = {}
    rationale_events: dict[str, dict] = {}
    failures: list[str] = []

    for path in sorted(raw_dir.glob('*_response.json')):
        expected_study_id = path.name[:-len('_response.json')]
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            failures.append(f"[{expected_study_id}] {path.name}: malformed JSON ({e})")
            continue

        if not isinstance(payload, dict) or 'data' not in payload or 'rationale' not in payload:
            failures.append(f"[{expected_study_id}] {path.name}: response must be an object "
                             f"with top-level 'data' and 'rationale' keys")
            continue

        data = payload['data']
        rationale = payload['rationale']

        article = data.get('article') if isinstance(data, dict) else None
        events = data.get('ae_events') if isinstance(data, dict) else None
        if not isinstance(article, dict):
            failures.append(f"[{expected_study_id}] {path.name}: data.article missing or not an object")
            continue
        if events is None:
            events = []
        if not isinstance(events, list):
            failures.append(f"[{expected_study_id}] {path.name}: data.ae_events must be a list")
            continue

        study_id = article.get('StudyID', expected_study_id)
        if study_id != expected_study_id:
            failures.append(f"[{expected_study_id}] {path.name}: data.article.StudyID "
                             f"('{study_id}') does not match filename ('{expected_study_id}')")

        articles.append(article)
        ae_events.extend(events)
        rationale_article[study_id] = rationale.get('article', {}) if isinstance(rationale, dict) else {}
        rationale_events[study_id] = rationale.get('ae_events', {}) if isinstance(rationale, dict) else {}

    return articles, ae_events, rationale_article, rationale_events, failures


# ── Human curation overrides ─────────────────────────────────────────────

def load_overrides(path: Path) -> dict:
    """Read overrides.json. An absent file means 'no overrides', not an error."""
    if not path.exists():
        return {'exclude': {}, 'conditions': {}, 'fields': {}}
    data = json.loads(path.read_text(encoding='utf-8'))
    return {section: data.get(section, {}) for section in ('exclude', 'conditions', 'fields')}


def apply_overrides(
    articles: list[dict], ae_events: list[dict], overrides: dict,
) -> tuple[list[dict], list[dict], dict[str, list[str]], list[str], list[str]]:
    """Apply overrides.json on top of the raw extraction record.

    Returns (articles, ae_events, condition_rows, notes, failures). `condition_rows`
    maps StudyID -> the condition list it contributes to; write_articles_csv emits
    one row per entry. `notes` is the human-readable audit trail for the validation
    report. An override naming a StudyID that no raw response provides is a failure,
    so a stale entry blocks the merge rather than rotting unnoticed.
    """
    known = {a.get('StudyID') for a in articles}
    notes: list[str] = []
    failures: list[str] = []

    for section in ('exclude', 'conditions', 'fields'):
        for sid in overrides[section]:
            if sid not in known:
                failures.append(f"[{sid}] overrides.{section} names a StudyID with no raw response")

    excluded = {sid: reason for sid, reason in overrides['exclude'].items() if sid in known}
    for sid in sorted(excluded):
        notes.append(f'EXCLUDED [{sid}] — {excluded[sid]}')
    articles = [a for a in articles if a.get('StudyID') not in excluded]
    ae_events = [e for e in ae_events if e.get('StudyID') not in excluded]

    by_id = {a.get('StudyID'): a for a in articles}

    condition_rows: dict[str, list[str]] = {}
    for sid, spec in overrides['conditions'].items():
        if sid not in by_id:
            continue
        values = spec['values']
        condition_rows[sid] = values
        # Validation runs one row per study, so the article carries the first
        # condition; write_articles_csv expands the rest.
        by_id[sid]['Condition'] = values[0]
        notes.append(f"CONDITION [{sid}] — {', '.join(values)}: {spec['reason']}")

    for sid, fields in overrides['fields'].items():
        if sid not in by_id:
            continue
        for field, spec in fields.items():
            before = by_id[sid].get(field)
            by_id[sid][field] = spec['value']
            notes.append(f"FIELD [{sid}] {field}: {before!r} -> {spec['value']!r} "
                         f"— {spec['reason']}")

    return articles, ae_events, condition_rows, notes, failures


# ── Validation ───────────────────────────────────────────────────────────

def validate_article_types(article: dict) -> list[str]:
    issues = []
    for field, check in lib.ARTICLE_VALIDATORS.items():
        if field not in article:
            issues.append(f"missing field '{field}'")
            continue
        if not check(article[field]):
            issues.append(f"invalid value for '{field}': {article[field]!r}")
    return issues


def validate_ae_event_types(event: dict) -> list[str]:
    issues = []
    for field, check in lib.AE_EVENT_VALIDATORS.items():
        if field not in event:
            issues.append(f"missing field '{field}'")
            continue
        if not check(event[field]):
            issues.append(f"invalid value for '{field}': {event[field]!r}")
    return issues


def validate_provenance(article: dict) -> list[str]:
    issues = []
    for field in lib.PROVENANCE_FIELDS:
        v = article.get(field)
        if field == 'Temperature':
            if not lib.is_number(v):
                issues.append(f"provenance field '{field}' is missing/empty")
        elif not lib.is_nonempty_text(v):
            issues.append(f"provenance field '{field}' is missing/empty")
    return issues


def validate_gates(article: dict, events: list[dict]) -> list[str]:
    issues = []
    sr  = article.get('SafetyReported')
    aar = article.get('AnyAEReported')
    nde = article.get('NumDistinctAEs')
    ws  = article.get('WorstSeverity')

    if sr == 'N':
        if aar != 'NA':
            issues.append(f"SafetyReported=N requires AnyAEReported=NA (got {aar!r})")
        if nde != 'NA':
            issues.append(f"SafetyReported=N requires NumDistinctAEs=NA (got {nde!r})")
        if ws != 'NA':
            issues.append(f"SafetyReported=N requires WorstSeverity=NA (got {ws!r})")
        if len(events) != 0:
            issues.append(f"SafetyReported=N requires zero ae_events rows (got {len(events)})")

    if aar == 'N':
        if not (nde == 0 or nde == '0'):
            issues.append(f"AnyAEReported=N requires NumDistinctAEs=0 (got {nde!r})")
        if ws != 'None':
            issues.append(f"AnyAEReported=N requires WorstSeverity=None (got {ws!r})")
        if len(events) != 0:
            issues.append(f"AnyAEReported=N requires zero ae_events rows (got {len(events)})")

    if aar == 'Y':
        if not (len(events) >= 1 or nde == 'Not numbered'):
            issues.append("AnyAEReported=Y requires >=1 ae_events row or NumDistinctAEs='Not numbered'")

    if events:
        severities = [e.get('Severity') for e in events if e.get('Severity') in lib.SEVERITY_RANK]
        if severities:
            max_severity = max(severities, key=lambda s: lib.SEVERITY_RANK[s])
            if ws != max_severity:
                issues.append(f"WorstSeverity ({ws!r}) does not equal max ae_events Severity "
                               f"({max_severity!r})")

    ind = lib.as_number(article.get('PctIndigenous'))
    bip = lib.as_number(article.get('PctBIPOC'))
    if ind is not None and bip is not None and ind > bip:
        issues.append(f"PctIndigenous ({ind}) exceeds PctBIPOC ({bip})")

    return issues


def validate_all(articles: list[dict], ae_events: list[dict]) -> list[str]:
    failures: list[str] = []
    study_ids = set()

    for article in articles:
        sid = article.get('StudyID', '<unknown>')
        if sid in study_ids:
            failures.append(f"[{sid}] duplicate StudyID across raw_responses")
        study_ids.add(sid)

        for issue in validate_article_types(article):
            failures.append(f"[{sid}] {issue}")
        for issue in validate_provenance(article):
            failures.append(f"[{sid}] {issue}")

        own_events = [e for e in ae_events if e.get('StudyID') == sid]
        for issue in validate_gates(article, own_events):
            failures.append(f"[{sid}] {issue}")

    for event in ae_events:
        eid = event.get('AE_ID', '<unknown>')
        esid = event.get('StudyID', '<unknown>')
        for issue in validate_ae_event_types(event):
            failures.append(f"[{esid}/{eid}] {issue}")
        if esid not in study_ids:
            failures.append(f"[{esid}/{eid}] referential integrity: StudyID not found in articles")

    # Every SeverityIndeterminate=Y row must be present in the human-review
    # queue. The queue is built from this same ae_events list (see
    # build_review_queue), so this check guards against the queue-building
    # step silently dropping a row rather than re-deriving independently.
    indeterminate_ids = {e.get('AE_ID') for e in ae_events if e.get('SeverityIndeterminate') == 'Y'}
    queue_ids = {e.get('AE_ID') for e in build_review_queue(ae_events)}
    missing_from_queue = indeterminate_ids - queue_ids
    for aeid in sorted(missing_from_queue):
        failures.append(f"[{aeid}] SeverityIndeterminate=Y but missing from human-review queue")

    return failures


def build_review_queue(ae_events: list[dict]) -> list[dict]:
    return [e for e in ae_events if e.get('SeverityIndeterminate') == 'Y']


def find_design_warnings(articles: list[dict], rationale_article: dict) -> list[str]:
    """Non-blocking: articles the subagent flagged as not observational.

    This corpus is curated to be all-observational, so IsObservational=N is
    a likely corpus-curation mistake worth a human's attention — but it is
    not a data-integrity error, so it does not block the merge the way a
    gate-consistency failure does.
    """
    warnings = []
    for article in articles:
        if article.get('IsObservational') == 'N':
            sid = article.get('StudyID', '<unknown>')
            reason = rationale_article.get(sid, {}).get('IsObservational', '(no rationale given)')
            warnings.append(f"[{sid}] IsObservational=N — {reason}")
    return warnings


# ── Output writers ───────────────────────────────────────────────────────

def write_articles_csv(articles: list[dict], condition_rows: dict[str, list[str]],
                       out_dir: Path) -> None:
    """One row per study, or one row per condition for multi-condition studies.

    Sorts stably so a study's condition rows keep the order overrides.json gives
    them and the file is byte-reproducible across runs.
    """
    rows = []
    for article in articles:
        conditions = condition_rows.get(article.get('StudyID'), [article.get('Condition')])
        for condition in conditions:
            row = {f: article.get(f) for f in lib.ARTICLE_FIELDS}
            row['Condition'] = condition
            rows.append(row)
    df = pd.DataFrame(rows, columns=lib.ARTICLE_FIELDS).sort_values('StudyID', kind='stable')
    df.to_csv(out_dir / 'articles.csv', index=False)


def write_ae_events_csv(ae_events: list[dict], out_dir: Path) -> None:
    rows = [{f: e.get(f) for f in lib.AE_EVENT_FIELDS} for e in ae_events]
    df = pd.DataFrame(rows, columns=lib.AE_EVENT_FIELDS)
    if not df.empty:
        df = df.sort_values(['StudyID', 'AE_ID'], kind='stable')
    df.to_csv(out_dir / 'ae_events_observational.csv', index=False)


def write_review_queue_csv(ae_events: list[dict], rationale_events: dict, out_dir: Path) -> None:
    queue = build_review_queue(ae_events)
    rows = []
    for e in queue:
        rows.append({
            'StudyID':     e.get('StudyID'),
            'AE_ID':       e.get('AE_ID'),
            'Description': e.get('Description'),
            'Severity':    e.get('Severity'),
            'Rationale':   rationale_events.get(e.get('StudyID'), {}).get(e.get('AE_ID'), ''),
        })
    df = pd.DataFrame(rows, columns=['StudyID', 'AE_ID', 'Description', 'Severity', 'Rationale'])
    if not df.empty:
        df = df.sort_values(['StudyID', 'AE_ID'], kind='stable')
    df.to_csv(out_dir / 'human_review_queue.csv', index=False)


def study_override_notes(sid: str, overrides: dict) -> list[str]:
    """The overrides.json entries that apply to one study, as log lines."""
    lines = []
    spec = overrides['conditions'].get(sid)
    if spec:
        lines.append(f"- **Condition** (override): {', '.join(spec['values'])} — {spec['reason']}")
    for field, field_spec in overrides['fields'].get(sid, {}).items():
        lines.append(f"- **{field}** (override): {field_spec['value']!r} — {field_spec['reason']}")
    return lines


def write_rationale_log(
    articles: list[dict], rationale_article: dict, rationale_events: dict,
    overrides: dict, out_dir: Path,
) -> None:
    lines = ['# Rationale Log', '']
    for article in sorted(articles, key=lambda a: a.get('StudyID', '')):
        sid = article.get('StudyID', '<unknown>')
        lines.append(f'## {sid}')
        art_rat = rationale_article.get(sid, {})
        if art_rat:
            lines.append('### Article')
            for field, reason in art_rat.items():
                lines.append(f'- **{field}**: {reason}')
        override_notes = study_override_notes(sid, overrides)
        if override_notes:
            lines.append('### Human curation (overrides.json)')
            lines.extend(override_notes)
        ae_rat = rationale_events.get(sid, {})
        if ae_rat:
            lines.append('### AE events')
            for aeid, reason in ae_rat.items():
                lines.append(f'- **{aeid}**: {reason}')
        lines.append('')
    (out_dir / 'rationale_log.md').write_text('\n'.join(lines), encoding='utf-8')


def write_validation_report(
    failures: list[str], warnings: list[str], override_notes: list[str],
    n_articles: int, n_events: int, out_dir: Path,
) -> None:
    lines = ['AE/Demographics Extraction — Validation Report', '=' * 48, '']
    lines.append(f'Articles parsed:  {n_articles}  (after overrides.json exclusions)')
    lines.append(f'AE events parsed: {n_events}  (after overrides.json exclusions)')
    lines.append('')
    if failures:
        lines.append(f'VALIDATION FAILED — {len(failures)} issue(s). Merge blocked; '
                      f'no output tables were written.')
        lines.append('')
        for f in failures:
            lines.append(f'  - {f}')
    else:
        lines.append('VALIDATION PASSED — 0 issues. Output tables written.')
    lines.append('')
    if warnings:
        lines.append(f'WARNINGS — {len(warnings)} (non-blocking; review before publication):')
        lines.append('')
        for w in warnings:
            lines.append(f'  - {w}')
        lines.append('')
    if override_notes:
        lines.append(f'HUMAN OVERRIDES APPLIED — {len(override_notes)} (from overrides.json):')
        lines.append('')
        for note in override_notes:
            lines.append(f'  - {note}')
        lines.append('')
    (out_dir / 'validation_report.txt').write_text('\n'.join(lines), encoding='utf-8')


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Merge raw_responses/ into outputs/ and run the validation gate.')
    parser.add_argument('--raw-dir', default='raw_responses',
                         help='Directory of {StudyID}_response.json files (default: raw_responses).')
    parser.add_argument('--out-dir', default='outputs',
                         help='Directory to write outputs into (default: outputs).')
    parser.add_argument('--overrides', default='overrides.json',
                         help='Human curation decisions applied on top of the raw '
                              'responses (default: overrides.json).')
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    if not raw_dir.is_absolute():
        raw_dir = _BASE / raw_dir
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = _BASE / out_dir
    overrides_path = Path(args.overrides)
    if not overrides_path.is_absolute():
        overrides_path = _BASE / overrides_path
    out_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print(f"ERROR: raw-dir not found: {raw_dir}", file=sys.stderr)
        sys.exit(1)

    articles, ae_events, rationale_article, rationale_events, load_failures = load_responses(raw_dir)
    overrides = load_overrides(overrides_path)
    articles, ae_events, condition_rows, override_notes, override_failures = apply_overrides(
        articles, ae_events, overrides)
    validation_failures = validate_all(articles, ae_events)
    failures = load_failures + override_failures + validation_failures
    warnings = find_design_warnings(articles, rationale_article)

    write_validation_report(failures, warnings, override_notes,
                            len(articles), len(ae_events), out_dir)

    if failures:
        print(f"VALIDATION FAILED — {len(failures)} issue(s). See {out_dir / 'validation_report.txt'}")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    write_articles_csv(articles, condition_rows, out_dir)
    write_ae_events_csv(ae_events, out_dir)
    write_review_queue_csv(ae_events, rationale_events, out_dir)
    write_rationale_log(articles, rationale_article, rationale_events, overrides, out_dir)

    print(f"VALIDATION PASSED. {len(articles)} article(s), {len(ae_events)} ae_event(s) merged, "
          f"{len(override_notes)} override(s) applied.")
    if warnings:
        print(f"WARNINGS — {len(warnings)} (non-blocking, see validation_report.txt):")
        for w in warnings:
            print(f"  - {w}")
    print(f"Written: articles.csv, ae_events_observational.csv, human_review_queue.csv, "
          f"rationale_log.md, validation_report.txt -> {out_dir}")


if __name__ == '__main__':
    main()
