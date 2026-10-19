"""Deterministic PDF -> Markdown conversion for the clinical-trial corpus (design §1.2).

Usage:
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/convert_pdfs.py
    C:/Users/jeanv/miniforge3/python.exe clinical_trials/scripts/convert_pdfs.py --force

Scans inputs/pdfs/{alcohol,opioids,smoking}/ and converts each PDF through the
§1.2 fallback chain, writing one file per article into inputs/text/ and
registering it in inputs/manifest.csv:

    1. pymupdf4llm.to_markdown()  -> .md   text_source=born-digital, text_format=markdown
    2. Markdown fails a fidelity check -> PyMuPDF page.get_text('text') -> .txt
                                          text_source=born-digital, text_format=text
    3. Plain text < 200 stripped chars (image-only) -> Tesseract @300dpi -> .txt
                                          text_source=OCR,          text_format=text
    4. OCR also < 200 chars -> left unprocessed, done=N, flagged for manual transcription

Markdown is the default tier because headings locate eight of the fourteen
MethodologyDescribedYN criteria and the SafetyReported gate, and because pipe
tables keep Outcome / SD / SampleSize_NFinal attached to their labels.
An article that fails any fidelity check is demoted to plain text rather than
partially accepted — a collapsed table looks structured while silently
re-associating numbers with the wrong row.

Fidelity checks (all four must pass to keep the Markdown):
    1. no text loss   len(md)/len(txt) >= 0.90
    2. no runaway     len(md)/len(txt) <= 1.60
    3. structure      >= 1 ATX heading in the Markdown
    4. tables         if the PDF has >= 1 detected table, the Markdown has >= 1 pipe row

Text files are named by PDF stem at this stage; StudyID is not known until
citation/year are filled in. reconcile_manifest.py renames them to
{StudyID}.{ext} once the metadata pass is complete.

Idempotent: a manifest row whose converted file still exists is skipped unless
--force. Rows whose PDF has been removed are pruned.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd
import pymupdf4llm

_BASE    = Path(__file__).parent.parent
PDF_DIR  = _BASE / 'inputs' / 'pdfs'
TEXT_DIR = _BASE / 'inputs' / 'text'
MANIFEST = _BASE / 'inputs' / 'manifest.csv'

# Manifest schema, design §1.3. citation/year are the human metadata pass;
# StudyID/surname/old_row_match are derived from them by reconcile_manifest.py.
MANIFEST_COLUMNS = [
    'StudyID', 'Condition', 'pdf_path', 'citation', 'surname', 'year',
    'old_row_match', 'text_source', 'text_format', 'fidelity_note', 'done',
]

# inputs/pdfs/ subfolder -> canonical singular Condition label (design §1.3).
CONDITION_BY_FOLDER = {'alcohol': 'Alcohol', 'opioids': 'Opioid', 'smoking': 'Smoking'}

MIN_EXTRACTABLE_CHARS = 200
MIN_MD_RATIO = 0.90
MAX_MD_RATIO = 1.60

_ATX_HEADING = re.compile(r'^#{1,6}\s', re.MULTILINE)
_PIPE_ROW    = re.compile(r'^\s*\|', re.MULTILINE)

try:
    import pytesseract
    from PIL import Image
    # conda-forge installs the binary + tessdata alongside the interpreter, not on PATH.
    _conda_root    = Path(sys.executable).parent
    _tesseract_exe = _conda_root / 'Library' / 'bin' / 'tesseract.exe'
    _tessdata_dir  = _conda_root / 'share' / 'tessdata'
    if _tesseract_exe.exists():
        pytesseract.pytesseract.tesseract_cmd = str(_tesseract_exe)
    if _tessdata_dir.exists():
        os.environ['TESSDATA_PREFIX'] = str(_tessdata_dir)
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


# ── Conversion tiers ─────────────────────────────────────────────────────

def extract_plain(pdf_path: Path) -> str:
    with fitz.open(pdf_path) as doc:
        return '\n\n'.join(page.get_text('text') for page in doc)


def extract_markdown(pdf_path: Path) -> str:
    return pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)


def count_tables(pdf_path: Path) -> int:
    """Number of tables PyMuPDF detects anywhere in the PDF (fidelity check 4)."""
    total = 0
    with fitz.open(pdf_path) as doc:
        for page in doc:
            try:
                total += len(page.find_tables().tables)
            except Exception:
                # Table finding is heuristic and can throw on malformed pages;
                # a page we cannot analyse contributes no expectation.
                continue
    return total


def ocr_text(pdf_path: Path) -> str:
    pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            pages.append(pytesseract.image_to_string(img))
    return '\n\n'.join(pages)


def check_fidelity(md: str, txt: str, n_tables: int) -> str:
    """Return '' if the Markdown passes all four checks, else the failing check."""
    md_len, txt_len = len(md.strip()), len(txt.strip())
    if txt_len == 0:
        return 'check1: plain-text tier produced no text to compare against'
    ratio = md_len / txt_len
    if ratio < MIN_MD_RATIO:
        return f'check1 text-loss: md/txt ratio {ratio:.2f} < {MIN_MD_RATIO}'
    if ratio > MAX_MD_RATIO:
        return f'check2 runaway: md/txt ratio {ratio:.2f} > {MAX_MD_RATIO}'
    if not _ATX_HEADING.search(md):
        return 'check3 structure: no ATX heading recovered'
    if n_tables >= 1 and not _PIPE_ROW.search(md):
        return f'check4 tables: {n_tables} table(s) detected in PDF, 0 pipe rows in Markdown'
    return ''


# ── Manifest ─────────────────────────────────────────────────────────────

def load_manifest() -> pd.DataFrame:
    if MANIFEST.exists():
        df = pd.read_csv(MANIFEST, dtype=str, keep_default_na=False)
        for col in MANIFEST_COLUMNS:
            if col not in df.columns:
                df[col] = ''
        return df[MANIFEST_COLUMNS]
    return pd.DataFrame(columns=MANIFEST_COLUMNS)


def scan_pdfs() -> list[tuple[str, str, Path]]:
    """Return (condition_label, pdf_path_relative_to_pdfs_dir, absolute_path)."""
    found = []
    for folder, label in sorted(CONDITION_BY_FOLDER.items()):
        for pdf in sorted((PDF_DIR / folder).glob('*.pdf')):
            found.append((label, f'{folder}/{pdf.name}', pdf))
    return found


def text_stem(rel_path: str) -> str:
    """Filesystem-safe stem for the converted file, unique across condition folders."""
    folder, name = rel_path.split('/', 1)
    return f'{folder}__{Path(name).stem}'


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description='Convert the clinical PDF corpus to text.')
    parser.add_argument('--force', action='store_true',
                        help='Re-convert every PDF even if its text file already exists.')
    args = parser.parse_args()

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    pdfs = scan_pdfs()
    if not pdfs:
        print(f'No PDFs found under {PDF_DIR}. Nothing to convert.', file=sys.stderr)
        sys.exit(1)

    present = {rel for _, rel, _ in pdfs}
    stale = manifest[~manifest['pdf_path'].isin(present)]
    for rel in stale['pdf_path']:
        print(f'  PRUNED: {rel} no longer under {PDF_DIR}; manifest row removed.')
    manifest = manifest[manifest['pdf_path'].isin(present)].reset_index(drop=True)

    known = set(manifest['pdf_path'])
    new_rows = [
        {**{c: '' for c in MANIFEST_COLUMNS}, 'Condition': label, 'pdf_path': rel, 'done': 'N'}
        for label, rel, _ in pdfs if rel not in known
    ]
    if new_rows:
        manifest = pd.concat([manifest, pd.DataFrame(new_rows)], ignore_index=True)
        print(f'Registered {len(new_rows)} new PDF(s) in the manifest.')

    abs_by_rel = {rel: path for _, rel, path in pdfs}
    counts = {'markdown': 0, 'text': 0, 'ocr': 0, 'skipped': 0, 'manual': 0}

    for i, row in manifest.iterrows():
        rel = row['pdf_path']
        pdf_path = abs_by_rel[rel]
        stem = text_stem(rel)
        existing = [p for p in (TEXT_DIR / f'{stem}.md', TEXT_DIR / f'{stem}.txt') if p.exists()]

        if existing and row['text_format'] and not args.force:
            counts['skipped'] += 1
            continue
        for p in existing:
            p.unlink()

        txt = extract_plain(pdf_path)
        source, fmt, note = 'born-digital', '', ''

        if len(txt.strip()) < MIN_EXTRACTABLE_CHARS:
            # Tier 3: image-only PDF.
            if not OCR_AVAILABLE:
                manifest.at[i, 'text_source'] = ''
                manifest.at[i, 'text_format'] = ''
                manifest.at[i, 'fidelity_note'] = 'image-only PDF and no OCR engine installed'
                manifest.at[i, 'done'] = 'N'
                counts['manual'] += 1
                print(f'  NEEDS OCR: {rel} — {len(txt.strip())} extractable chars, no Tesseract.')
                continue
            print(f'  OCR: {rel} — {len(txt.strip())} extractable chars; running Tesseract...')
            txt = ocr_text(pdf_path)
            if len(txt.strip()) < MIN_EXTRACTABLE_CHARS:
                manifest.at[i, 'text_source'] = ''
                manifest.at[i, 'text_format'] = ''
                manifest.at[i, 'fidelity_note'] = (
                    f'OCR yielded only {len(txt.strip())} chars; needs manual transcription')
                manifest.at[i, 'done'] = 'N'
                counts['manual'] += 1
                print(f'  NEEDS MANUAL: {rel} — OCR yielded {len(txt.strip())} chars.')
                continue
            # OCR output is always plain text; the Markdown tier does not apply.
            (TEXT_DIR / f'{stem}.txt').write_text(txt, encoding='utf-8')
            source, fmt, note = 'OCR', 'text', 'OCR output; Markdown tier not applicable'
            counts['ocr'] += 1
            print(f'  OK (OCR/text): {rel} -> {stem}.txt ({len(txt)} chars)')
        else:
            try:
                md = extract_markdown(pdf_path)
            except Exception as e:                       # noqa: BLE001 - any converter fault demotes
                md, note = '', f'markdown conversion raised {type(e).__name__}: {e}'
            if md:
                note = check_fidelity(md, txt, count_tables(pdf_path))
            if not note:
                (TEXT_DIR / f'{stem}.md').write_text(md, encoding='utf-8')
                fmt = 'markdown'
                counts['markdown'] += 1
                print(f'  OK (markdown): {rel} -> {stem}.md ({len(md)} chars)')
            else:
                (TEXT_DIR / f'{stem}.txt').write_text(txt, encoding='utf-8')
                fmt = 'text'
                counts['text'] += 1
                print(f'  DEMOTED (text): {rel} -> {stem}.txt ({len(txt)} chars) — {note}')

        manifest.at[i, 'text_source']   = source
        manifest.at[i, 'text_format']   = fmt
        manifest.at[i, 'fidelity_note'] = note

    manifest = manifest.sort_values(['Condition', 'pdf_path']).reset_index(drop=True)
    manifest.to_csv(MANIFEST, index=False)

    print(f"\nMarkdown: {counts['markdown']} | demoted to text: {counts['text']} | "
          f"OCR: {counts['ocr']} | skipped (already converted): {counts['skipped']} | "
          f"needs manual: {counts['manual']}")
    print(f'Manifest written: {MANIFEST} ({len(manifest)} row(s)).')
    print('\nNext: fill the citation and year columns (the human metadata pass, §1.3), '
          'then run reconcile_manifest.py.')


if __name__ == '__main__':
    main()
