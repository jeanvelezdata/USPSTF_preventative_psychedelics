"""Per-condition configuration for alcohol psychedelic trials."""

CONDITION_NAME = 'alcohol'
CONDITION_LABEL = 'Alcohol'   # value of the master's Condition column
INPUT_FILE = 'clinical_trials/outputs/clinical_master.csv'

# ── Effect-size extraction table ──────────────────────────────────────────────
# Keyed by (first_author_surname, year). One entry per study.
# (metric, measure, note) — measure is numeric where possible; "X vs Y"
# string for irreducible two-group comparisons.

EFFECT_SIZE_EXTRACTIONS: dict = {
    (     'Bogenschutz', 2015): ("Cohen's d", 1.383, ''),
    (     'Bogenschutz', 2022): ("Hedges' g", 0.52, ''),
    (           'Bowen', 1970): ('Chi-squared', 1.408, 'df=1; 24% vs 27% good adjustment (LSD+HRTL vs control, combined); ns'),
    (          'Dakwar', 2020): ('F', 25.1, "Primary outcome (21-day alcohol abstinence) tested via the time-by-treatment interaction, F(1,797)=25.1, p<.001 (single-numerator-df F, directly convertible to a Hedges' g equivalent); direction=1 because the effect favors ketamine, the psychedelic arm."),
    (             'Das', 2019): ('Partial eta squared', 0.14, "Primary drinking outcome: F(1,89.17)=19.55, p<.001, np2=0.14. The frozen 0.219 belongs to the secondary post-consumption urge measure, which output.md ruled non-primary."),
    (          'Denson', 1970): ('Non-significant (no statistic)', None, 'Outcome not reported'),
    (           'Dusen', 1967): ('Non-significant (no statistic)', '4.03 vs 3.97 (18-month mean outcome score, 2=worse...5=much improved scale; prelysergide control N=37 vs Lysergide Experiment N=56)', 'No SDs reported; ns'),
    (            'Gent', 2024): ('F', 6.88, "Primary outcome (psychological engagement in MBI) tested via the group main effect, F(1,26)=6.88, p=.014, a single-numerator-df F cleanly convertible to a Hedges' g equivalent; direction=1 because the effect favors esketamine (the psychedelic arm) over placebo."),
    (         'Grabski', 2022): ('Mean difference (percentage days abstinent, %), site-adjusted intention-to-treat, ketamine vs. placebo pooled across therapy conditions at 6 months', 10.1, '% heavy drinking days'),
    (     'Heinzerling', 2023): ('F', 15.76, ''),
    (       'Hollister', 1969): ('F', 8.5, ''),
    (          'Jensen', 1963): ('Two-group proportions (%)', '63 vs 27', 'LSD vs control abstinence'),
    (          'Jensen', 2024): ("Cohen's d", 1.02, 'Stenbaek et al. open-label psilocybin'),
    (         'Johnson', 1969): ('Non-significant (no statistic)', None, 'Reported only as "NS"'),
    (         'Kurland', 1967): ('Abstinence rate (%), single-arm', None, 'Single-arm rate; no comparator group'),
    (        'Luquiens', 2025): ('Risk difference (%)', -44, 'Abstinence rate difference'),
    (         'MacLean', 1961): ('Single-arm improvement rate (%)', '46/61 (75.4%)', 'Single-arm improvement rate'),
    (        'Marvania', 2024): ('Paired t-test (within-subjects, no comparator arm)', None, 'AASE pre-post; no comparator'),
    (        'Nicholas', 2022): ("Hedges' g", 0.45, 'AUDIT change'),
    (        "O'Reilly", 1964): ('Abstinence rate (%)', '38% (26/68)', 'Single-arm rate'),
    (           'Pagni', 2024): ('Whole-brain fMRI cluster-level statistics (multiple discrete clusters comprising the primary outcome; no single scalar effect size)', None, 'fMRI craving reduction; df=3'),
    (           'Pagni', 2025): ('Partial eta squared', 0.06, 'Openness scale'),
    (          'Pahnke', 1970): ('Two-group proportions (%)', '53 vs 33', 'High vs low dose'),
    (          'Rieser', 2025): ("Cohen's d", 0.151, ''),
    (        'Rothberg', 2021): ('Odds ratio (approximate)', 2.98, 'OR approximate'),
    (           'Sessa', 2019): ('Single-arm rate (no inferential statistic)', '4/4 (100%) tolerated; 2/4 alcohol-free, 2/4 single low-dose lapse only', '2/4 abstinent; case series'),
    (           'Sessa', 2021): ('Descriptive completion/safety rate (no inferential statistic)', None, 'units/wk pre vs 9mo, no comparator'),
    (           'Smart', 1966): ('Non-significant 3-group ANOVA (multi-df F) — percentage gain in abstinence', '34 vs 32 vs 20 (%, lysergide vs ephedrine vs control)', 'LSD vs control abstinence gain; ns'),
    (           'Smith', 1958): ('Single-arm improvement rate (%)', '12/24 (50%)', '12/24; single-arm'),
    (        'Terasaki', 2022): ('Risk ratio', 0.37, 'KET vs LA arm'),
    (         'Thurgur', 2025): ('Bayesian posterior probability (single-arm binomial success rate)', '9/14 (Bayesian posterior probability of treatment success: 0.63 flat prior, 0.55 skeptical prior)', 'Flat prior'),
    (        'Tomsovic', 1970): ('Chi-squared', 7.19, "χ²(1)=7.19 (Table 7) comparing nonschizophrenic lysergide-treated (n=32) vs. nonschizophrenic control group I (n=26) on 1-year abstinence/nonabstinence classification. The article explicitly states the applicable critical value is for df=1 ('Chi square for .05 level of confidence with df 1 = 3.84'), confirming a genuine 1-df 2x2 comparison, so convert_to_d()'s 1-df assumption holds cleanly here. Direction=1 because the result favors lysergide (higher abstinence). Note the authors themselves question the validity of this specific comparison (possible 'deprivation effect' inflating the gap via control group I's unusually poor outcomes), which is a substantive caveat for methodologist review even though the statistic itself converts cleanly."),
    (            'Yoon', 2019): ('Single-arm response rate (%)', None, 'Case series 5/5'),
}

