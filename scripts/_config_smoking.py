"""Per-condition configuration for smoking psychedelic trials."""

CONDITION_NAME = 'smoking'
INPUT_FILE = 'data/Smoking_Dataset.xlsx'

# ── Effect-size extraction table ──────────────────────────────────────────────
# Keyed by (first_author_surname, year).
# Surnames are derived by _lib.first_author_surname() — non-breaking hyphens are
# normalised to '-', so 'Garcia‑Romeu' (U+2011) becomes 'Garcia-Romeu'.
# 'Johnson MW' (no comma between surname and initials) is kept as-is.

EFFECT_SIZE_EXTRACTIONS: dict = {
    ('Johnson MW', 2026):   ('Odds ratio',                           6.12,
                              'OR for 7-day point abstinence at week 4; RCT N=82'),
    ('Garcia-Romeu', 2015): ('Group means (quitters vs non-quitters)', '65.8 vs 52.1',
                              'SOCQ scores; predictive subgroup analysis, not treatment vs control'),
    ('Johnson',     2016):  ('Abstinence rate (%)',                  60,
                              '60% abstinent @ 30 mo; single-arm open-label N=15'),
    ('Johnson',     2014):  ('Abstinence rate (%)',                  80,
                              '80% abstinent @ 6 mo; single-arm open-label N=15'),
}

# ── Conversion rules ──────────────────────────────────────────────────────────

CONVERSION_RULES: dict = {
    ('Johnson MW', 2026):   {'method': 'OR', 'confidence': 'approx',
                              'note': 'OR=6.12 favours psilocybin; Hasselblad-Hedges approximation'},
    ('Garcia-Romeu', 2015): {'method': None, 'confidence': 'excluded',
                              'note': 'Predictive analysis (quitters vs non-quitters on SOCQ); '
                                      'not a treatment vs control effect size'},
    ('Johnson',     2016):  {'method': None, 'confidence': 'excluded',
                              'note': 'Single-arm abstinence rate; no comparator'},
    ('Johnson',     2014):  {'method': None, 'confidence': 'excluded',
                              'note': 'Single-arm abstinence rate; no comparator'},
}
