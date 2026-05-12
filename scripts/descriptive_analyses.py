"""
Descriptive analyses for psychedelic-trial datasets, output to per-condition .docx files.

Inputs:
    <Condition>_Dataset_Cleaned.xlsx   (output of clean_dataset.py --condition <c>)

Outputs:
    <Condition>_Descriptive_Analyses.docx   five tables for the manuscript:
        Table 1. Study Characteristics, stratified by era
        Table 2. Methodological Quality, stratified by era
        Table 3. USPSTF Indicator Gap Heat Map (52 indicators across 6 domains)
        Table 4. Outcomes Measured, stratified by era
        Table 5. Follow-up Duration Distribution

Usage:
    python descriptive_analyses.py [--condition alcohol|smoking|all]

Coding conventions:
- "% met" = proportion of all studies in the stratum where the criterion is
  positively documented. Missing/not-reported is treated as not met (strict
  USPSTF gap interpretation; documented in each table footnote).
- Era split: Pre-1980 vs. 2010+. The 1980-2009 gap is empty for both conditions.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

_BASE = Path(__file__).parent.parent

CONDITION_META: dict[str, dict] = {
    'alcohol': {'short': 'Alcohol', 'disorder': 'Alcohol Use Disorder'},
    'smoking': {'short': 'Smoking', 'disorder': 'Tobacco/Smoking Cessation'},
    'opioid':  {'short': 'Opioid',  'disorder': 'Opioid Use Disorder'},
}
AVAILABLE_CONDITIONS = ['alcohol', 'smoking', 'opioid']


# =============================================================================
# Stats helpers
# =============================================================================

def to_numeric_strict(series: pd.Series) -> pd.Series:
    """Coerce a possibly-mixed binary column to numeric, treating 'Does not
    apply' as missing."""
    return pd.to_numeric(series, errors='coerce')


def pct_met(series: pd.Series, total_n: int) -> float:
    """Strict % of `total_n` studies where binary value == 1.
    Missing or 'Does not apply' counts as not met."""
    s = to_numeric_strict(series)
    return 100.0 * (s == 1).sum() / total_n if total_n else float('nan')


def pct_reported(series: pd.Series, total_n: int) -> float:
    """% of `total_n` studies with a non-null value (any value reported)."""
    return 100.0 * series.notna().sum() / total_n if total_n else float('nan')


def median_iqr(series: pd.Series) -> str:
    """Format median (IQR) string for a numeric series; '—' if empty."""
    s = pd.to_numeric(series, errors='coerce').dropna()
    if s.empty:
        return '—'
    med = s.median()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    if abs(med - round(med)) < 0.05 and abs(q1 - round(q1)) < 0.05 and abs(q3 - round(q3)) < 0.05:
        return f"{med:.0f} ({q1:.0f}–{q3:.0f})"
    return f"{med:.1f} ({q1:.1f}–{q3:.1f})"


def mean_sd_n(series: pd.Series) -> str:
    """Format mean (SD), n=k for a numeric series."""
    s = pd.to_numeric(series, errors='coerce').dropna()
    if s.empty:
        return '— (n=0)'
    return f"{s.mean():.1f} ({s.std():.1f}), n={len(s)}"


def n_pct(count: int, total: int) -> str:
    if total == 0:
        return '0 (—)'
    return f"{count} ({100*count/total:.0f}%)"


# =============================================================================
# docx styling helpers
# =============================================================================

