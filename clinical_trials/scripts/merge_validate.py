"""Merge subagent responses into clinical_master and run the validation gate.

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/merge_validate.py
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/merge_validate.py --raw-dir raw_responses --out-dir outputs

Reads every {StudyID}_response.json in --raw-dir (the two-part {data, rationale}
object each subagent returns per the contract in clinical_system_design.md §2 /
clinical_codebook.md §7) and runs the blocking checks that are derivable from
the responses, the manifest and the converted text.

**Blocking failures prevent any output table from being written** — only
validation_report.txt is produced, so a partially-invalid dataset is never
silently published. On a clean pass this writes clinical_master.csv,
clinical_master.xlsx, ae_events.csv, rationale_log.md, human_review_queue.csv
and config_proposals/<condition>.py.

Gate coverage. Design §8 lists fourteen blocking checks; they run at two
different points in the workflow because two of them need artifacts that do
not exist until after the rebuild:

    checks 1-10, 12  here (response / manifest / text derived)
    checks 11, 13    gate_rebuild.py  (needs the ratified config and the
                     cleaned per-condition frames)
    check 14         visual_regression.py (needs the rebuilt artifacts)

Splitting them this way is what lets check 11 block the *rebuild* rather than
the merge — the config entries it checks are proposed by this step and
ratified by the next one, so blocking the merge on them would deadlock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).parent
_BASE    = _SCRIPTS.parent
_ROOT    = _BASE.parent

# Both pipelines have a module named _lib. Keep them apart explicitly: `lib` is
# always the clinical schema module here, and the repo-root analysis library is
# loaded by path so import order cannot silently swap them.
sys.path.insert(0, str(_SCRIPTS))
import _lib as lib                                       # noqa: E402  (clinical schema)


def _load_analysis_lib():
    import importlib.util
    spec = importlib.util.spec_from_file_location('_analysis_lib', _ROOT / 'scripts' / '_lib.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = _load_analysis_lib()
first_author_surname = analysis.first_author_surname

sys.path.append(str(_ROOT / 'scripts'))                  # for _config_<condition>
import reconcile_manifest as recon                       # noqa: E402
import apply_adjudication                                # noqa: E402

MANIFEST = _BASE / 'inputs' / 'manifest.csv'
TEXT_DIR = _BASE / 'inputs' / 'text'

CONFIG_BY_CONDITION = {'Alcohol': 'alcohol', 'Smoking': 'smoking', 'Opioid': 'opioid'}


# ── Loading ──────────────────────────────────────────────────────────────

def load_responses(raw_dir: Path) -> tuple[list[dict], list[dict], dict, dict, dict, list[str]]:
    """Parse every {StudyID}_response.json. Returns articles, events, three
    rationale maps keyed by StudyID, and load failures."""
    articles: list[dict] = []
    events: list[dict] = []
    rat_article: dict[str, dict] = {}
    rat_events: dict[str, dict] = {}
    proposals: dict[str, dict] = {}
    failures: list[str] = []

    for path in sorted(raw_dir.glob('*_response.json')):
        expected = path.name[:-len('_response.json')]
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            failures.append(f'[{expected}] {path.name}: malformed JSON ({e})')
            continue
        if not isinstance(payload, dict) or 'data' not in payload or 'rationale' not in payload:
            failures.append(f"[{expected}] {path.name}: response must be an object with "
                            f"top-level 'data' and 'rationale' keys")
            continue

        data = payload['data']
        rationale = payload['rationale'] if isinstance(payload['rationale'], dict) else {}
        article = data.get('article') if isinstance(data, dict) else None
        rows = data.get('ae_events') if isinstance(data, dict) else None
        if not isinstance(article, dict):
            failures.append(f'[{expected}] {path.name}: data.article missing or not an object')
            continue
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            failures.append(f'[{expected}] {path.name}: data.ae_events must be a list')
            continue

        sid = article.get('StudyID', expected)
        if sid != expected:
            failures.append(f"[{expected}] {path.name}: data.article.StudyID ('{sid}') "
                            f"does not match filename ('{expected}')")

        articles.append(article)
        events.extend(rows)
        rat_article[sid] = rationale.get('article', {}) or {}
        rat_events[sid] = rationale.get('ae_events', {}) or {}
        proposals[sid] = rationale.get('config_proposal', {}) or {}

    return articles, events, rat_article, rat_events, proposals, failures


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ── Blocking checks ──────────────────────────────────────────────────────

def check_columns(article: dict) -> list[str]:
    """Check 2 — column set exactly the 54 carried + 18 added names."""
    got, want = set(article), set(lib.ARTICLE_FIELDS)
    return (
        [f"missing field '{f}'" for f in sorted(want - got)]
        + [f"unexpected field '{f}'" for f in sorted(got - want)]
    )


def check_types(article: dict) -> list[str]:
    """Check 1 — type/enum per field."""
    issues = []
    for field, ok in lib.ARTICLE_VALIDATORS.items():
        if field in article and not ok(article[field]):
            issues.append(f"invalid value for '{field}': {article[field]!r}")
    return issues


def check_eligibility(article: dict) -> list[str]:
    """Check 3 — the four blocking rows of design §5.1."""
    issues = []
    elig = article.get('EligibleYN')
    crit = article.get('EligibilityFailedCriterion')
    note = article.get('EligibilityNote')
    ctyn = article.get('Clincial Trial YN')

    if elig == 'Y' and crit != 'NA':
        issues.append(f"EligibleYN=Y requires EligibilityFailedCriterion=NA (got {crit!r})")
    if elig == 'N' and crit == 'NA':
        issues.append("EligibleYN=N requires a named EligibilityFailedCriterion, not NA")
    if elig == 'N' and not (isinstance(note, str) and note.strip() not in ('', '.', 'NA')):
        issues.append(f"EligibleYN=N requires a non-empty EligibilityNote (got {note!r})")

    failed_a = crit in ('not_clinical_trial', 'both')
    if lib.as_number(ctyn) == 1 and failed_a:
        issues.append(f"Clincial Trial YN=1 contradicts EligibilityFailedCriterion={crit!r}")
    if lib.as_number(ctyn) == 0 and not failed_a:
        issues.append(f"Clincial Trial YN=0 contradicts EligibilityFailedCriterion={crit!r} "
                      f"— criterion (a) was not recorded as failed")
    return issues


def check_harms_safety(article: dict) -> list[str]:
    """Check 4 — SafetyReported=Y <=> HarmsAssessed=1."""
    sr = article.get('SafetyReported')
    ha = article.get('HarmsAssessed')
    ha_is_one = lib.as_number(ha) == 1
    if sr == 'Y' and not ha_is_one:
        return [f'SafetyReported=Y requires HarmsAssessed=1 (got {ha!r})']
    if sr == 'N' and ha_is_one:
        return ['SafetyReported=N requires HarmsAssessed in {0, 3, "."} (got 1)']
    return []


def check_ae_gate(article: dict, events: list[dict]) -> list[str]:
    """Check 5 — AE gate consistency, imported from the observational pipeline."""
    issues = []
    sr, aar = article.get('SafetyReported'), article.get('AnyAEReported')
    nde, ws = article.get('NumDistinctAEs'), article.get('WorstSeverity')

    if sr == 'N':
        if aar != 'NA':
            issues.append(f'SafetyReported=N requires AnyAEReported=NA (got {aar!r})')
        if nde != 'NA':
            issues.append(f'SafetyReported=N requires NumDistinctAEs=NA (got {nde!r})')
        if ws != 'NA':
            issues.append(f'SafetyReported=N requires WorstSeverity=NA (got {ws!r})')
        if article.get('AE_denominator') == 'NA':
            issues.append('AE_denominator never takes "NA"; use "." when no safety assessment')
        if events:
            issues.append(f'SafetyReported=N requires zero ae_events rows (got {len(events)})')

    if aar == 'N':
        if lib.as_number(nde) != 0:
            issues.append(f'AnyAEReported=N requires NumDistinctAEs=0 (got {nde!r})')
        if ws != 'None':
            issues.append(f'AnyAEReported=N requires WorstSeverity=None (got {ws!r})')
        if events:
            issues.append(f'AnyAEReported=N requires zero ae_events rows (got {len(events)})')

    if aar == 'Y' and not (events or nde == 'Not numbered'):
        issues.append("AnyAEReported=Y requires >=1 ae_events row or NumDistinctAEs='Not numbered'")

    if events:
        graded = [e.get('Severity') for e in events if e.get('Severity') in lib.SEVERITY_RANK]
        if graded:
            worst = max(graded, key=lambda s: lib.SEVERITY_RANK[s])
            if ws != worst:
                issues.append(f'WorstSeverity ({ws!r}) does not equal max ae_events Severity '
                              f'({worst!r})')
    return issues


def check_checklist(sid: str, article: dict, rationale: dict) -> list[str]:
    """Check 6 — the 14-criterion arithmetic."""
    obj = rationale.get('MethodologyDescribedYN')
    if not isinstance(obj, dict):
        return ['rationale.article.MethodologyDescribedYN must be the structured object '
                '{criteria, n_met, note}']
    issues = []
    criteria = obj.get('criteria')
    if not isinstance(criteria, dict):
        return ["rationale.article.MethodologyDescribedYN.criteria must be an object"]
    missing = [k for k in lib.METHODOLOGY_CRITERIA if k not in criteria]
    if missing:
        issues.append(f'MethodologyDescribedYN.criteria missing key(s): {missing}')
    bad = {k: v for k, v in criteria.items() if v not in ('Y', 'N')}
    if bad:
        issues.append(f'MethodologyDescribedYN.criteria values must be "Y"/"N": {bad}')
    if issues:
        return issues

    n_yes = sum(1 for k in lib.METHODOLOGY_CRITERIA if criteria[k] == 'Y')
    if lib.as_number(obj.get('n_met')) != n_yes:
        issues.append(f"MethodologyDescribedYN.n_met ({obj.get('n_met')!r}) does not equal the "
                      f'count of "Y" ({n_yes})')
    binary = lib.as_number(article.get('MethodologyDescribedYN'))
    if binary in (0, 1):
        expected = 1 if n_yes >= lib.METHODOLOGY_THRESHOLD else 0
        if binary != expected:
            issues.append(f'MethodologyDescribedYN={int(binary)} but n_met={n_yes}; the binary '
                          f'is 1 iff n_met >= {lib.METHODOLOGY_THRESHOLD} (expected {expected})')
    return issues


def check_internal_design(article: dict) -> list[str]:
    """Codebook §8 — internal design consistency."""
    issues = []
    if lib.as_number(article.get('Double+Blind')) == 1 and \
            lib.as_number(article.get('BlindingYN')) == 0:
        issues.append('Double+Blind=1 requires BlindingYN=1')
    n_sub = sum(1 for c in lib.SUBSTANCE_FLAGS if lib.as_number(article.get(c)) == 1)
    multi = lib.as_number(article.get('MultiplePsychedelic'))
    if n_sub >= 2 and multi != 1:
        issues.append(f'{n_sub} substance flags are 1, so MultiplePsychedelic must be 1 '
                      f'(got {article.get("MultiplePsychedelic")!r})')
    return issues


def check_provenance(article: dict) -> list[str]:
    """Check 7 — provenance completeness."""
    issues = []
    for field in lib.PROVENANCE_FIELDS:
        v = article.get(field)
        ok = lib.is_number(v) if field == 'Temperature' else lib.is_nonempty_text(v)
        if not ok:
            issues.append(f"provenance field '{field}' is missing/empty")
    return issues


def check_text_provenance(sid: str, article: dict, raw_dir: Path) -> list[str]:
    """Check 8 — converted file exists at the implied extension and its SHA-256
    matches the one archived in the request."""
    fmt = article.get('text_format')
    if fmt not in lib.TEXT_FORMATS:
        return []  # already reported by the type check
    ext = '.md' if fmt == 'markdown' else '.txt'
    path = TEXT_DIR / f'{sid}{ext}'
    if not path.exists():
        return [f'text_format={fmt} but no converted file at {path.name}']

    req_path = raw_dir / f'{sid}_request.json'
    if not req_path.exists():
        return [f'no archived request at {req_path.name} — provenance chain is broken']
    try:
        request = json.loads(req_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        return [f'{req_path.name}: malformed JSON ({e})']
    archived = request.get('text_sha256')
    actual = sha256_file(path)
    if archived != actual:
        return [f'{path.name} SHA-256 {actual[:12]}… does not match the archived '
                f'{str(archived)[:12]}… — the text changed after extraction']
    return []


def check_identity(articles: list[dict], manifest: pd.DataFrame) -> list[str]:
    """Check 9 — model citation reproduces the frozen manifest surname, and
    (surname, Year) is unique across the master."""
    issues = []
    frozen = {r['StudyID']: (r['surname'], str(r['year'])) for _, r in manifest.iterrows()}
    seen: dict[tuple[str, int], str] = {}

    for a in articles:
        sid = a.get('StudyID', '<unknown>')
        if sid not in frozen:
            issues.append(f'[{sid}] StudyID not present in the manifest')
            continue
        want_surname, want_year = frozen[sid]
        got_surname = first_author_surname(a.get('Citation/Title', ''))
        if got_surname != want_surname:
            issues.append(f"[{sid}] Citation/Title yields surname token {got_surname!r} but the "
                          f"manifest froze {want_surname!r} — the config lookup key would miss")
        got_year = lib.as_number(a.get('Year'))
        if got_year is not None and str(int(got_year)) != want_year:
            issues.append(f'[{sid}] Year {int(got_year)} disagrees with the manifest year '
                          f'{want_year}')
        if got_year is not None:
            key = (got_surname, int(got_year))
            if key in seen:
                issues.append(f'[{sid}] duplicate (surname, Year) {key} — also {seen[key]}. '
                              f'The config dicts key on this tuple and cannot disambiguate.')
            seen[key] = sid
    return issues


def check_config_proposals(proposals: dict[str, dict]) -> list[str]:
    """Check 12 — proposal discipline."""
    issues = []
    for sid, p in proposals.items():
        if not p:
            issues.append(f'[{sid}] rationale.config_proposal is missing or empty')
            continue
        conf, method = p.get('confidence'), p.get('method')
        if conf not in lib.CONFIDENCE_BANDS:
            issues.append(f'[{sid}] config_proposal.confidence must be one of '
                          f'{list(lib.CONFIDENCE_BANDS)} (got {conf!r})')
        if conf == 'clean' and method not in lib.SUPPORTED_METHODS:
            issues.append(f'[{sid}] confidence=clean is only accepted for the seven methods '
                          f'convert_to_d() implements {list(lib.SUPPORTED_METHODS)} '
                          f'(got method={method!r})')
        if method == 'F' and not lib.is_number(p.get('df_error')):
            issues.append(f"[{sid}] method='F' requires a numeric df_error "
                          f"(got {p.get('df_error')!r})")
        if method is not None and method not in lib.SUPPORTED_METHODS:
            issues.append(f'[{sid}] unknown conversion method {method!r}; use null when no '
                          f'conversion is possible')
        # A convertible method needs a single number to convert. A descriptive
        # measure ("23.5% vs 47.8%") silently produced a crash at rebuild time
        # rather than a visible exclusion, so it is caught here instead.
        # An OR/RR proposal routinely puts the two-group proportions in
        # `measure` and the computed ratio in `computed_or`. That is a field
        # placement slip, not a missing number — apply_config_proposals.py
        # promotes computed_or to measure, so it is accepted here.
        or_rescued = (method in ('OR', 'RR') and lib.is_number(p.get('computed_or')))
        if method is not None and not lib.is_number(p.get('measure')) and not or_rescued:
            issues.append(f"[{sid}] method={method!r} requires a numeric measure, but measure is "
                          f"{p.get('measure')!r}. Either give the number the method converts, or "
                          f"set method=null with confidence='excluded'.")
    return issues


def check_rationale_completeness(sid: str, rationale: dict) -> list[str]:
    """Codebook §8 — the four Tier-1 fields need a rationale on every article."""
    return [f"rationale.article is missing the mandatory '{f}' entry"
            for f in lib.TIER1_FIELDS
            if not str(rationale.get(f, '')).strip()]


def validate_all(articles: list[dict], events: list[dict], rat_article: dict,
                 proposals: dict, manifest: pd.DataFrame, raw_dir: Path) -> list[str]:
    failures: list[str] = []
    for a in articles:
        sid = a.get('StudyID', '<unknown>')
        own = [e for e in events if e.get('StudyID') == sid]
        rat = rat_article.get(sid, {})
        for issue in (check_columns(a) + check_types(a) + check_eligibility(a)
                      + check_harms_safety(a) + check_ae_gate(a, own)
                      + check_checklist(sid, a, rat) + check_internal_design(a)
                      + check_provenance(a) + check_text_provenance(sid, a, raw_dir)
                      + check_rationale_completeness(sid, rat)):
            failures.append(f'[{sid}] {issue}')

    study_ids = {a.get('StudyID') for a in articles}
    for e in events:
        eid, esid = e.get('AE_ID', '<unknown>'), e.get('StudyID', '<unknown>')
        for field, ok in lib.AE_EVENT_VALIDATORS.items():
            if field not in e:
                failures.append(f"[{esid}/{eid}] missing field '{field}'")
            elif not ok(e[field]):
                failures.append(f"[{esid}/{eid}] invalid value for '{field}': {e[field]!r}")
        if esid not in study_ids:
            failures.append(f'[{esid}/{eid}] referential integrity: StudyID not found in articles')

    # Every SeverityIndeterminate=Y row must reach the human-review queue. The
    # queue is built from this same list, so this guards the queue builder
    # rather than re-deriving the rule.
    flagged = {e.get('AE_ID') for e in events if e.get('SeverityIndeterminate') == 'Y'}
    queued = {r['ref'] for r in build_review_queue(articles, events, rat_article, proposals, {})
              if r['kind'] == 'indeterminate_severity'}
    for aeid in sorted(flagged - queued):
        failures.append(f'[{aeid}] SeverityIndeterminate=Y but missing from the human-review queue')

    failures += check_identity(articles, manifest)
    failures += check_config_proposals(proposals)

    # Check 10 — corpus reconciliation, re-run here so the gate is not
    # dependent on someone having run reconcile_manifest.py recently.
    blocking, _warn, _info = recon.reconcile(manifest)
    failures += [f'[reconciliation] {b}' for b in blocking]

    covered = {a.get('StudyID') for a in articles}
    for sid in sorted(set(manifest['StudyID']) - covered):
        failures.append(f'[{sid}] manifest row has no extraction response')

    return failures


# ── Warnings (non-blocking) ──────────────────────────────────────────────

def collect_warnings(articles: list[dict], events: list[dict], rat_article: dict,
                     proposals: dict, dispositions: dict, manifest: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    fmt_note = {r['StudyID']: r['fidelity_note'] for _, r in manifest.iterrows()}

    for a in articles:
        sid = a.get('StudyID', '<unknown>')
        rat = rat_article.get(sid, {})

        if a.get('EligibleYN') == 'N':
            warnings.append(f"[{sid}] EligibleYN=N — {a.get('EligibilityNote')}")

        ctyn = a.get('Clincial Trial YN')
        if (ctyn == '.' or lib.as_number(ctyn) == 3) and \
                a.get('EligibilityFailedCriterion') in ('NA', 'no_sud_outcome'):
            warnings.append(f'[{sid}] Clincial Trial YN={ctyn!r} while eligibility criterion (a) '
                            f'passed — design undeterminable yet the screen reached a verdict')

        # Checklist-vs-binary contradictions, in the checked direction only.
        obj = rat.get('MethodologyDescribedYN')
        if isinstance(obj, dict) and isinstance(obj.get('criteria'), dict):
            crit = obj['criteria']
            for key, col in (('harms', 'HarmsAssessed'),
                             ('funding_coi', 'Funding/COI YN'),
                             ('comparator', 'Comparator')):
                if crit.get(key) == 'N' and lib.as_number(a.get(col)) == 1:
                    warnings.append(f"[{sid}] checklist criterion {key}=N but {col}=1 — the "
                                    f"element cannot be present and undescribed")

        if a.get('text_format') == 'text':
            warnings.append(f"[{sid}] read the plain-text fallback — "
                            f"{fmt_note.get(sid) or 'no fidelity note recorded'}")
        if a.get('text_source') == 'OCR':
            warnings.append(f'[{sid}] text_source=OCR — extraction quality is degraded; '
                            f'stratify on this before comparing across eras')

        ret = lib.as_number(a.get('Retention (%)'))
        if ret is not None and abs(ret - 80) <= 2:
            warnings.append(f'[{sid}] Retention (%)={ret} is within 2 points of the 80% '
                            f'threshold, which flips a Table 2 and Table 3 cell')

        yr = lib.as_number(a.get('Year'))
        if yr is not None and yr < 1980:
            for e in [x for x in events if x.get('StudyID') == sid]:
                if e.get('SeveritySource') == 'author':
                    warnings.append(
                        f"[{sid}/{e.get('AE_ID')}] pre-1980 article with SeveritySource=author — "
                        f"CTCAE postdates this literature. Legitimate only if the authors used "
                        f"their own severity language; check the rationale.")

        subs = [c for c in lib.SUBSTANCE_FLAGS if lib.as_number(a.get(c)) == 1]
        if not subs:
            warnings.append(f'[{sid}] no substance flag set — primary_substance() will return '
                            f'"Unknown" and the study renders in fallback grey')

    for sid, disp in dispositions.items():
        if disp == 'auto-ratified':
            p = proposals.get(sid, {})
            warnings.append(f"[{sid}] config entry AUTO-RATIFIED without human review "
                            f"(method={p.get('method')!r}, confidence=clean) — {p.get('note', '')}")

    _blocking, recon_warnings, _info = recon.reconcile(manifest)
    warnings += [f'[reconciliation] {w}' for w in recon_warnings]
    return warnings


# ── Config-proposal partitioning (design §5.3) ───────────────────────────

def load_frozen_rules(condition: str) -> dict:
    """CONVERSION_RULES from the currently committed per-condition config."""
    import importlib
    try:
        cfg = importlib.import_module(f'_config_{CONFIG_BY_CONDITION[condition]}')
    except (ImportError, KeyError):
        return {}
    return getattr(cfg, 'CONVERSION_RULES', {})


def partition_proposals(articles: list[dict], proposals: dict) -> dict[str, str]:
    """Assign each proposal one of auto-ratified / carried-forward / pending."""
    dispositions: dict[str, str] = {}
    for a in articles:
        sid = a.get('StudyID', '<unknown>')
        p = proposals.get(sid, {})
        if not p:
            dispositions[sid] = 'pending'
            continue
        rules = load_frozen_rules(a.get('Condition', ''))
        yr = lib.as_number(a.get('Year'))
        key = (first_author_surname(a.get('Citation/Title', '')), int(yr)) if yr else None
        old = rules.get(key) if key else None

        if old is not None and old.get('method') == p.get('method') \
                and old.get('confidence') == p.get('confidence'):
            dispositions[sid] = 'carried-forward'
        elif p.get('confidence') == 'clean':
            dispositions[sid] = 'auto-ratified'
        else:
            dispositions[sid] = 'pending'
    return dispositions


def write_config_proposals(articles: list[dict], proposals: dict, dispositions: dict,
                           out_dir: Path) -> None:
    """One annotated .py per condition, for apply_config_proposals.py to read."""
    target = out_dir / 'config_proposals'
    target.mkdir(parents=True, exist_ok=True)

    by_condition: dict[str, list[dict]] = {c: [] for c in CONFIG_BY_CONDITION}
    for a in articles:
        by_condition.setdefault(a.get('Condition', 'Unknown'), []).append(a)

    for condition, rows in by_condition.items():
        if condition not in CONFIG_BY_CONDITION:
            continue
        frozen = load_frozen_rules(condition)
        lines = [
            f'"""Model-proposed config entries for {condition} — NOT yet applied.',
            '',
            'Generated by merge_validate.py. Each entry is annotated with its',
            'disposition (design §5.3):',
            '',
            '  auto-ratified   proposed confidence=clean; applied without human review',
            '  carried-forward matches the frozen entry on method and confidence; the',
            "                  frozen entry's note and direction are kept verbatim",
            '  pending         needs a human decision before it is applied',
            '',
            'apply_config_proposals.py merges the first two into',
            'scripts/_config_<condition>.py and leaves pending ones out.',
            '"""',
            '',
            'PROPOSALS = {',
        ]
        for a in sorted(rows, key=lambda r: r.get('StudyID', '')):
            sid = a.get('StudyID', '')
            p = proposals.get(sid, {})
            yr = lib.as_number(a.get('Year'))
            key = (first_author_surname(a.get('Citation/Title', '')), int(yr)) if yr else None
            disp = dispositions.get(sid, 'pending')
            lines.append(f'    # {sid}  [{disp}]  eligible={a.get("EligibleYN")}')
            if disp == 'pending' and key in frozen:
                lines.append(f'    #   frozen:   {frozen[key]!r}')
                lines.append(f'    #   proposed: method={p.get("method")!r}, '
                             f'confidence={p.get("confidence")!r}')
            lines.append(f'    {key!r}: {{')
            for field in ('metric', 'measure', 'method', 'df_error', 'direction',
                          'confidence', 'note', 'tier2_category', 'tier2_basis', 'computed_or'):
                if field in p:
                    lines.append(f'        {field!r}: {p[field]!r},')
            lines.append(f'        {"_disposition"!r}: {disp!r},')
            lines.append('    },')
        lines += ['}', '']
        (target / f'{CONFIG_BY_CONDITION[condition]}.py').write_text(
            '\n'.join(lines), encoding='utf-8')


