"""Per-condition configuration for alcohol psychedelic trials."""

CONDITION_NAME = 'alcohol'
INPUT_FILE = 'data/Alcohol_Dataset.xlsx'

# ── Effect-size extraction table ──────────────────────────────────────────────
# Keyed by (first_author_surname, year).  One entry per study.
# (metric, measure, note)  — measure is numeric where possible; "X vs Y" string
# for irreducible two-group comparisons.

EFFECT_SIZE_EXTRACTIONS: dict = {
    ('Bogenschutz', 2015): ("Cohen's d",                      1.383,          ''),
    ('Bogenschutz', 2022): ("Hedges' g",                      0.52,           ''),
    ('Bowen',       1970): ('Chi-squared',                    1.408,          'df=1; 24% vs 27% good adjustment (LSD+HRTL vs control, combined); ns'),
    ('Dakwar',      2020): ('F',                              25.1,           'F preferred over NNT for Tier 1 (df reported)'),
    ('Das',         2019): ('Partial eta squared',            0.219,          ''),
    ('Denson',      1970): (None,                             None,           'Outcome not reported'),
    ('Dusen',       1967): ('Group means (Tx vs Ctrl)',       '3.97 vs 4.03', 'No SDs reported; ns'),
    ('Gent',        2024): ('F',                              6.45,           ''),
    ('Grabski',     2022): ('Mean difference (%)',            10.1,           '% heavy drinking days'),
    ('Heinzerling', 2023): ('F',                              15.76,          ''),
    ('Hollister',   1969): ('F',                              8.5,            ''),
    ('Jensen',      2024): ("Cohen's d",                      1.02,           'Stenbaek et al. open-label psilocybin'),
    ('Jensen',      1963): ('Two-group proportions (%)',      '63 vs 27',     'LSD vs control abstinence'),
    ('Johnson',     1969): ('Non-significant (no statistic)', None,           'Reported only as "NS"'),
    ('Kurland',     1967): ('Abstinence rate (%)',            33.3,           'Single-arm rate; no comparator group'),
    ('Luquiens',    2025): ('Risk difference (%)',            -44,            'Abstinence rate difference'),
    ('MacLean',     1961): ('Improvement rate (%)',           49,             'Single-arm improvement rate'),
    ('Marvania',    2024): ('Within-group change (%)',        51.98,          'AASE pre-post; no comparator'),
    ('Nicholas',    2022): ("Hedges' g",                      0.45,           'AUDIT change'),
    ("O'Reilly",    1964): ('Abstinence rate (%)',            38,             'Single-arm rate'),
    ('Pagni',       2025): ('Partial eta squared',            0.07,           'Openness scale'),
    ('Pagni',       2024): ('t',                              5.568,          'fMRI craving reduction; df=3'),
    ('Pahnke',      1970): ('Two-group proportions (%)',      '53 vs 33',     'High vs low dose'),
    ('Rieser',      2025): ("Cohen's d",                      0.151,          ''),
    ('Rothberg',    2020): ('Odds ratio',                     5.0,            'OR approximate'),
    ('Sessa',       2021): ('Within-group mean change',       '18.7 vs 130.6','units/wk pre vs 9mo, no comparator'),
    ('Sessa',       2019): ('Abstinence rate (%)',            50,             '2/4 abstinent; case series'),
    ('Smart',       1966): ('Two-group proportions (%)',      '33.7 vs 19.6', 'LSD vs control abstinence gain; ns'),
    ('Smith',       1958): ('Improvement rate (%)',           50,             '12/24; single-arm'),
    ('Terasaki',    2022): ('Risk ratio',                     0.37,           'KET vs LA arm'),
    ('Thurgur',     2025): ('Bayesian posterior probability', 0.63,           'Flat prior'),
    ('Tomsovic',    1970): ('Chi-squared',                    7.19,           'df=1; LSD vs control I'),
    ('Yoon',        2019): ('Response rate (%)',              100,            'Case series 5/5'),
}

# ── Conversion rules ──────────────────────────────────────────────────────────
# Keyed by (first_author_surname, year).
# direction defaults to +1; set -1 when the metric's natural sign is opposite
# to the favoured treatment direction.