# ── Conversion rules ──────────────────────────────────────────────────────────
# Keyed by (first_author_surname, year).
# direction defaults to +1; set -1 when the metric's natural sign is
# opposite to the favoured treatment direction.

CONVERSION_RULES: dict = {
    (     'Bogenschutz', 2015): {'method': 'd', 'confidence': 'clean'},
    (     'Bogenschutz', 2022): {'method': 'g', 'confidence': 'clean', 'note': "Authors report Hedges' g = 0.52 (95% CI 0.11-0.94) directly for the primary PHDD between-group contrast at weeks 5-36 (Table 2/Efficacy text); this is a direct pass-through of an author-computed Hedges g, no conversion required. Article's own convention already orients positive g toward the favored (psilocybin) direction, so direction=1."},
    (           'Bowen', 1970): {'method': 'chi2', 'confidence': 'approx', 'direction': -1, 'note': 'χ²=1.408, p>0.05; 24% vs 27% good adjustment; treatment direction slightly negative'},
    (          'Dakwar', 2020): {'method': 'F', 'df_error': 797, 'confidence': 'clean', 'note': "Primary outcome (21-day alcohol abstinence) tested via the time-by-treatment interaction, F(1,797)=25.1, p<.001 (single-numerator-df F, directly convertible to a Hedges' g equivalent); direction=1 because the effect favors ketamine, the psychedelic arm."},
    (             'Das', 2019): {'method': 'eta_p', 'confidence': 'clean'},
    (          'Denson', 1970): {'method': None, 'confidence': 'excluded', 'note': 'No outcome statistic reported'},
    (           'Dusen', 1967): {'method': None, 'confidence': 'excluded', 'note': 'Group means without SDs; ns'},
    (            'Gent', 2024): {'method': 'F', 'df_error': 26, 'confidence': 'clean', 'note': "Primary outcome (psychological engagement in MBI) tested via the group main effect, F(1,26)=6.88, p=.014, a single-numerator-df F cleanly convertible to a Hedges' g equivalent; direction=1 because the effect favors esketamine (the psychedelic arm) over placebo."},
    (         'Grabski', 2022): {'method': None, 'confidence': 'excluded', 'note': 'Mean difference reported without SDs'},
    (     'Heinzerling', 2023): {'method': None, 'confidence': 'excluded', 'note': 'F has 6 df numerator; repeated-measures design'},
    (       'Hollister', 1969): {'method': 'F', 'df_error': 50, 'confidence': 'clean', 'direction': -1, 'note': 'Sig. F unfavorable to LSD vs dextroamphetamine'},
    (          'Jensen', 1963): {'method': None, 'confidence': 'excluded', 'note': 'Two-group proportions; downgrade to Tier 2'},
    (          'Jensen', 2024): {'method': 'd', 'confidence': 'clean'},
    (         'Johnson', 1969): {'method': None, 'confidence': 'excluded', 'note': 'Reported only as "NS"'},
    (         'Kurland', 1967): {'method': None, 'confidence': 'excluded', 'note': 'Single-arm rate; no comparator'},
    (        'Luquiens', 2025): {'method': None, 'confidence': 'excluded', 'note': 'Risk difference only; downgrade to Tier 2'},
    (         'MacLean', 1961): {'method': None, 'confidence': 'excluded', 'note': 'Single-arm improvement rate'},
    (        'Marvania', 2024): {'method': None, 'confidence': 'excluded', 'note': 'Within-group AASE change; no comparator'},
    (        'Nicholas', 2022): {'method': 'g', 'confidence': 'clean', 'note': "Authors directly report Hedge's g=.45 for the AUDIT (alcohol) change-score group difference, MDMA-AT vs Placebo+Therapy (Abstract; §3.2); this is a direct pass-through of an author-computed Hedges' g requiring no conversion, and the reported positive value already favors MDMA-AT (greater alcohol-use reduction), so direction=1."},
    (        "O'Reilly", 1964): {'method': None, 'confidence': 'excluded', 'note': 'Single-arm abstinence rate'},
    (           'Pagni', 2024): {'method': None, 'confidence': 'excluded', 'note': 'Within-subjects t (df=3); not between-groups'},
    (           'Pagni', 2025): {'method': 'eta_p', 'confidence': 'approx', 'note': 'Small N=84, partial eta^2 conversion approximate'},
    (          'Pahnke', 1970): {'method': None, 'confidence': 'excluded', 'note': 'Two dose-group proportions; downgrade to Tier 2'},
    (          'Rieser', 2025): {'method': 'd', 'confidence': 'clean', 'note': "Cohen's d = 0.151 for abstinence duration (psilocybin vs. placebo, 4-week follow-up) is directly reported by the authors and requires no derivation, so it is a clean d-to-Hedges'-g pass-through. Flagging for human awareness: this same d-value is paired with two different p-values in the article (p=0.55 in the Abstract vs. p=0.37 in the Results narrative) - an unresolved internal inconsistency in the source article that does not affect the d-value itself but affects interpretation of its significance."},
    (        'Rothberg', 2021): {'method': 'OR', 'confidence': 'approx', 'note': 'OR=2.98 computed from Table 2 (ketamine 4/17 vs midazolam 11/23 engaged in at-risk drinking post-infusion), expressed as midazolam:ketamine odds so that >1 already favours ketamine; direction=+1. The frozen entry carried direction=-1 to pair with an OR expressed the other way round, and keeping it after the computed OR was promoted into measure double-negated the sign, plotting a beneficial result as harmful.'},
    (           'Sessa', 2019): {'method': None, 'confidence': 'excluded', 'note': 'Case series 2/4 abstinent; no comparator'},
    (           'Sessa', 2021): {'method': None, 'confidence': 'excluded', 'note': 'Within-group mean change; no comparator'},
    (           'Smart', 1966): {'method': None, 'confidence': 'excluded', 'note': 'Two-group proportions; downgrade to Tier 2'},
    (           'Smith', 1958): {'method': None, 'confidence': 'excluded', 'note': 'Single-arm improvement rate'},
    (        'Terasaki', 2022): {'method': 'RR', 'confidence': 'approx', 'direction': -1, 'note': 'RR=0.37 = LESS readmission (favors ketamine); sign flipped'},
    (         'Thurgur', 2025): {'method': None, 'confidence': 'excluded', 'note': 'Bayesian posterior not directly convertible'},
    (        'Tomsovic', 1970): {'method': 'chi2', 'confidence': 'clean', 'note': "χ²(1)=7.19 (Table 7) comparing nonschizophrenic lysergide-treated (n=32) vs. nonschizophrenic control group I (n=26) on 1-year abstinence/nonabstinence classification. The article explicitly states the applicable critical value is for df=1 ('Chi square for .05 level of confidence with df 1 = 3.84'), confirming a genuine 1-df 2x2 comparison, so convert_to_d()'s 1-df assumption holds cleanly here. Direction=1 because the result favors lysergide (higher abstinence). Note the authors themselves question the validity of this specific comparison (possible 'deprivation effect' inflating the gap via control group I's unusually poor outcomes), which is a substantive caveat for methodologist review even though the statistic itself converts cleanly."},
    (            'Yoon', 2019): {'method': None, 'confidence': 'excluded', 'note': 'Case series 5/5 response; no comparator'},
}