def set_cell_shading(cell, hex_color: str) -> None:
    """Apply a clear (non-pattern) background fill to a cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn('w:shd')):
        tc_pr.remove(old)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tc_pr.append(shd)


def set_cell_borders(cell, color: str = 'BFBFBF', size: int = 4) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn('w:tcBorders')):
        tc_pr.remove(old)
    borders = OxmlElement('w:tcBorders')
    for side in ('top', 'left', 'bottom', 'right'):
        b = OxmlElement(f'w:{side}')
        b.set(qn('w:val'), 'single')
        b.set(qn('w:sz'), str(size))
        b.set(qn('w:color'), color)
        borders.append(b)
    tc_pr.append(borders)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn('w:tcMar')):
        tc_pr.remove(old)
    margins = OxmlElement('w:tcMar')
    for side, val in (('top', top), ('left', left), ('bottom', bottom), ('right', right)):
        m = OxmlElement(f'w:{side}')
        m.set(qn('w:w'), str(val))
        m.set(qn('w:type'), 'dxa')
        margins.append(m)
    tc_pr.append(margins)


def style_cell(cell, *, text=None, bold=False, italic=False, size=10,
               align='left', shading=None, font='Arial') -> None:
    if text is not None:
        cell.text = ''
        p = cell.paragraphs[0]
        run = p.add_run(text)
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        p.alignment = {
            'left': WD_ALIGN_PARAGRAPH.LEFT,
            'center': WD_ALIGN_PARAGRAPH.CENTER,
            'right': WD_ALIGN_PARAGRAPH.RIGHT,
        }[align]
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    set_cell_borders(cell)
    set_cell_margins(cell)
    if shading:
        set_cell_shading(cell, shading)


def heat_color(pct: float | None) -> str:
    """Red→amber→green gradient, lightened for readability with text."""
    if pct is None or (isinstance(pct, float) and math.isnan(pct)):
        return 'F2F2F2'
    pct = max(0.0, min(100.0, pct))
    if pct <= 50:
        r, g, b = 255, int(255 * (pct / 50)), 0
    else:
        r, g, b = int(255 * (1 - (pct - 50) / 50)), 200, 0
    # Lighten by mixing toward white
    f = 0.55
    r = int(r + (255 - r) * f)
    g = int(g + (255 - g) * f)
    b = int(b + (255 - b) * f)
    return f'{r:02X}{g:02X}{b:02X}'


def add_table(doc: Document, n_rows: int, n_cols: int, col_widths_in: list[float]):
    """Create a table with explicit column widths in inches.
    Sets dual widths (cell + column) per docx best practice."""
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.autofit = False
    table.allow_autofit = False
    for i, w in enumerate(col_widths_in):
        for row in table.rows:
            row.cells[i].width = Inches(w)
    # Also set table grid column widths
    tbl = table._tbl
    tbl_grid = tbl.find(qn('w:tblGrid'))
    if tbl_grid is not None:
        for col, w in zip(tbl_grid.findall(qn('w:gridCol')), col_widths_in):
            col.set(qn('w:w'), str(int(w * 1440)))
            col.set(qn('w:type'), 'dxa')
    return table


def add_caption(doc: Document, text: str, *, italic: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.italic = italic
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def add_heading(doc: Document, text: str, *, level: int = 1) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.bold = True
    run.font.size = Pt(13 if level == 1 else 11)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)


# =============================================================================
# Era and substance classification
# =============================================================================

def classify_era(year: int) -> str:
    if year < 1980:
        return 'Pre-1980'
    if year >= 2010:
        return '2010+'
    return 'Gap'


SUBSTANCE_COLS = ['Psilocybin', 'LSD', 'Ketamine', 'MDMA',
                  'Ayahuasca', 'Mescaline', 'Ibogaine', 'Cannabis',
                  'OtherPsychedelic', 'MultiplePsychedelic']


# =============================================================================
# Table 1 — Study characteristics
# =============================================================================

@dataclass
class Stratum:
    name: str
    df: pd.DataFrame

    @property
    def n(self) -> int:
        return len(self.df)


def build_table1(strata: list[Stratum]) -> list[list[str]]:
    """Return rows of Table 1 as list-of-lists [['', 'col1', 'col2', ...], ...]."""
    rows: list[list[str]] = []

    def row(label, values, indent=False):
        prefix = '    ' if indent else ''
        rows.append([prefix + label] + values)

    # Header
    rows.append(['Characteristic'] + [f"{s.name}\n(n={s.n})" for s in strata])

    # Sample size and participants
    row('Sample size, median (IQR)',
        [median_iqr(s.df['SampleSize_NFinal']) for s in strata])
    row('Total participants',
        [f"{int(pd.to_numeric(s.df['SampleSize_NFinal'], errors='coerce').sum())}"
         for s in strata])

    # Follow-up
    row('Follow-up months, median (IQR)',
        [median_iqr(s.df['Followup in months']) for s in strata])

    # Country
    rows.append(['Country, n (%)'] + ['' for _ in strata])
    for country in ['US', 'Non-US', 'US and Non-US']:
        row(country,
            [n_pct((s.df['Country_USvsNonUS'] == country).sum(), s.n)
             for s in strata],
            indent=True)

    # Baseline severity
    rows.append(['Baseline severity, n (%)'] + ['' for _ in strata])
    for sev in ['Severe', 'Moderate', 'Mild']:
        row(sev,
            [n_pct((s.df['BaseStatus'].astype('object') == sev).sum(), s.n)
             for s in strata],
            indent=True)
    row('Not reported',
        [n_pct(s.df['BaseStatus'].isna().sum(), s.n) for s in strata],
        indent=True)

    # Age bracket
    rows.append(['Age bracket, n (%)'] + ['' for _ in strata])
    for age in ['<30', '30-50', '50+']:
        row(age,
            [n_pct((s.df['Age_Median'].astype('object') == age).sum(), s.n)
             for s in strata],
            indent=True)
    row('Not reported',
        [n_pct(s.df['Age_Median'].isna().sum(), s.n) for s in strata],
        indent=True)

    # Sex/gender
    row('Female %, mean (SD), n reporting',
        [mean_sd_n(s.df['PercentFem']) for s in strata])

    # Race/ethnicity
    row('BIPOC %, mean (SD), n reporting',
        [mean_sd_n(s.df['RaceEthnicity_BIPOCPercent']) for s in strata])

    # Retention
    row('Retention %, mean (SD)',
        [mean_sd_n(s.df['Retention (%)']) for s in strata])

    # Substance class
    rows.append(['Substance studied, n (%)'] + ['' for _ in strata])
    for sub in ['Psilocybin', 'LSD', 'Ketamine', 'MDMA']:
        row(sub,
            [n_pct((to_numeric_strict(s.df[sub]) == 1).sum(), s.n) for s in strata],
            indent=True)

    return rows


# =============================================================================
# Table 2 — Methodological quality
# =============================================================================

METHODOLOGY_INDICATORS = [
    # (label, column, type) where type is 'binary' or 'derived'
    ('Randomization',                       'RandomizationYN',          'binary'),
    ('Any blinding',                        'BlindingYN',               'binary'),
    ('Double-blind or above',               'Double+Blind',             'binary'),
    ('Comparator/control group',            'Comparator',               'binary'),
    ('Power reported or discussed',         'Power',                    'binary'),
    ('≥80% retention',                      'Retention (%)',            'retention'),
    ('Validated outcome scale',             'ValidatedScaleMeasYN',     'binary'),
    ('Confounders assessed',                'ConfoundYN',               'binary'),
    ('Inclusion/exclusion criteria stated', 'InclusionExclusionCriteria','binary'),
    ('≥13/14 design criteria described',    'MethodologyDescribedYN',   'binary'),
    ('Funding/COI disclosed',               'Funding/COI YN',           'binary'),
    ('Primary care interface',              'PrimaryCare',              'binary'),
]


def methodology_value(df: pd.DataFrame, column: str, kind: str, n: int) -> float:
    if kind == 'binary':
        return pct_met(df[column], n)
    if kind == 'retention':
        s = pd.to_numeric(df[column], errors='coerce')
        return 100.0 * (s >= 80).sum() / n if n else float('nan')
    raise ValueError(kind)


def build_table2(strata: list[Stratum]) -> list[list[str]]:
    rows: list[list[str]] = []
    rows.append(['Methodological criterion'] + [f"{s.name}\n(n={s.n})" for s in strata])
    for label, col, kind in METHODOLOGY_INDICATORS:
        rows.append([label] + [
            f"{methodology_value(s.df, col, kind, s.n):.0f}%" for s in strata
        ])
    return rows


# =============================================================================
# Table 3 — USPSTF gap heat map (52 indicators across 6 domains)
# =============================================================================

USPSTF_INDICATORS = [
    # (domain, indicator label, column, eval_type)
    # eval_type: 'binary' (% with ==1), 'reported' (% non-null), 'retention80'
    # Domain 1: Study Identification & Design (15)
    ('Study Identification & Design', 'Study design type reported',           'Study Design Type',           'reported'),
    ('Study Identification & Design', 'Clinical trial (any type)',            'Clincial Trial YN',           'binary'),
    ('Study Identification & Design', 'Randomization performed',              'RandomizationYN',             'binary'),
    ('Study Identification & Design', 'Any blinding implemented',             'BlindingYN',                  'binary'),
    ('Study Identification & Design', 'Double-blind or above',                'Double+Blind',                'binary'),
    ('Study Identification & Design', 'Control/comparator group',             'Comparator',                  'binary'),
    ('Study Identification & Design', 'Final analyzed sample size reported',  'SampleSize_NFinal',           'reported'),
    ('Study Identification & Design', 'Primary care interface',               'PrimaryCare',                 'binary'),
    ('Study Identification & Design', 'Power reported or discussed',          'Power',                       'binary'),
    ('Study Identification & Design', '≥80% retention',                       'Retention (%)',               'retention80'),
    ('Study Identification & Design', 'Validated scale used',                 'ValidatedScaleMeasYN',        'binary'),
    ('Study Identification & Design', 'Confounders assessed',                 'ConfoundYN',                  'binary'),
    ('Study Identification & Design', 'Inclusion/exclusion criteria stated',  'InclusionExclusionCriteria',  'binary'),
    ('Study Identification & Design', '≥13/14 design criteria present',       'MethodologyDescribedYN',      'binary'),
    ('Study Identification & Design', 'Funding/COI disclosed',                'Funding/COI YN',              'binary'),
    # Domain 2: Population & Generalizability (7)
    ('Population & Generalizability', 'Baseline severity reported',           'BaseStatus',                  'reported'),
    ('Population & Generalizability', 'Age bracket reported',                 'Age_Median',                  'reported'),
    ('Population & Generalizability', 'Female % reported',                    'PercentFem',                  'reported'),
    ('Population & Generalizability', 'BIPOC % reported',                     'RaceEthnicity_BIPOCPercent',  'reported'),
    ('Population & Generalizability', 'Low-SES participants included',        'SocioeconomicStatusYN',       'binary'),
    ('Population & Generalizability', 'Country reported',                     'Country_USvsNonUS',           'reported'),
    ('Population & Generalizability', 'Recruitment representative',           'RecruitmentRepresentYN',      'binary'),
    # Domain 3: Intervention & Safety (3)
    ('Intervention & Safety',         'Intervention described',               'InterventionDescription',     'reported'),
    ('Intervention & Safety',         'Therapy/integration included',         'InterventionTherapy',         'binary'),
    ('Intervention & Safety',         'Harms/AEs assessed',                   'HarmsAssessed',               'binary'),
    # Domain 4: Equity & Cultural Framing (3)
    ('Equity & Cultural Framing',     'Cultural framing used',                'CulturalFraming',             'binary'),
    ('Equity & Cultural Framing',     'Indigenous frameworks referenced',     'IndigenousFramework',         'binary'),
    ('Equity & Cultural Framing',     'Reciprocity addressed',                'Reciprocity',                 'binary'),
    # Domain 5: Outcomes & Follow-Up (14)
    ('Outcomes & Follow-Up',          'Positive primary result',              'Pos Result Y/N',              'binary'),
    ('Outcomes & Follow-Up',          'Effect size reported',                 'Outcome',                     'reported'),
    ('Outcomes & Follow-Up',          'Test statistic reported',              'SD',                          'reported'),
    ('Outcomes & Follow-Up',          'P-value reported',                     'PVal',                        'reported'),
    ('Outcomes & Follow-Up',          'Follow-up duration reported',          'Followup in months',          'reported'),
    ('Outcomes & Follow-Up',          'Behavioral changes measured',          'BehaviorChangeMeasured',      'binary'),
    ('Outcomes & Follow-Up',          'Physical/biological measured',         'PhysicalChangeMeasured',      'binary'),
    ('Outcomes & Follow-Up',          'Mental health measured',               'MentalHealthChangeMeasured',  'binary'),
    ('Outcomes & Follow-Up',          'Quality of life measured',             'QualityOfLifeMeasured',       'binary'),
    ('Outcomes & Follow-Up',          'Implementation outcomes',              'Implementation Outcome',      'binary'),
    ('Outcomes & Follow-Up',          'Partial reduction reported',           'ReductionMeasured',           'binary'),
    ('Outcomes & Follow-Up',          'Complete cessation reported',          'CessationMeasured',           'binary'),
    ('Outcomes & Follow-Up',          'Relapse tracked',                      'RelapseMeasured',             'binary'),
    ('Outcomes & Follow-Up',          'Mortality measured',                   'MortalityMeasured',           'binary'),
    # Domain 6: Substance Category (10)
    ('Substance Category',            'Psilocybin studied',                   'Psilocybin',                  'binary'),
    ('Substance Category',            'Ayahuasca studied',                    'Ayahuasca',                   'binary'),
    ('Substance Category',            'LSD studied',                          'LSD',                         'binary'),
    ('Substance Category',            'Mescaline/peyote studied',             'Mescaline',                   'binary'),
    ('Substance Category',            'Ibogaine studied',                     'Ibogaine',                    'binary'),
    ('Substance Category',            'MDMA studied',                         'MDMA',                        'binary'),
    ('Substance Category',            'Ketamine studied',                     'Ketamine',                    'binary'),
    ('Substance Category',            'Cannabis studied',                     'Cannabis',                    'binary'),
    ('Substance Category',            'Other psychedelic studied',            'OtherPsychedelic',            'binary'),
    ('Substance Category',            'Multiple psychedelics used',           'MultiplePsychedelic',         'binary'),
]


def uspstf_value(df: pd.DataFrame, column: str, kind: str, n: int) -> float:
    if column not in df.columns:
        return float('nan')
    if kind == 'binary':
        return pct_met(df[column], n)
    if kind == 'reported':
        return pct_reported(df[column], n)
    if kind == 'retention80':
        s = pd.to_numeric(df[column], errors='coerce')
        return 100.0 * (s >= 80).sum() / n if n else float('nan')
    raise ValueError(kind)


# =============================================================================
# Table 4 — Outcomes measured
# =============================================================================

OUTCOME_INDICATORS = [
    ('Behavioral changes',           'BehaviorChangeMeasured'),
    ('Physical/biological',          'PhysicalChangeMeasured'),
    ('Mental health',                'MentalHealthChangeMeasured'),
    ('Quality of life',              'QualityOfLifeMeasured'),
    ('Implementation outcomes',      'Implementation Outcome'),
    ('Partial reduction',            'ReductionMeasured'),
    ('Complete cessation',           'CessationMeasured'),
    ('Relapse tracked',              'RelapseMeasured'),
    ('Mortality',                    'MortalityMeasured'),
]


def build_table4(strata: list[Stratum]) -> list[list[str]]:
    rows: list[list[str]] = []
    rows.append(['Outcome domain'] + [f"{s.name}\n(n={s.n})" for s in strata])
    for label, col in OUTCOME_INDICATORS:
        rows.append([label] + [f"{pct_met(s.df[col], s.n):.0f}%" for s in strata])
    return rows


# =============================================================================
# Table 5 — Follow-up duration distribution
# =============================================================================

FOLLOWUP_BINS = [
    ('< 1 month',       lambda x: x < 1),
    ('1 to <3 months',  lambda x: 1 <= x < 3),
    ('3 to <6 months',  lambda x: 3 <= x < 6),
    ('6 to <12 months', lambda x: 6 <= x < 12),
    ('12 to <24 months',lambda x: 12 <= x < 24),
    ('≥24 months',      lambda x: x >= 24),
]

USPSTF_THRESHOLDS = [
    ('≥3 months',  3),
    ('≥6 months',  6),
    ('≥12 months', 12),
    ('≥24 months', 24),
]


def build_table5(strata: list[Stratum]) -> list[list[str]]:
    """Two sub-blocks: distribution by bin, and cumulative ≥ thresholds."""
    rows: list[list[str]] = []
    rows.append(['Follow-up duration'] + [f"{s.name}\n(n={s.n})" for s in strata])

    # Distribution
    rows.append(['Distribution by bin, n (%)'] + ['' for _ in strata])
    for label, predicate in FOLLOWUP_BINS:
        rows.append(
            ['    ' + label] +
            [n_pct(int(s.df['Followup in months'].apply(predicate).sum()), s.n)
             for s in strata]
        )

    # Cumulative thresholds
    rows.append(['Cumulative, n (%) at or above'] + ['' for _ in strata])
    for label, threshold in USPSTF_THRESHOLDS:
        rows.append(
            ['    ' + label] +
            [n_pct(int((s.df['Followup in months'] >= threshold).sum()), s.n)
             for s in strata]
        )
    return rows


# =============================================================================
# Document composition
# =============================================================================

def configure_document(doc: Document) -> None:
    """US Letter, 1-inch margins, Arial default."""
    section = doc.sections[0]
    section.page_height = Inches(11)
    section.page_width = Inches(8.5)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)


def render_table(doc: Document, rows: list[list[str]],
                 col_widths: list[float], *,
                 first_row_is_header: bool = True,
                 indented_rows: set[int] | None = None,
                 group_rows: set[int] | None = None) -> None:
    """Render a generic 2-D table with header shading and section grouping."""
    indented_rows = indented_rows or set()
    group_rows = group_rows or set()

    table = add_table(doc, n_rows=len(rows), n_cols=len(rows[0]),
                      col_widths_in=col_widths)
    for r, row_data in enumerate(rows):
        for c, val in enumerate(row_data):
            cell = table.cell(r, c)
            shading = None
            bold = False
            if first_row_is_header and r == 0:
                shading = 'D9E2F3'  # soft blue
                bold = True
            elif r in group_rows:
                shading = 'F2F2F2'  # light gray for section header rows
                bold = True
            style_cell(cell, text=str(val), bold=bold, size=10,
                       align='left' if c == 0 else 'center',
                       shading=shading)


def render_heatmap_table(doc: Document, df: pd.DataFrame, n: int) -> None:
    """Render Table 3 (USPSTF heat map) with continuous shading by % met."""
    # Group indicators by domain
    domain_counts: dict[str, int] = {}
    for dom, *_ in USPSTF_INDICATORS:
        domain_counts[dom] = domain_counts.get(dom, 0) + 1

    n_rows = 1 + len(USPSTF_INDICATORS) + len(domain_counts)  # header + indicators + domain headers
    col_widths = [2.0, 3.7, 0.8]
    table = add_table(doc, n_rows=n_rows, n_cols=3, col_widths_in=col_widths)

    # Header row
    for c, hdr in enumerate(['Domain', 'Indicator', '% Met']):
        style_cell(table.cell(0, c), text=hdr, bold=True, size=10,
                   align='left' if c < 2 else 'center', shading='D9E2F3')

    last_domain = None
    row_idx = 1
    for domain, label, column, kind in USPSTF_INDICATORS:
        if domain != last_domain:
            # Domain header row (spanning across)
            for c, txt in enumerate([domain, '', '']):
                style_cell(table.cell(row_idx, c), text=txt, bold=True,
                           size=10, align='left', shading='F2F2F2')
            row_idx += 1
            last_domain = domain
        pct = uspstf_value(df, column, kind, n)
        # Domain column intentionally blank for indicator rows (already shown above)
        style_cell(table.cell(row_idx, 0), text='', size=10)
        style_cell(table.cell(row_idx, 1), text='    ' + label, size=10, align='left')
        style_cell(table.cell(row_idx, 2),
                   text='—' if math.isnan(pct) else f"{pct:.0f}%",
                   size=10, align='center', shading=heat_color(pct))
        row_idx += 1


def generate_for_condition(condition: str) -> None:
    meta = CONDITION_META[condition]
    short = meta['short']
    disorder = meta['disorder']
    input_path = _BASE / 'data' / f'{short}_Dataset_Cleaned.xlsx'
    output_path = _BASE / 'tables' / f'{short}_Descriptive_Analyses.docx'

    if not input_path.exists():
        print(f"WARNING: {input_path} not found — skipping {condition}.")
        return

    df = pd.read_excel(input_path)
    df['era'] = df['Year'].apply(classify_era)

    n_pre  = int((df['era'] == 'Pre-1980').sum())
    n_post = int((df['era'] == '2010+').sum())
    n_total = len(df)

    strata = [
        Stratum('All studies', df),
        Stratum('Pre-1980',    df[df['era'] == 'Pre-1980']),
        Stratum('2010+',       df[df['era'] == '2010+']),
    ]

    doc = Document()
    configure_document(doc)

    # Title
    title_p = doc.add_paragraph()
    title_run = title_p.add_run(f'Descriptive Analyses — Psychedelics for {disorder}')
    title_run.font.name = 'Arial'
    title_run.bold = True
    title_run.font.size = Pt(15)
    add_caption(doc,
                f'Five descriptive tables supporting the USPSTF evidentiary-gap analysis. '
                f'Era split: Pre-1980 (n={n_pre}) vs. 2010+ (n={n_post}); '
                f'the 1980–2009 interval contains zero studies.',
                italic=True)

    # ---------------- Table 1 ----------------
    add_heading(doc, 'Table 1. Study Characteristics by Era')
    rows1 = build_table1(strata)
    group_rows1 = {i for i, r in enumerate(rows1) if i > 0 and all(c == '' for c in r[1:])}
    render_table(doc, rows1, col_widths=[2.7, 1.3, 1.3, 1.3],
                 group_rows=group_rows1)
    add_caption(doc, 'Cell values: median (IQR) for continuous; mean (SD), n reporting '
                     'where missingness is high; n (%) for categorical. Substance '
                     'categories are non-exclusive (a study can use multiple substances).',
                italic=True)

    # ---------------- Table 2 ----------------
    add_heading(doc, 'Table 2. Methodological Quality by Era')
    rows2 = build_table2(strata)
    render_table(doc, rows2, col_widths=[3.0, 1.2, 1.2, 1.2])
    add_caption(doc, 'Cell values are the % of studies in each stratum that '
                     'positively met the criterion. Missing or "not reported" '
                     'values are treated as not met (strict USPSTF gap interpretation). '
                     'The retention criterion uses ≥80% as the USPSTF-style threshold.',
                italic=True)

    # ---------------- Table 3 ----------------
    add_heading(doc, 'Table 3. USPSTF Indicator Gap Heat Map (52 Indicators \xd7 6 Domains)')
    add_caption(doc,
                f'Cell shading reflects % of all studies (n={n_total}) meeting/reporting '
                f'each indicator. Red = low (gap); green = high (well covered). '
                f'For binary criteria, % is the proportion with value 1. For '
                f'continuous/categorical variables (denoted "reported"), % is the '
                f'proportion with any non-null value. Substance Category rows '
                f'describe the literature\'s coverage, not USPSTF criteria per se.',
                italic=True)
    render_heatmap_table(doc, df, n=n_total)

    # ---------------- Table 4 ----------------
    add_heading(doc, 'Table 4. Outcome Domains Measured by Era')
    rows4 = build_table4(strata)
    render_table(doc, rows4, col_widths=[3.0, 1.2, 1.2, 1.2])
    add_caption(doc, 'Cell values are the % of studies measuring each outcome domain. '
                     'Note that USPSTF-relevant "hard" endpoints (mortality, durable '
                     'cessation, relapse over long follow-up) are markedly under-measured.',
                italic=True)

    # ---------------- Table 5 ----------------
    add_heading(doc, 'Table 5. Follow-up Duration Distribution')
    rows5 = build_table5(strata)
    group_rows5 = {i for i, r in enumerate(rows5) if i > 0 and all(c == '' for c in r[1:])}
    render_table(doc, rows5, col_widths=[3.0, 1.2, 1.2, 1.2],
                 group_rows=group_rows5)
    add_caption(doc, 'USPSTF behavioral-intervention recommendations typically rely on '
                     'evidence with ≥6–12 months follow-up. Cumulative rows show the '
                     'fraction of studies meeting common durability thresholds.',
                italic=True)

    doc.save(output_path)
    print(f"Wrote {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate descriptive analysis tables for one or all conditions.'
    )
    parser.add_argument(
        '--condition',
        choices=AVAILABLE_CONDITIONS + ['all'],
        default='all',
        help='Condition to process (default: all available conditions).',
    )
    args = parser.parse_args()

    conditions = AVAILABLE_CONDITIONS if args.condition == 'all' else [args.condition]
    for condition in conditions:
        generate_for_condition(condition)


if __name__ == '__main__':
    main()