CONVERSION_RULES: dict = {
    ('Bogenschutz', 2015): {'method': 'd',     'confidence': 'clean'},
    ('Bogenschutz', 2022): {'method': 'g',     'confidence': 'clean'},
    ('Bowen',       1970): {'method': 'chi2',  'confidence': 'approx', 'direction': -1,
                            'note': 'χ²=1.408, p>0.05; 24% vs 27% good adjustment; treatment direction slightly negative'},
    ('Dakwar',      2020): {'method': 'F', 'df_error': 797, 'confidence': 'approx',
                            'note': 'F is interaction term with large df_error; rough'},
    ('Das',         2019): {'method': 'eta_p', 'confidence': 'clean'},
    ('Denson',      1970): {'method': None,    'confidence': 'excluded',
                            'note': 'No outcome statistic reported'},
    ('Dusen',       1967): {'method': None,    'confidence': 'excluded',
                            'note': 'Group means without SDs; ns'},
    ('Gent',        2024): {'method': None,    'confidence': 'excluded',
                            'note': 'F has 2 df numerator (3-arm); not 1-df comparison'},
    ('Grabski',     2022): {'method': None,    'confidence': 'excluded',
                            'note': 'Mean difference reported without SDs'},
    ('Heinzerling', 2023): {'method': None,    'confidence': 'excluded',
                            'note': 'F has 6 df numerator; repeated-measures design'},
    ('Hollister',   1969): {'method': 'F', 'df_error': 50, 'confidence': 'clean',
                            'direction': -1,
                            'note': 'Sig. F unfavorable to LSD vs dextroamphetamine'},
    ('Jensen',      2024): {'method': 'd',     'confidence': 'clean'},
    ('Jensen',      1963): {'method': None,    'confidence': 'excluded',
                            'note': 'Two-group proportions; downgrade to Tier 2'},
    ('Johnson',     1969): {'method': None,    'confidence': 'excluded',
                            'note': 'Reported only as "NS"'},
    ('Kurland',     1967): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm rate; no comparator'},
    ('Luquiens',    2025): {'method': None,    'confidence': 'excluded',
                            'note': 'Risk difference only; downgrade to Tier 2'},
    ('MacLean',     1961): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm improvement rate'},
    ('Marvania',    2024): {'method': None,    'confidence': 'excluded',
                            'note': 'Within-group AASE change; no comparator'},
    ('Nicholas',    2022): {'method': 'g',     'confidence': 'clean'},
    ("O'Reilly",    1964): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm abstinence rate'},
    ('Pagni',       2025): {'method': 'eta_p', 'confidence': 'approx',
                            'note': 'Small N=84, partial eta^2 conversion approximate'},
    ('Pagni',       2024): {'method': None,    'confidence': 'excluded',
                            'note': 'Within-subjects t (df=3); not between-groups'},
    ('Pahnke',      1970): {'method': None,    'confidence': 'excluded',
                            'note': 'Two dose-group proportions; downgrade to Tier 2'},
    ('Rieser',      2025): {'method': 'd',     'confidence': 'clean'},
    ('Rothberg',    2020): {'method': 'OR',    'confidence': 'approx',
                            'note': 'OR reported as approx (~5); no cell counts'},
    ('Sessa',       2021): {'method': None,    'confidence': 'excluded',
                            'note': 'Within-group mean change; no comparator'},
    ('Sessa',       2019): {'method': None,    'confidence': 'excluded',
                            'note': 'Case series 2/4 abstinent; no comparator'},
    ('Smart',       1966): {'method': None,    'confidence': 'excluded',
                            'note': 'Two-group proportions; downgrade to Tier 2'},
    ('Smith',       1958): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm improvement rate'},
    ('Terasaki',    2022): {'method': 'RR', 'direction': -1, 'confidence': 'approx',
                            'note': 'RR=0.37 = LESS readmission (favors ketamine); sign flipped'},
    ('Thurgur',     2025): {'method': None,    'confidence': 'excluded',
                            'note': 'Bayesian posterior not directly convertible'},
    ('Tomsovic',    1970): {'method': 'chi2',  'confidence': 'approx',
                            'note': 'Primary chi^2 (LSD vs control I, nonschiz, abstinence)'},
    ('Yoon',        2019): {'method': None,    'confidence': 'excluded',
                            'note': 'Case series 5/5 response; no comparator'},
}

