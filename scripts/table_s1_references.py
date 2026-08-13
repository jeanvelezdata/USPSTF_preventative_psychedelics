"""
Supplementary Table S1 — references for every study in the final analysis.

One combined table of the 42 eligible clinical trials plus the 33 observational
studies, grouped by condition and alphabetical within each, with a study-type,
condition, and substance column alongside the full reference.

Inputs:
    clinical_trials/outputs/clinical_master.csv       (rows with EligibleYN == 'Y')
    observational_studies/outputs/articles.csv        (deduplicated on StudyID)
    observational_studies/inputs/text/<StudyID>.txt   (author lists, where truncated)

Output:
    tables/TableS1_References.docx

Usage:
    python scripts/table_s1_references.py

Citation strings are normalised to APA punctuation, never invented. The
observational source stores Vancouver-style citations, 13 of which truncated the
author list to "et al."; those author lists were read off the article front
matter in inputs/text/ and are recorded in AUTHOR_RECOVERY below, together with
whatever volume and page numbers the same front matter states. References whose
source text carries no volume or page numbers (online-first PDFs, mostly) are
left without them and flagged in the footnotes rather than filled in.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt

_BASE    = Path(__file__).parent.parent
_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import descriptive_analyses as da  # noqa: E402  (docx styling helpers)

CLINICAL     = _BASE / 'clinical_trials' / 'outputs' / 'clinical_master.csv'
OBSERVATIONAL = _BASE / 'observational_studies' / 'outputs' / 'articles.csv'
OUTPUT       = _BASE / 'tables' / 'TableS1_References.docx'

# Substance flag columns in clinical_master.csv, in display order.
# MultiplePsychedelic is a marker for "more than one of the above", not a
# substance, so it is not printed.
SUBSTANCE_FLAGS = [
    ('Psilocybin', 'Psilocybin'),
    ('Ayahuasca',  'Ayahuasca'),
    ('LSD',        'LSD'),
    ('Mescaline',  'Mescaline'),
    ('Ibogaine',   'Ibogaine'),
    ('MDMA',       'MDMA'),
    ('Ketamine',   'Ketamine'),
    ('Cannabis',   'Cannabis'),
    ('OtherPsychedelic', 'Other psychedelic'),
]

# Four clinical citations store the first author as "Initials Surname" instead
# of "Surname, Initials." Same name, APA word order.
LEAD_AUTHOR_FIXES = {
    'D.C. Mash,':  'Mash, D. C.,',
    'Jovaisa T,':  'Jovaisa, T.,',
    'P. Glue,':    'Glue, P.,',
    'Johnson MW,': 'Johnson, M. W.,',
}

# The observational corpus labels tobacco studies inconsistently; the clinical
# corpus and the manuscript both use "Smoking".
CONDITION_ALIASES = {'Tobacco': 'Smoking'}
CONDITION_ORDER = ['Alcohol', 'Smoking', 'Opioid']

# Bibliographic detail read off the article front matter in
# observational_studies/inputs/text/<StudyID>.txt, keyed by StudyID as
# (author_list, volume_and_pages).
#
# author_list is None where articles.csv already carries the full list; it is
# filled in for the 13 citations articles.csv abbreviates to "<First author>,
# et al." volume_and_pages is None where the source text states none — an
# online-first PDF, or a scan whose OCR mangled the header beyond reading.
# Nothing here is filled in from outside the source text.
FRONT_MATTER = {
    'Agin-Liebes 2021': (
        'Agin-Liebes, G., Haas, T. F., Lancelotta, R., Uthaug, M. V., '
        'Ramaekers, J. G., & Davis, A. K.', '4, 543-552'),
    'Alper 1999':    (None, '8, 234-242'),
    'Alper 2012':    (None, '57(2), 398-412'),
    'Anderson 2019': (
        'Anderson, T., Petranker, R., Christopher, A., Rosenbaum, D., '
        'Weissman, C., Dinh-Williams, L.-A., Hui, K., & Hapke, E.', '16, 43'),
    'Armstrong 2024': (None, '36(2), 184-191'),
    'Barbosa 2018': (
        'Barbosa, P. C. R., Tófoli, L. F., Bogenschutz, M. P., Hoy, R., '
        'Berro, L. F., Marinho, E. A. V., Areco, K. N., & Winkelman, M. J.', '9, 136'),
    # Barrett 1999: the PDF uses a shifted glyph encoding, so every digit in its
    # header is unreliable. Left blank rather than decoded.
    'Barrett 1999':  (None, None),
    'Berlowitz 2019': (None, None),
    'Brown 2018':    (None, '44(1), 24-36'),
    'Brown 2019':    (None, '51(2), 155-165'),
    # Chwelos 1959: page footers give 577-590, but the volume number is garbled
    # in the scan, so the locator would be incomplete either way.
    'Chwelos 1959':  (None, None),
    'Davis 2017':    (None, '1(2), 65-73'),
    'Davis 2018':    (None, '50(4), 287-297'),
    'Doering-Silveira 2005': (
        'Doering-Silveira, E., Grob, C. S., Dobkin de Rios, M., Lopez, E., '
        'Alonso, L. K., Tacla, C., & Da Silveira, D. X.', '37(2), 141-144'),
    'Fabregas 2010': (
        'Fábregas, J. M., González, D., Fondevila, S., Cutchet, M., '
        'Fernández, X., Barbosa, P. C. R., Alcázar-Córcoles, M. Á., '
        'Barbanoj, M. J., Riba, J., & Bouso, J. C.', '111, 257-261'),
    'Faillace 1970': (None, '11(1), 51-56'),
    'Garcia-Romeu 2019': (
        'Garcia-Romeu, A., Davis, A. K., Erowid, F., Erowid, E., '
        'Griffiths, R. R., & Johnson, M. W.', None),
    'Greer 1986':    (None, '18(4), 319-327'),
    'Johnson 2017':  (None, '31(7), 841-850'),
    'Jones 2022':    (None, '12, 4099'),
    'Jones 2022 b':  (None, '12, 10578'),
    'Jones 2025':    (None, '20(5), e0321461'),
    'Kolp 2006':     (None, '34(4), 399-422'),
    'Lawn 2017': (
        'Lawn, W., Hallak, J. E., Crippa, J. A., Dos Santos, R., Porffy, L., '
        'Barratt, M. J., Ferris, J. A., Winstock, A. R., & Morgan, C. J. A.', '7, 15201'),
    'Malcolm 2018': (
        'Malcolm, B. J., Polanco, M., & Barsuglia, J. P.', None),
    'Noller 2018':   (None, '44(1), 37-46'),
    'Noorani 2018': (
        'Noorani, T., Garcia-Romeu, A., Swift, T. C., Griffiths, R. R., '
        '& Johnson, M. W.', None),
    'Perkins 2022': (
        'Perkins, D., Opaleye, E., Simonova, H., Bouso, J. C., Tófoli, L. F., '
        'Galvão-Coelho, N. L., Schubert, V., & Sarris, J.', None),
    'Pisano 2017': (
        'Pisano, V. D., Putnam, N. P., Kramer, H. M., Franciotti, K. J., '
        'Halpern, J. H., & Holden, S. C.', '31(5), 606-613'),
    # Rydzynski 1978: taken from the interlibrary-loan slip bound into the scan,
    # the only place in the source text stating volume, issue, and pages.
    'Rydzynski 1978': (None, '20(1), 81-82'),
    'Sarett 1966':   (None, None),
    'Thomas 2013': (
        'Thomas, G., Lucas, P., Capler, N. R., Tupper, K. W., & Martin, G.', '6, 30-42'),
    'Wong 2014': (
        'Wong, A., Benedict, N. J., Armahizer, M. J., & Kane-Gill, S. L.', None),
}


def vancouver_to_apa(citation: str, study_id: str) -> tuple[str, bool]:
    """Convert 'Authors. Title. Journal. Year.' to APA.

    FRONT_MATTER supplies the author list where articles.csv truncates it, and
    the volume/page numbers wherever the source text states them. Returns the
    converted string and whether it carries volume/page numbers.
    """
    segments = re.split(r'\.\s+', citation.strip().rstrip('.'))
    if len(segments) < 4:
        raise ValueError(f'unparseable citation: {citation!r}')

    authors, year, journal = segments[0], segments[-1], segments[-2]
    title = '. '.join(segments[1:-2])
    if not re.fullmatch(r'\d{4}', year):
        raise ValueError(f'no trailing year in citation: {citation!r}')

    truncated = 'et al' in authors
    recovered_authors, pages = FRONT_MATTER.get(study_id, (None, None))
    if truncated and recovered_authors is None:
        raise ValueError(f'{study_id} truncates its author list but FRONT_MATTER '
                         f'supplies no replacement')
    if recovered_authors is not None and not truncated:
        raise ValueError(f'{study_id} already has a full author list; drop the '
                         f'author half of its FRONT_MATTER entry')

    locator = f'{journal}, {pages}' if pages else journal
    if recovered_authors is not None:
        return f'{recovered_authors} ({year}). {title}. {locator}.', pages is not None

    names = []
    for token in authors.split(','):
        token = token.strip()
        if token.startswith('et al'):
            names.append('et al.')
            continue
        # 'Alper KR' -> 'Alper, K. R.'; hyphenated surnames stay intact.
        match = re.fullmatch(r"(.+?)\s+([A-Z]{1,4})", token)
        if not match:
            raise ValueError(f'unparseable author {token!r} in {citation!r}')
        surname, initials = match.groups()
        names.append(f'{surname}, ' + ' '.join(f'{i}.' for i in initials))

    if len(names) == 1:
        author_str = names[0]
    elif names[-1] == 'et al.':
        author_str = ', '.join(names)
    else:
        author_str = ', '.join(names[:-1]) + ', & ' + names[-1]

    return f'{author_str} ({year}). {title}. {locator}.', pages is not None


def normalise_clinical(citation: str) -> str:
    """Clinical citations are already APA; only the lead author needs fixing."""
    for wrong, right in LEAD_AUTHOR_FIXES.items():
        if citation.startswith(wrong):
            return right + citation[len(wrong):]
    return citation


TYPE_ORDER = ['Clinical trial', 'Observational']


def sort_key(entry: dict) -> tuple[int, str]:
    """Study type first (clinical trials, then observational), then surname."""
    surname = entry['reference'].split(',')[0].split('(')[0].strip()
    # Fold accents first, so Fábregas sorts as "fabregas" rather than "fbregas".
    folded = unicodedata.normalize('NFKD', surname.lower())
    return TYPE_ORDER.index(entry['type']), re.sub(r'[^a-z]', '', folded)


def load_clinical() -> list[dict]:
    df = pd.read_csv(CLINICAL)
    df = df[df['EligibleYN'].astype(str).str.strip() == 'Y']

    entries = []
    for _, row in df.iterrows():
        substances = [label for col, label in SUBSTANCE_FLAGS
                      if str(row[col]).strip() in ('1', '1.0')]
        if not substances:
            raise ValueError(f"no substance flag set for {row['StudyID']}")
        entries.append({
            'reference': normalise_clinical(str(row['Citation/Title']).strip()),
            'type': 'Clinical trial',
            'condition': CONDITION_ALIASES.get(row['Condition'], row['Condition']),
            'substance': ', '.join(substances),
            'has_pages': True,
        })
    return entries


def load_observational() -> list[dict]:
    df = pd.read_csv(OBSERVATIONAL)

    entries = []
    for study_id, group in df.groupby('StudyID', sort=False):
        citations = group['Citation'].unique()
        if len(citations) != 1:
            raise ValueError(f'conflicting citations for {study_id}: {citations}')

        # A study appears once per condition it contributes to (e.g. Thomas 2013
        # covers alcohol, tobacco, and opioid); collapse to one reference row.
        conditions = {CONDITION_ALIASES.get(c, c) for c in group['Condition']}
        ordered = [c for c in CONDITION_ORDER if c in conditions]
        ordered += sorted(conditions - set(CONDITION_ORDER))

        substances = group['Substance'].dropna().unique()
        reference, has_pages = vancouver_to_apa(str(citations[0]), study_id)
        entries.append({
            'reference': reference,
            'type': 'Observational',
            'condition': ', '.join(ordered),
            'substance': '; '.join(str(s).strip() for s in substances),
            'has_pages': has_pages,
        })
    return entries


def main() -> None:
    clinical = load_clinical()
    observational = load_observational()
    print(f'Clinical trials: {len(clinical)}   Observational: {len(observational)}')

    entries = sorted(clinical + observational, key=sort_key)
    no_pages = [e for e in observational if not e['has_pages']]

    header = ['#', 'Reference', 'Study type', 'Condition', 'Substance(s)']
    rows = [header] + [
        [str(i), e['reference'], e['type'], e['condition'], e['substance']]
        for i, e in enumerate(entries, start=1)
    ]

    doc = Document()
    da.configure_document(doc)
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Inches(11), Inches(8.5)

    title = doc.add_paragraph()
    run = title.add_run(f'Table S1. References for all studies included in the '
                        f'final analysis (N = {len(entries)})')
    run.font.name = 'Arial'
    run.bold = True
    run.font.size = Pt(13)

    table = da.add_table(doc, n_rows=len(rows), n_cols=len(header),
                         col_widths_in=[0.35, 4.75, 1.0, 1.0, 1.9])
    for r, row_data in enumerate(rows):
        for c, val in enumerate(row_data):
            da.style_cell(table.cell(r, c), text=val, bold=(r == 0), size=9,
                          align='center' if c == 0 else 'left',
                          shading='D9E2F3' if r == 0 else None)

    da.add_caption(doc, f'Clinical trials (n = {len(clinical)}) are the studies '
                        f'flagged EligibleYN = Y in clinical_master.csv. Observational '
                        f'studies (n = {len(observational)}) are the unique StudyIDs in '
                        f'articles.csv; studies contributing to more than one condition '
                        f'(Anderson 2019, Thomas 2013) appear once, with all conditions listed. '
                        f'Entries are ordered by study type, then alphabetically by first author.')
    n_authors = sum(1 for authors, _ in FRONT_MATTER.values() if authors is not None)
    da.add_caption(doc, f'References follow APA style. articles.csv stores no volume or page '
                        f'numbers and abbreviates {n_authors} author lists to "et al.", so all '
                        f'{len(FRONT_MATTER)} observational source texts in '
                        f'observational_studies/inputs/text/ were read: the {n_authors} missing '
                        f'author lists were recovered in full, and volume and page numbers were '
                        f'recovered for {len(observational) - len(no_pages)} of '
                        f'{len(observational)} references.')
    da.add_caption(doc, f'{len(no_pages)} observational references print without volume or page '
                        f'numbers because their source text states none — online-first PDFs, or '
                        f'scans whose OCR mangled the header. Complete these from the published '
                        f'versions before submission.')
    da.add_caption(doc, 'Generated by scripts/table_s1_references.py.', italic=True)

    doc.save(OUTPUT)
    print(f'Wrote {OUTPUT}')
    for row in rows[1:]:
        print(f'{row[0]:>3}. {row[1]}  [{row[2]} | {row[3]} | {row[4]}]')


if __name__ == '__main__':
    main()
