"""Per-condition configuration for opioid psychedelic trials."""

CONDITION_NAME = 'opioid'
CONDITION_LABEL = 'Opioid'   # value of the master's Condition column
INPUT_FILE = 'clinical_trials/outputs/clinical_master.csv'

# ── Effect-size extraction table ──────────────────────────────────────────────
# Keyed by (first_author_surname, year). One entry per study.
# (metric, measure, note) — measure is numeric where possible; "X vs Y"
# string for irreducible two-group comparisons.

EFFECT_SIZE_EXTRACTIONS: dict = {
    (       'D.C. Mash', 2000): ('F (multi-df, within-subjects repeated-measures ANOVA)', 'F(3,24) = 81.38', 'F(3,18)=9.59; 3-df repeated-measures ANOVA; BDI within-group pre-post'),
    (       'Jovaisa T', 2006): ("Cohen's d", 1.39, 'pre-computed from group means (MAP 96.6 vs 79.4 mmHg) and SDs (13.8, 10.8); N=50 assumed equal groups'),
    (       'Krupitsky', 2002): ('Two-group proportions (%)', '50 vs 60', 'approx from Fig. 1; 12mo abstinence, high-dose KET vs control'),
    (       'Krupitsky', 2007): ('Two-group proportions (%)', '50 vs 22.2', 'KET vs control abstinence at 12mo'),
    (         'P. Glue', 2016): ('Exposure-response linear mixed-effects regression slope (change from baseline, placebo-corrected QTcI vs. plasma noribogaine concentration)', 0.17, 'hours to OST resumption; NS; noribogaine 120mg vs placebo'),
    (      'P.L. Prior', 2014): ('F (repeated-measures ANOVA, urine-positivity primary outcome)', 2.45, 'F(3,12)=2.450; 3-df numerator; 10% positive urine in ibogaine group'),
    (          'Savage', 1973): ('Chi-squared', 3.86, 'df=1; 9/36 (25%) vs 2/37 (5%) abstinent at 12mo; p=0.05'),
}

# ── Conversion rules ──────────────────────────────────────────────────────────
# Keyed by (first_author_surname, year).
# direction defaults to +1; set -1 when the metric's natural sign is
# opposite to the favoured treatment direction.

CONVERSION_RULES: dict = {
    (       'D.C. Mash', 2000): {'method': None, 'confidence': 'excluded', 'note': 'F(3,18) multi-df; within-group pre-post design; no comparator arm'},
    (       'Jovaisa T', 2006): {'method': None, 'confidence': 'excluded', 'note': "Excluded from Tier 1: the only convertible statistic (d=1.39 from peak MAP, 96.6 vs 79.4 mmHg) measures blood pressure, not substance use. output.md rules the OOWS-A withdrawal-severity score the primary outcome, and it is reported only as 'p<0.05' with no test statistic, so no SUD-outcome effect size can be derived without computing a test the authors did not report."},
    (       'Krupitsky', 2002): {'method': None, 'confidence': 'excluded', 'note': 'Two-group proportions from figure (approximate); downgrade to Tier 2'},
    (       'Krupitsky', 2007): {'method': None, 'confidence': 'excluded', 'note': 'Two-group proportions; no SD reported; downgrade to Tier 2'},
    (         'P. Glue', 2016): {'method': None, 'confidence': 'excluded', 'direction': -1, 'note': 'NS (p not significant); single SD of unclear provenance; time-to-event endpoint'},
    (      'P.L. Prior', 2014): {'method': None, 'confidence': 'excluded', 'note': 'F(3,12) has 3-df numerator; not reducible to 1-df between-groups comparison'},
    (          'Savage', 1973): {'method': 'chi2', 'confidence': 'approx', 'note': 'χ²=3.86, df=1; 9/36 vs 2/37 abstinent at 12mo'},
}

# ── Tier 2 qualitative ratings ────────────────────────────────────────────────
# Keyed by (first_author_surname, year). Studies excluded from Tier 1.

TIER2_RATINGS: dict = {
    (       'Jovaisa T', 2006): {
        'category': 'moderate_positive',
        'basis':    'Randomised, blinded two-group trial of ketamine as an adjuvant to opioid-antagonist induction. The ketamine arm showed significantly less severe withdrawal on the hourly OOWS-A score (p<0.05) and the authors conclude the ketamine group "presented better control of withdrawal symptoms" — a directionally clear, statistically significant between-group advantage on the primary SUD outcome, but reported without a test statistic or group means, so no effect size is derivable. Graded moderate rather than large on the strength of a single significant withdrawal-severity comparison.',
    },
    (       'D.C. Mash', 2000): {
        'category': 'single_arm_positive',
        'basis':    'Single-arm open-label ibogaine trial with no control group. All 5 HCQN-29 opiate-craving subscales (TABLE 2, all p<=.0001) and 3 of 5 CCQN-45 cocaine-craving subscales (TABLE 3) showed statistically significant pre-to-post reductions, and BDI depression scores also decreased significantly across the study (F(3,18)=9.59, p=.0005, TABLE 1) -- a consistently positive pre/post direction across every reported outcome family, with no comparator arm to benchmark against.',
    },
    (       'Krupitsky', 2002): {
        'category': 'moderate_positive',
        'basis':    'High-dose (psychedelic) ketamine group showed significantly higher abstinence / lower relapse than the low-dose active-placebo group from month 1 through nearly all of the 24-month follow-up (Section 3.2), plus greater and longer-lasting craving reduction (Section 3.3) and greater positive change on the Color Test of Attitudes (Section 3.11) — a directionally clear, sustained advantage for the higher psychedelic dose, though without a precise pooled effect size.',
    },
    (       'Krupitsky', 2007): {
        'category': 'large_positive',
        'basis':    'Computed OR=3.50 from two-group abstinence proportions (50% vs 22.2% at 12mo); exceeds OR≥3 threshold.',
        'computed_or': 3.5,
    },
    (         'P. Glue', 2016): {
        'category': 'null',
        'basis':    "The article's only SUD-relevant outcome -- opioid withdrawal ratings (SOWS/OOWS/COWS) and time to resumption of OST -- showed a nonstatistically significant trend toward reduced withdrawal at 120 mg, and near-identical placebo-vs-active time-to-OST-resumption within cohorts (Pearson r=0.993), which the authors attribute to a design confound (shared housing/observation making OST resumption obvious to co-housed participants) rather than to a genuine null effect. No SUD outcome reached significance in either direction.",
    },
    (      'P.L. Prior', 2014): {
        'category': 'moderate_positive',
        'basis':    'Two-arm double-blind placebo-controlled pilot RCT; ibogaine group showed a significantly lower positive-urine (relapse) rate than placebo across 24-week follow-up (F(3,12)=2.45, p=0.023), corroborated by a large, significant reduction in MCCS craving scores in the ibogaine arm vs no change in placebo (p<0.0001). Graded moderate rather than large because the primary urine-positivity effect itself is not reported in a directly quantifiable, group-comparable form (no paired percentages); graded above small/null given significance and consistent direction across two independent outcome measures.',
    },
}