# ── Tier 2 ratings ────────────────────────────────────────────────────────────
# Applied only to studies where confidence == 'excluded' in Tier 1.
# category: one of {negative, null, small_positive, moderate_positive,
#                   large_positive, single_arm_positive, unclassifiable}
# basis: one sentence explaining the classification.
# computed_or: float — OR derived from two-group proportions (when applicable).

TIER2_RATINGS: dict = {
    ('Denson',      1970): {
        'category': 'null',
        'basis':    'Authors say: results obtained from statistical analysis of the data were interpreted as negative.',
    },
    ('Dusen',       1967): {
        'category': 'null',
        'basis':    'Group means virtually identical (3.97 vs 4.03); reported non-significant.',
    },
    ('Gent',        2024): {
        'category': 'large_positive',
        'basis':    'F(2,df)=6.45, p<0.01 in 3-arm RCT; overall ANOVA significant, favoring active treatment over placebo.',
    },
    ('Grabski',     2022): {
        'category': 'moderate_positive',
        'basis':    '+10.1 percentage-point difference in heavy drinking days favoring ketamine; no SD reported so Tier 1 conversion not feasible.',
    },
    ('Heinzerling', 2023): {
        'category': 'large_positive',
        'basis':    'F(6,df)=15.76 for time-by-treatment interaction, p<0.001; repeated-measures design with sustained treatment advantage.',
    },
    ('Jensen',      1963): {
        'category':    'large_positive',
        'basis':       'Computed OR=4.60 from two-group abstinence proportions (63% vs 27%); exceeds OR≥3 threshold.',
        'computed_or': 4.60,
    },
    ('Johnson',     1969): {
        'category': 'null',
        'basis':    'Reported only as non-significant; no test statistic given.',
    },
    ('Kurland',     1967): {
        'category': 'single_arm_positive',
        'basis':    '33.3% abstinence rate at follow-up; single-arm study with no comparator group.',
    },
    ('Luquiens',    2025): {
        'category': 'negative',
        'basis':    'Risk difference = -44 percentage points in abstinence rate; treatment arm had substantially lower abstinence than comparator.',
    },
    ('MacLean',     1961): {
        'category': 'single_arm_positive',
        'basis':    '49% improvement rate; single-arm open-label study with no comparator.',
    },
    ('Marvania',    2024): {
        'category': 'single_arm_positive',
        'basis':    '51.98% within-group improvement on AASE scale; no comparator arm.',
    },
    ("O'Reilly",    1964): {
        'category': 'single_arm_positive',
        'basis':    '38% abstinence rate; single-arm study with no comparator group.',
    },
    ('Pagni',       2024): {
        'category': 'single_arm_positive',
        'basis':    'Within-subjects t(3)=5.568, p<0.05 for craving reduction on fMRI; N=4, within-subjects design, no comparator arm.',
    },
    ('Pahnke',      1970): {
        'category':    'moderate_positive',
        'basis':       'Computed OR=2.29 from two-group abstinence proportions (53% vs 33%); falls in OR 1.5-3 range.',
        'computed_or': 2.29,
    },
    ('Sessa',       2021): {
        'category': 'single_arm_positive',
        'basis':    'Within-group reduction from 130.6 to 18.7 units/wk at 9 months; no comparator arm.',
    },
    ('Sessa',       2019): {
        'category': 'single_arm_positive',
        'basis':    '50% abstinence rate (2/4); case series with no comparator.',
    },
    ('Smart',       1966): {
        'category':    'moderate_positive',
        'basis':       'Computed OR=2.08 from two-group abstinence proportions (33.7% vs 19.6%); falls in OR 1.5-3 range.',
        'computed_or': 2.08,
    },
    ('Smith',       1958): {
        'category': 'single_arm_positive',
        'basis':    '50% improvement rate (12/24 patients); single-arm study with no comparator.',
    },
    ('Thurgur',     2025): {
        'category': 'null',
        'basis':    'Bayesian posterior P(positive effect)=0.63; insufficient evidence above chance threshold (flat prior).',
    },
    ('Yoon',        2019): {
        'category': 'single_arm_positive',
        'basis':    '100% response rate (5/5); case series with no comparator.',
    },
}