# ── Output writers ───────────────────────────────────────────────────────

def build_review_queue(articles: list[dict], events: list[dict], rat_article: dict,
                       proposals: dict, dispositions: dict) -> list[dict]:
    """SeverityIndeterminate=Y rows + ineligible articles + pending proposals."""
    rows: list[dict] = []
    rat_ev_by_study: dict[str, dict] = {}
    for e in events:
        rat_ev_by_study.setdefault(e.get('StudyID'), {})

    for e in events:
        if e.get('SeverityIndeterminate') == 'Y':
            rows.append({
                'kind': 'indeterminate_severity',
                'StudyID': e.get('StudyID'),
                'ref': e.get('AE_ID'),
                'detail': f"{e.get('Description')} [graded {e.get('Severity')}]",
            })
    for a in articles:
        if a.get('EligibleYN') == 'N':
            rows.append({
                'kind': 'ineligible_study',
                'StudyID': a.get('StudyID'),
                'ref': a.get('EligibilityFailedCriterion'),
                'detail': a.get('EligibilityNote'),
            })
    for sid, disp in dispositions.items():
        if disp == 'pending':
            p = proposals.get(sid, {})
            rows.append({
                'kind': 'pending_config_proposal',
                'StudyID': sid,
                'ref': f"{p.get('method')}/{p.get('confidence')}",
                'detail': p.get('note', ''),
            })
    return rows


