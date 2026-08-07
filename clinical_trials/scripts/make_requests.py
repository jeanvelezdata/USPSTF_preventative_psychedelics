"""Write the immutable per-article request archive (design §1.4).

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/make_requests.py

Writes raw_responses/{StudyID}_request.json for every manifest row: the pinned
prompt and rubric versions, the exact converted text the subagent will see
(path + SHA-256), the model and sampling parameters, and the identity the
subagent must echo back.

Generating these deterministically here — rather than letting each subagent
write its own — is what makes the SHA-256 check in merge_validate.py mean
something: the hash is taken of the file as it stood when the request was
built, so a text file edited after extraction is detectable.

Nothing in an orchestrated run archives itself. This is the archive.

**Temperature.** The design specifies temperature 0. Claude Code subagents do
not expose a sampling-temperature control, so the recorded value is the
harness default, not a configured 0, and `temperature_configured` records
that plainly. Writing 0 here would be a fabricated provenance value.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_SCRIPTS = Path(__file__).parent
_BASE    = _SCRIPTS.parent
sys.path.insert(0, str(_SCRIPTS))

import _lib as lib  # noqa: E402

MANIFEST = _BASE / 'inputs' / 'manifest.csv'
TEXT_DIR = _BASE / 'inputs' / 'text'
PROMPT   = _BASE / 'prompts' / 'clinical_extraction_prompt_v1_1.md'
RUBRIC   = _BASE / 'prompts' / 'severity_rubric_v1.md'
RAW_DIR  = _BASE / 'raw_responses'


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not MANIFEST.exists():
        sys.exit(f'ERROR: {MANIFEST} not found. Run convert_pdfs.py first.')
    if not PROMPT.exists():
        sys.exit(f'ERROR: pinned prompt not found at {PROMPT}.')
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(MANIFEST, dtype=str, keep_default_na=False)
    prompt_sha = sha256_file(PROMPT)
    rubric_sha = sha256_file(RUBRIC) if RUBRIC.exists() else None
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')

    written, missing = 0, []
    for _, r in manifest.iterrows():
        sid = r['StudyID']
        if not sid:
            missing.append(f"{r['pdf_path']}: no StudyID — run reconcile_manifest.py")
            continue
        ext = '.md' if r['text_format'] == 'markdown' else '.txt'
        text_path = TEXT_DIR / f'{sid}{ext}'
        if not text_path.exists():
            missing.append(f'{sid}: no converted text at {text_path.name}')
            continue

        request = {
            'StudyID':       sid,
            'Condition':     r['Condition'],
            'surname_token': r['surname'],
            'Year':          int(r['year']),
            'citation_manifest': r['citation'],
            'SourcePDF':     r['pdf_path'],
            'text_path':     str(text_path.relative_to(_BASE.parent)).replace('\\', '/'),
            'text_sha256':   sha256_file(text_path),
            'text_source':   r['text_source'],
            'text_format':   r['text_format'],
            'fidelity_note': r['fidelity_note'],
            'prompt_path':   str(PROMPT.relative_to(_BASE.parent)).replace('\\', '/'),
            'prompt_sha256': prompt_sha,
            'rubric_sha256': rubric_sha,
            'Model':          lib.MODEL,
            'PromptVersion':  lib.PROMPT_VERSION,
            'RubricVersion':  lib.RUBRIC_VERSION,
            'Temperature':    1,
            'temperature_configured': (
                'no — Claude Code subagents expose no sampling-temperature control, so this '
                'is the harness default rather than the design\'s configured 0. Recorded '
                'honestly rather than as a 0 that never happened.'),
            'requested_utc': stamp,
        }
        (RAW_DIR / f'{sid}_request.json').write_text(
            json.dumps(request, indent=2, ensure_ascii=False), encoding='utf-8')
        written += 1

    print(f'Wrote {written} request archive(s) to {RAW_DIR}')
    if missing:
        print(f'\n{len(missing)} row(s) skipped:')
        for m in missing:
            print(f'  - {m}')
        sys.exit(1)


if __name__ == '__main__':
    main()