# ── Tier 2 qualitative ratings ────────────────────────────────────────────────
# Keyed by (first_author_surname, year). Studies excluded from Tier 1.

TIER2_RATINGS: dict = {
    (          'Denson', 1970): {
        'category': 'null',
        'basis':    "Significant-difference counts across MMPI (6/126), Lorr (2/90), IPAT (0), Eysenck/Maudsley (2/27), and Questionnaire (9/165) comparisons approximate the ~5% rate expected by chance; the one nominally 'positive' finding (general health) is explicitly deemed insufficient by the authors, who conclude the results were negative/null overall.",
    },
    (           'Dusen', 1967): {
        'category': 'null',
        'basis':    "The lysergide-experiment group's 18-month mean (3.97) is numerically lower than the prelysergide historical-control group's (4.03), and the article states differences across all groups 'did not even approach significance' by chi-square and Duncan's range test; the study's own conclusion is that lysergide 'did not increase the patients' abstinence.'",
    },
    (            'Gent', 2024): {
        'category': 'large_positive',
        'basis':    'F(2,df)=6.45, p<0.01 in 3-arm RCT; overall ANOVA significant, favoring active treatment over placebo.',
    },
    (         'Grabski', 2022): {
        'category': 'moderate_positive',
        'basis':    'Significant ITT mean difference of 10.1 percentage points (95% CI 1.1, 19.0) in percentage days abstinent at 6 months, ketamine vs. placebo pooled across therapy arms, in a 4-arm double-blind RCT (N=89 analyzed at this timepoint); the co-primary relapse outcome was null (OR=0.70, 95% CI 0.28-1.75).',
    },
    (     'Heinzerling', 2023): {
        'category': 'large_positive',
        'basis':    'F(6,df)=15.76 for time-by-treatment interaction, p<0.001; repeated-measures design with sustained treatment advantage.',
    },
    (          'Jensen', 1963): {
        'category': 'large_positive',
        'basis':    'Computed OR=4.60 from two-group abstinence proportions (63% vs 27%); exceeds OR≥3 threshold.',
        'computed_or': 4.6,
    },
    (         'Johnson', 1969): {
        'category': 'null',
        'basis':    'All four arms (two LSD arms, an active-drug control, and a no-drug routine-care control) showed statistically significant pre-to-post improvement on drinking indices (p<.01 to p<.10), but the ANOVA between-groups test was non-significant on every criterion in Table 4, and the authors explicitly conclude LSD conferred no advantage over the comparator conditions -- a null differential-effect result rather than a negative one.',
    },
    (         'Kurland', 1967): {
        'category': 'single_arm_positive',
        'basis':    "23/69 (33%) maintained abstinence at 6-month follow-up in a single-arm, open-label pilot; MMPI clinical-scale changes reported as significant and in a positive direction; authors state 'no patient has been harmed' and describe benefit as 'considerable' in some cases.",
    },
    (        'Luquiens', 2025): {
        'category': 'negative',
        'basis':    'Risk difference = -44 percentage points in abstinence rate; treatment arm had substantially lower abstinence than comparator.',
    },
    (         'MacLean', 1961): {
        'category': 'single_arm_positive',
        'basis':    '75.4% (46/61) of the alcoholic subgroup was rated much improved or improved on the composite outcome (which for alcoholics required abstinence or a definite reduction in drinking versus the prior 12 months), a directionally positive single-arm result with no control group.',
    },
    (        'Marvania', 2024): {
        'category': 'single_arm_positive',
        'basis':    'Statistically significant within-subject increase in AASE confidence-to-abstain score sustained from baseline to 2-week post-treatment follow-up (51.98% increase, T=-4.982, p<0.05), in a single-arm study with no comparator group.',
    },
    (        "O'Reilly", 1964): {
        'category': 'single_arm_positive',
        'basis':    "38% abstinence (26/68) at follow-up (mean 14 months post-treatment), explicitly framed by the authors as having 'produced sobriety... without any disastrous side effects' — a positive pre/post result in a single-arm design.",
    },
    (           'Pagni', 2024): {
        'category': 'moderate_positive',
        'basis':    "Significant reduction in psilocybin-group cue-elicited craving post-treatment (t(3)=5.568, p=0.0114) plus multiple significant whole-brain treatment-by-time interaction clusters in the direction the authors interpret as therapeutic (increased PFC/caudate engagement, decreased insula/motor/cerebellar activity), tempered by the very small pilot sample (n=11), uncorrected p<.005 whole-brain threshold, and the authors' own caution that some directionality is not straightforwardly consistent with AUD-circuit normalization.",
    },
    (          'Pahnke', 1970): {
        'category': 'moderate_positive',
        'basis':    'Computed OR=2.29 from two-group abstinence proportions (53% vs 33%); falls in OR 1.5-3 range.',
        'computed_or': 2.29,
    },
    (           'Sessa', 2019): {
        'category': 'single_arm_positive',
        'basis':    'All 4 participants avoided harmful/daily drinking post-treatment (2 fully alcohol-free, 2 with only a single low-dose lapse), no serious adverse events, and improvement on GAD-7, PHQ-9, SF-36 and SCS — a favorable single-arm pre/post pattern with no comparator.',
    },
    (           'Sessa', 2021): {
        'category': 'single_arm_positive',
        'basis':    'Single-arm design with a favourable within-subject direction on both the primary outcome (85.7% completed both MDMA sessions, no unexpected AEs) and the secondary outcome (alcohol consumption fell from 130.6 to 18.7 units/week at 9-month follow-up; 9/14 totally abstinent).',
    },
    (           'Smart', 1966): {
        'category': 'null',
        'basis':    "Non-significant omnibus test across lysergide/ephedrine/control on the abstract-leading abstinence-gain outcome; lysergide had the numerically largest gain (~34%) but was statistically indistinguishable from the active ephedrine comparator (~32%) and not clearly superior to the no-drug control (~20%), and every other reported drinking-behavior outcome (drinking occasions, drunkenness occasions, symptom checklist, clinic contacts) was also non-significant between groups — the authors' own conclusion is that lysergide 'failed as an effective adjunct to psychotherapy.'",
    },
    (           'Smith', 1958): {
        'category': 'single_arm_positive',
        'basis':    '50% of a deliberately refractory, A.A.-failure alcoholic sample (12/24) were rated much improved or improved on drinking outcome post-treatment, none worsened, and the authors characterize the results as sufficiently encouraging to justify further controlled trials.',
    },
    (         'Thurgur', 2025): {
        'category': 'single_arm_positive',
        'basis':    'Single-arm, open-label secondary analysis; 9/14 (64%) participants achieved the pre-defined 2-level WHO drinking-risk reduction success threshold, with Bayesian posterior probability of success 55-63% depending on prior, and multiple secondary craving/sleep/self-compassion PROMs improved significantly at 3 months -- directionally positive though the preliminary frequentist binomial test against a 50% null was not significant (P=.423).',
    },
    (            'Yoon', 2019): {
        'category': 'single_arm_positive',
        'basis':    '100% (5/5) met the pre-specified clinical response criterion by the fourth ketamine infusion, and 80% (4/5) reported improved alcohol craving/consumption on the OCDS, in a single-arm open-label design with no comparator.',
    },
}
