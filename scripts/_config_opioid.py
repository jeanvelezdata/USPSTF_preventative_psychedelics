"""Per-condition configuration for opioid psychedelic trials."""

CONDITION_NAME = 'opioid'
INPUT_FILE = 'data/Opioid_Dataset.xlsx'

# ── Effect-size extraction table ──────────────────────────────────────────────
# Keyed by (first_author_surname, year).  One entry per study.
# (metric, measure, note)  — measure is numeric where possible; "X vs Y" string
# for irreducible two-group comparisons.
#
# Key derivation: first_author_surname() splits on the first comma/semicolon.
#   "D.C. Mash, C.A. Kovera..."  → 'D.C. Mash'
#   "Jovaisa T, Laurinenas G..." → 'Jovaisa T'
#   "Krupitsky, E. M., ..."      → 'Krupitsky'
#   "P. Glue, G. Cape, ..."      → 'P. Glue'
#   "P.L. Prior, S.L. Prior ..." → 'P.L. Prior'
#   "Savage, C., & McCabe, ..."  → 'Savage'

EFFECT_SIZE_EXTRACTIONS: dict = {
    # Ibogaine studies
    ('D.C. Mash',  2000): ('F',                             9.59,           'F(3,18)=9.59; 3-df repeated-measures ANOVA; BDI within-group pre-post'),
    ('Jovaisa T',  2006): ("Cohen's d",                     1.39,           'pre-computed from group means (MAP 96.6 vs 79.4 mmHg) and SDs (13.8, 10.8); N=50 assumed equal groups'),
    ('P. Glue',    2016): ('Group means (Tx vs Ctrl)',       '22.5 vs 13.9', 'hours to OST resumption; NS; noribogaine 120mg vs placebo'),
    ('P.L. Prior', 2014): ('F',                             2.450,          'F(3,12)=2.450; 3-df numerator; 10% positive urine in ibogaine group'),
    # Ketamine studies
    ('Krupitsky',  2002): ('Two-group proportions (%)',      '25 vs 3',      'approx from Fig. 1; 12mo abstinence, high-dose KET vs control'),
    ('Krupitsky',  2007): ('Two-group proportions (%)',      '50 vs 22.2',   'KET vs control abstinence at 12mo'),
    # LSD study
    ('Savage',     1973): ('Chi-squared',                    3.86,           'df=1; 9/36 (25%) vs 2/37 (5%) abstinent at 12mo; p=0.05'),
}

# ── Conversion rules ──────────────────────────────────────────────────────────
# Keyed by (first_author_surname, year).
# direction defaults to +1; set -1 when the metric's natural sign is opposite
# to the favoured treatment direction.

CONVERSION_RULES: dict = {
    ('D.C. Mash',  2000): {'method': None,   'confidence': 'excluded',
                            'note': 'F(3,18) multi-df; within-group pre-post design; no comparator arm'},
    ('Jovaisa T',  2006): {'method': 'd',    'confidence': 'approx',
                            'note': 'd pre-computed from group means (96.6 vs 79.4 mmHg MAP) and SDs (13.8, 10.8); equal groups assumed; direction favors treatment (lower MAP)'},
    ('P. Glue',    2016): {'method': None,   'confidence': 'excluded',
                            'note': 'NS (p not significant); single SD of unclear provenance; time-to-event endpoint'},
    ('P.L. Prior', 2014): {'method': None,   'confidence': 'excluded',
                            'note': 'F(3,12) has 3-df numerator; not reducible to 1-df between-groups comparison'},
    ('Krupitsky',  2002): {'method': None,   'confidence': 'excluded',
                            'note': 'Two-group proportions from figure (approximate); downgrade to Tier 2'},
    ('Krupitsky',  2007): {'method': None,   'confidence': 'excluded',
                            'note': 'Two-group proportions; no SD reported; downgrade to Tier 2'},
    ('Savage',     1973): {'method': 'chi2', 'confidence': 'approx',
                            'note': 'χ²=3.86, df=1; 9/36 vs 2/37 abstinent at 12mo'},
}

# ── Tier 2 ratings ────────────────────────────────────────────────────────────
# Applied only to studies where confidence == 'excluded' in Tier 1.
# category: one of {negative, null, small_positive, moderate_positive,
#                   large_positive, single_arm_positive, unclassifiable}
# basis: one sentence explaining the classification.
# computed_or: float — OR derived from two-group proportions (when applicable).

TIER2_RATINGS: dict = {
    ('D.C. Mash',  2000): {
        'category': 'single_arm_positive',
        'basis':    'BDI improved from 16.86 to 2.29 (F(3,18)=9.59, p<0.001); single-arm ibogaine study with no comparator group.',
    },
    ('P. Glue',    2016): {
        'category': 'null',
        'basis':    'Time to OST resumption 22.5 h vs 13.9 h (noribogaine 120mg vs placebo); difference non-significant.',
    },
    ('P.L. Prior', 2014): {
        'category': 'large_positive',
        'basis':    'Double-blind placebo-controlled pilot; ibogaine group had 10% positive urine at follow-up; F(3,12)=2.450, p=0.023 per source.',
    },
    ('Krupitsky',  2002): {
        'category':    'large_positive',
        'basis':       'Computed OR≈10.78 from approximate two-group abstinence proportions (25% vs 3% at 12mo, read from Fig. 1); sustained across 24mo.',
        'computed_or': 10.78,
    },
    ('Krupitsky',  2007): {
        'category':    'large_positive',
        'basis':       'Computed OR=3.50 from two-group abstinence proportions (50% vs 22.2% at 12mo); exceeds OR≥3 threshold.',
        'computed_or': 3.50,
    },
}