def write_outputs(articles: list[dict], events: list[dict], rat_article: dict,
                  rat_events: dict, proposals: dict, dispositions: dict,
                  out_dir: Path) -> None:
    master = pd.DataFrame(
        [{f: a.get(f) for f in lib.ARTICLE_FIELDS} for a in articles],
        columns=lib.ARTICLE_FIELDS,
    ).sort_values(['Condition', 'StudyID']).reset_index(drop=True)

    # The human adjudication in output.md is a durable layer on top of the raw
    # extraction, not a one-shot edit of the CSV. Re-applying it here means a
    # re-merge cannot silently revert decisions a human already made.
    applied, _, adj_errors = apply_adjudication.apply_to_frame(master)
    if adj_errors:
        raise SystemExit('FATAL: output.md no longer applies cleanly to the merged '
                         'master. Nothing written.\n  ' + '\n  '.join(adj_errors))
    if applied:
        print(f'  Re-applied {len(applied)} adjudicated correction(s) from output.md.')
        pd.DataFrame(applied).to_csv(out_dir / 'adjudication_applied.csv', index=False)

    master.to_csv(out_dir / 'clinical_master.csv', index=False)
    master.to_excel(out_dir / 'clinical_master.xlsx', index=False)

    ae = pd.DataFrame(
        [{f: e.get(f) for f in lib.AE_EVENT_FIELDS} for e in events],
        columns=lib.AE_EVENT_FIELDS,
    )
    if not ae.empty:
        ae = ae.sort_values(['StudyID', 'AE_ID'])
    ae.to_csv(out_dir / 'ae_events.csv', index=False)

    queue = build_review_queue(articles, events, rat_article, proposals, dispositions)
    pd.DataFrame(queue, columns=['kind', 'StudyID', 'ref', 'detail']).to_csv(
        out_dir / 'human_review_queue.csv', index=False)

    lines = ['# Rationale Log', '',
             'Every non-obvious call in the extraction, per article and per adverse event.',
             'Split out of the `rationale` half of each archived response at merge time.', '']
    for a in sorted(articles, key=lambda r: r.get('StudyID', '')):
        sid = a.get('StudyID', '<unknown>')
        lines += [f'## {sid}', '', f"*{a.get('Condition')} · {a.get('Year')} · "
                                   f"eligible={a.get('EligibleYN')} · "
                                   f"config={dispositions.get(sid, '?')}*", '']
        art = rat_article.get(sid, {})
        if art:
            lines.append('### Article')
            for field, reason in art.items():
                if isinstance(reason, dict):
                    crit = reason.get('criteria', {})
                    met = [k for k, v in crit.items() if v == 'Y']
                    unmet = [k for k, v in crit.items() if v == 'N']
                    lines.append(f"- **{field}**: {reason.get('n_met')}/14 met. "
                                 f"Unmet: {', '.join(unmet) or 'none'}. {reason.get('note', '')}")
                    del met
                else:
                    lines.append(f'- **{field}**: {reason}')
            lines.append('')
        ev = rat_events.get(sid, {})
        if ev:
            lines.append('### Adverse events')
            for aeid, reason in ev.items():
                lines.append(f'- **{aeid}**: {reason}')
            lines.append('')
        prop = proposals.get(sid, {})
        if prop:
            lines += ['### Config proposal',
                      f"- **disposition**: {dispositions.get(sid, '?')}",
                      f"- **metric / method / confidence**: {prop.get('metric')!r} / "
                      f"{prop.get('method')!r} / {prop.get('confidence')!r}",
                      f"- **note**: {prop.get('note', '')}", '']
    (out_dir / 'rationale_log.md').write_text('\n'.join(lines), encoding='utf-8')

    write_config_proposals(articles, proposals, dispositions, out_dir)


