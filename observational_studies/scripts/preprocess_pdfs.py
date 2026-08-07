"""Deterministic PDF -> text preprocessing for the AE/demographics corpus.

Usage:
    C:/Users/jeanv/miniforge3/python.exe aedemographics_extraction/scripts/preprocess_pdfs.py

Scans inputs/pdfs/ for *.pdf files not yet extracted, converts each to a
.txt file in inputs/text/ via PyMuPDF, and writes/updates inputs/manifest.csv
(StudyID, filename, citation, year, text_source, done). Idempotent: a PDF
whose manifest row is already done=Y and whose .txt file still exists is
skipped on re-run, so an interrupted or repeated run only processes what's
left. Manifest rows whose PDF has been removed from inputs/pdfs/ are pruned
on each run.

If born-digital extraction yields near-zero text (image-only/scanned PDF),
falls back to OCR via Tesseract (rendered per-page at 300dpi through
PyMuPDF, then pytesseract). OCR requires the Tesseract binary installed
separately from pip (here: `conda install -c conda-forge tesseract`) — if
it's unavailable, the PDF is flagged for manual transcription instead of
guessed at. Citation and Year are not derivable from the PDF alone; they
are left blank in the manifest for a metadata-backfill step to populate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd

_BASE      = Path(__file__).parent.parent
PDF_DIR    = _BASE / 'inputs' / 'pdfs'
TEXT_DIR   = _BASE / 'inputs' / 'text'
MANIFEST   = _BASE / 'inputs' / 'manifest.csv'

MANIFEST_COLUMNS = ['StudyID', 'filename', 'citation', 'year', 'text_source', 'done']

# Below this total extracted-character count, treat a PDF as image-only
# (scanned) rather than born-digital, and fall back to OCR.
MIN_EXTRACTABLE_CHARS = 200

try:
    import os

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


def load_manifest() -> pd.DataFrame:
    if MANIFEST.exists():
        df = pd.read_csv(MANIFEST, dtype=str, keep_default_na=False)
        for col in MANIFEST_COLUMNS:
            if col not in df.columns:
                df[col] = ''
        return df[MANIFEST_COLUMNS]
    return pd.DataFrame(columns=MANIFEST_COLUMNS)


def extract_text(pdf_path: Path) -> str:
    with fitz.open(pdf_path) as doc:
        return '\n\n'.join(page.get_text('text') for page in doc)


def ocr_text(pdf_path: Path) -> str:
    """Render each page at 300dpi and run Tesseract OCR over it."""
    pages = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            pages.append(pytesseract.image_to_string(img))
    return '\n\n'.join(pages)


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    pdf_files = sorted(PDF_DIR.glob('*.pdf'))

    if not pdf_files:
        print(f"No PDFs found in {PDF_DIR}. Nothing to process.")
        manifest.to_csv(MANIFEST, index=False)
        print(f"Manifest written: {MANIFEST} ({len(manifest)} row(s)).")
        return

    pdf_filenames = {p.name for p in pdf_files}
    stale = manifest[~manifest['filename'].isin(pdf_filenames)]
    if len(stale):
        for name in stale['filename']:
            print(f"  PRUNED: {name} no longer in {PDF_DIR}; removed from manifest.")
        manifest = manifest[manifest['filename'].isin(pdf_filenames)].reset_index(drop=True)

    known_filenames = set(manifest['filename'])
    new_rows = []
    for pdf_path in pdf_files:
        if pdf_path.name not in known_filenames:
            new_rows.append({
                'StudyID':     pdf_path.stem,
                'filename':    pdf_path.name,
                'citation':    '',
                'year':        '',
                'text_source': '',
                'done':        'N',
            })
    if new_rows:
        manifest = pd.concat([manifest, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"Registered {len(new_rows)} new PDF(s) in manifest.")

    n_processed = 0
    n_ocr = 0
    n_skipped = 0
    n_needs_manual = 0
    for i, row in manifest.iterrows():
        pdf_path = PDF_DIR / row['filename']
        txt_path = TEXT_DIR / f"{row['StudyID']}.txt"

        if row['done'] == 'Y' and txt_path.exists():
            n_skipped += 1
            continue
        if not pdf_path.exists():
            print(f"  WARNING: {row['filename']} listed in manifest but missing from {PDF_DIR}; skipping.")
            continue

        text = extract_text(pdf_path)
        source = 'born-digital'

        if len(text.strip()) < MIN_EXTRACTABLE_CHARS:
            if not OCR_AVAILABLE:
                manifest.at[i, 'text_source'] = ''
                manifest.at[i, 'done'] = 'N'
                n_needs_manual += 1
                print(f"  NEEDS OCR: {row['filename']} — only {len(text.strip())} extractable chars; "
                      f"likely scanned/image-only, and no OCR engine is installed. Left unprocessed.")
                continue
            print(f"  OCR: {row['filename']} — only {len(text.strip())} extractable chars; running Tesseract...")
            text = ocr_text(pdf_path)
            source = 'OCR'
            if len(text.strip()) < MIN_EXTRACTABLE_CHARS:
                manifest.at[i, 'text_source'] = ''
                manifest.at[i, 'done'] = 'N'
                n_needs_manual += 1
                print(f"  NEEDS MANUAL: {row['filename']} — OCR also yielded only {len(text.strip())} chars "
                      f"(likely poor scan quality). Left unprocessed for manual transcription.")
                continue
            n_ocr += 1

        txt_path.write_text(text, encoding='utf-8')
        manifest.at[i, 'text_source'] = source
        manifest.at[i, 'done'] = 'Y'
        n_processed += 1
        print(f"  OK ({source}): {row['filename']} -> {txt_path.name} ({len(text)} chars)")

    manifest = manifest.sort_values('StudyID').reset_index(drop=True)
    manifest.to_csv(MANIFEST, index=False)

    print(f"\nProcessed: {n_processed} (of which {n_ocr} via OCR) | "
          f"Skipped (already done): {n_skipped} | Needs manual: {n_needs_manual}")
    print(f"Manifest written: {MANIFEST} ({len(manifest)} row(s)).")


if __name__ == '__main__':
    main()
