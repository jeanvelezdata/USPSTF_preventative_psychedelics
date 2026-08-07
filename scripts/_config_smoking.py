"""Per-condition configuration for smoking psychedelic trials."""

CONDITION_NAME = 'smoking'
CONDITION_LABEL = 'Smoking'   # value of the master's Condition column
INPUT_FILE = 'clinical_trials/outputs/clinical_master.csv'

# ── Effect-size extraction table ──────────────────────────────────────────────
# Keyed by (first_author_surname, year). One entry per study.
# (metric, measure, note) — measure is numeric where possible; "X vs Y"
# string for irreducible two-group comparisons.

EFFECT_SIZE_EXTRACTIONS: dict = {
    (    'Garcia-Romeu', 2015): ('Abstinence rate (%)', '12/15 (80%)', 'SOCQ scores; predictive subgroup analysis, not treatment vs control'),
    (         'Johnson', 2014): ('Abstinence rate (%)', '12/15 (80%)', '80% abstinent @ 6 mo; single-arm open-label N=15'),
    (         'Johnson', 2016): ('Abstinence rate (%)', '9/15 (60%)', '60% abstinent @ 30 mo; single-arm open-label N=15'),
    (      'Johnson MW', 2026): ('Odds ratio', 6.12, 'Directly reported OR = 6.12 (95% CI, 1.99-23.26; P = .003) from binary logistic regression for the a priori primary outcome (6-month biochemically verified prolonged abstinence), ITT N = 82. Independently recomputed from the reported 2x2 cell counts (17/42 psilocybin abstinent vs 4/40 nicotine-patch abstinent: OR = (17x36)/(25x4) = 6.12), which matches the reported value exactly, supporting a clean conversion with no assumption required.'),
}

# ── Conversion rules ──────────────────────────────────────────────────────────
# Keyed by (first_author_surname, year).
# direction defaults to +1; set -1 when the metric's natural sign is
# opposite to the favoured treatment direction.

CONVERSION_RULES: dict = {
    (    'Garcia-Romeu', 2015): {'method': None, 'confidence': 'excluded', 'note': 'Predictive analysis (quitters vs non-quitters on SOCQ); not a treatment vs control effect size'},
    (         'Johnson', 2014): {'method': None, 'confidence': 'excluded', 'note': 'Single-arm abstinence rate; no comparator'},
    (         'Johnson', 2016): {'method': None, 'confidence': 'excluded', 'note': 'Single-arm abstinence rate; no comparator'},
    (      'Johnson MW', 2026): {'method': 'OR', 'confidence': 'clean', 'note': 'Directly reported OR = 6.12 (95% CI, 1.99-23.26; P = .003) from binary logistic regression for the a priori primary outcome (6-month biochemically verified prolonged abstinence), ITT N = 82. Independently recomputed from the reported 2x2 cell counts (17/42 psilocybin abstinent vs 4/40 nicotine-patch abstinent: OR = (17x36)/(25x4) = 6.12), which matches the reported value exactly, supporting a clean conversion with no assumption required.'},
}

# ── Tier 2 qualitative ratings ────────────────────────────────────────────────
# Keyed by (first_author_surname, year). Studies excluded from Tier 1.

TIER2_RATINGS: dict = {
    (    'Garcia-Romeu', 2015): {
        'category': 'single_arm_positive',
        'basis':    "80% (12/15) biologically verified 7-day point-prevalence smoking abstinence at 6-month follow-up in an open-label, single-arm design with no control group, well above the <35% 6-month abstinence typical of standard smoking-cessation treatments cited in the article's own Introduction.",
    },
    (         'Johnson', 2014): {
        'category': 'single_arm_positive',
        'basis':    "80% (12/15) biologically verified 7-day point-prevalence smoking abstinence at 6-month follow-up in an open-label, single-arm pilot with no control group, substantially exceeding the <35% typical 6-month abstinence rate for standard smoking-cessation pharmacotherapies/behavioral treatments cited in the article's own Introduction and Discussion.",
    },
    (         'Johnson', 2016): {
        'category': 'single_arm_positive',
        'basis':    '60% (9/15) biologically verified (CO + cotinine + TLFB) smoking abstinence at long-term follow-up (mean 30 months post-TQD, range 16-57 months) in an open-label, single-arm design, contrasted by the authors against <31% typical 12-month abstinence for standard smoking-cessation medications (Discussion).',
    },
}