def write_report(failures: list[str], warnings: list[str], n_articles: int,
                 n_events: int, dispositions: dict, out_dir: Path) -> None:
    lines = ['Clinical-Trial Extraction — Validation Report', '=' * 44, '',
             f'Articles parsed:  {n_articles}',
             f'AE events parsed: {n_events}', '']
    if dispositions:
        counts: dict[str, int] = {}
        for d in dispositions.values():
            counts[d] = counts.get(d, 0) + 1
        lines.append('Config proposals: ' +
                     '  '.join(f'{k}={v}' for k, v in sorted(counts.items())))
        lines.append('')
    lines.append('Gate coverage: design §8 checks 1-10 and 12 run here. Checks 11 and 13 run')
    lines.append('in gate_rebuild.py (they need the ratified config); check 14 runs in')
    lines.append('visual_regression.py (it needs the rebuilt artifacts).')
    lines.append('')
    if failures:
        lines += [f'VALIDATION FAILED — {len(failures)} blocking issue(s). Merge blocked; no '
                  f'output tables were written.', '']
        lines += [f'  - {f}' for f in failures]
    else:
        lines.append('VALIDATION PASSED — 0 blocking issues. Output tables written.')
    lines.append('')
    if warnings:
        lines += [f'WARNINGS — {len(warnings)} (non-blocking; read before publication):', '']
        lines += [f'  - {w}' for w in warnings]
        lines.append('')
    (out_dir / 'validation_report.txt').write_text('\n'.join(lines), encoding='utf-8')


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Merge raw_responses/ into outputs/ and run the validation gate.')
    parser.add_argument('--raw-dir', default='raw_responses')
    parser.add_argument('--out-dir', default='outputs')
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    raw_dir = raw_dir if raw_dir.is_absolute() else _BASE / raw_dir
    out_dir = Path(args.out_dir)
    out_dir = out_dir if out_dir.is_absolute() else _BASE / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print(f'ERROR: raw-dir not found: {raw_dir}', file=sys.stderr)
        sys.exit(1)
    if not MANIFEST.exists():
        print(f'ERROR: manifest not found: {MANIFEST}', file=sys.stderr)
        sys.exit(1)

    manifest = pd.read_csv(MANIFEST, dtype=str, keep_default_na=False)
    articles, events, rat_article, rat_events, proposals, load_failures = load_responses(raw_dir)

    dispositions = partition_proposals(articles, proposals)
    failures = load_failures + validate_all(articles, events, rat_article, proposals,
                                            manifest, raw_dir)
    warnings = collect_warnings(articles, events, rat_article, proposals, dispositions, manifest)

    write_report(failures, warnings, len(articles), len(events), dispositions, out_dir)

    if failures:
        print(f"VALIDATION FAILED — {len(failures)} issue(s). "
              f"See {out_dir / 'validation_report.txt'}")
        for f in failures[:40]:
            print(f'  - {f}')
        if len(failures) > 40:
            print(f'  … and {len(failures) - 40} more (full list in the report).')
        sys.exit(1)

    write_outputs(articles, events, rat_article, rat_events, proposals, dispositions, out_dir)

    # Re-stamp the report after the tables so it is the newest artifact.
    # run_pipeline.py's freshness check reads "master newer than report" as
    # "the master changed after the gate last passed", which is true only if
    # the report is written last.
    write_report(failures, warnings, len(articles), len(events), dispositions, out_dir)

    print(f'VALIDATION PASSED. {len(articles)} article(s), {len(events)} ae_event(s) merged.')
    if warnings:
        print(f'WARNINGS — {len(warnings)} (non-blocking, see validation_report.txt).')
    print(f'Written: clinical_master.csv/.xlsx, ae_events.csv, rationale_log.md, '
          f'human_review_queue.csv, config_proposals/, validation_report.txt -> {out_dir}')


if __name__ == '__main__':
    main()
