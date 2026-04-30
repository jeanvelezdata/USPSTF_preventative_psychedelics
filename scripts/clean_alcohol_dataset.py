"""
Clean the psychedelic-alcohol clinical-trial extraction dataset.

Operations performed:
1. Strip whitespace and replace '.' with NaN globally (codebook signal for "not reported").
2. Coerce numeric columns stored as object dtype.
3. Collapse Country_USvsNonUS categories: 'USA' -> 'US'; 'Both' -> 'US and Non-US'.
4. Fix Age_Median: numeric stray '45' -> '30-50'; convert to ordered categorical.
5. Replace '3' with 'Does not apply' ONLY in binary columns (per codebook).
   Continuous columns like 'Followup in months' are left alone, where 3 = 3 months.
6. Round float-precision artifacts on Retention (%).
7. Make BaseStatus an ordered categorical (Mild < Moderate < Severe).
8. Split the free-text Outcome column into two new fields:
     - metric: name of the primary effect-size statistic (e.g., "Cohen's d", "F", "Odds ratio")
     - measure: numeric value (or "X vs Y" string for irreducible two-value comparisons)
   Selection rule: prefer the metric most useful for Tier 1 standardization to Hedges' g
   (Cohen's d / Hedges' g > partial η² > F/t/χ² with df > OR/RR > two-group proportions
   > single proportions > narrative-only). Where multiple statistics are reported in a
   single Outcome cell, the one chosen is the cleanest path to a standardized d.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

_BASE  = Path(__file__).parent.parent
INPUT  = _BASE / 'data' / 'Alcohol_Dataset.xlsx'
OUTPUT = _BASE / 'data' / 'Alcohol_Dataset_Cleaned.xlsx'

# Columns where 3 = "Not applicable" per the codebook.
# Excludes continuous columns (e.g., Followup in months) where 3 is a real value.
BINARY_COLS = [
    'Pos Result Y/N', 'Clincial Trial YN', 'RandomizationYN', 'BlindingYN',
    'Double+Blind', 'Comparator', 'PrimaryCare', 'Power', 'ConfoundYN',
    'InclusionExclusionCriteria', 'ValidatedScaleMeasYN', 'MethodologyDescribedYN',
    'Funding/COI YN', 'SocioeconomicStatusYN', 'RecruitmentRepresentYN',
    'InterventionTherapy', 'HarmsAssessed', 'CulturalFraming',
    'IndigenousFramework', 'Reciprocity', 'BehaviorChangeMeasured',
    'PhysicalChangeMeasured', 'MentalHealthChangeMeasured', 'QualityOfLifeMeasured',
    'Implementation Outcome', 'ReductionMeasured', 'CessationMeasured',
    'RelapseMeasured', 'MortalityMeasured', 'Psilocybin', 'Ayahuasca', 'LSD',
    'Mescaline', 'Ibogaine', 'MDMA', 'Ketamine', 'Cannabis', 'OtherPsychedelic',
    'MultiplePsychedelic',
]

# Columns that should be numeric but are stored as object due to embedded '.'
NUMERIC_COLS = [
    'Retention (%)', 'PercentFem', 'RaceEthnicity_BIPOCPercent',
]

COUNTRY_MAP = {
    'USA': 'US',
    'US': 'US',
    'NonUS': 'Non-US',
    'Both': 'US and Non-US',
}

AGE_CATEGORIES = ['<30', '30-50', '50+']
SEVERITY_CATEGORIES = ['Mild', 'Moderate', 'Severe']

# -----------------------------------------------------------------------------
# Effect-size extraction table.
#
# Keyed by (first_author_surname, year). One entry per study. Where the raw
# Outcome cell reported multiple statistics, the metric chosen is the one that
# offers the cleanest Tier 1 conversion to Hedges' g.
#
# `measure` is numeric whenever possible. For irreducible two-group comparisons
# (e.g., proportions in two arms with no derived ES reported), a "X vs Y" string
# is used so both values are preserved for downstream Cohen's h or OR conversion.
# -----------------------------------------------------------------------------
EFFECT_SIZE_EXTRACTIONS = {
    # (surname, year): (metric, measure, note)
    ('Bogenschutz', 2015): ("Cohen's d",                    1.383,         ''),
    ('Bogenschutz', 2022): ("Hedges' g",                    0.52,          ''),
    ('Bowen',       1970): (None,                           None,          'Outcome not reported'),
    ('Dakwar',      2020): ('F',                            25.1,          'F preferred over NNT for Tier 1 (df reported)'),
    ('Das',         2019): ('Partial eta squared',          0.219,         ''),
    ('Denson',      1970): (None,                           None,          'Outcome not reported'),
    ('Dusen',       1967): ('Group means (Tx vs Ctrl)',     '3.97 vs 4.03', 'No SDs reported; ns'),
    ('Gent',        2024): ('F',                            6.45,          ''),
    ('Grabski',     2022): ('Mean difference (%)',          10.1,          '% heavy drinking days'),
    ('Heinzerling', 2023): ('F',                            15.76,         ''),
    ('Hollister',   1969): ('F',                            8.5,           ''),
    ('Jensen',      2024): ("Cohen's d",                    1.02,          'Stenbaek et al. open-label psilocybin'),
    ('Jensen',      1963): ('Two-group proportions (%)',    '63 vs 27',    'LSD vs control abstinence'),
    ('Johnson',     1969): ('Non-significant (no statistic)', None,        'Reported only as "NS"'),
    ('Kurland',     1967): ('Abstinence rate (%)',          33.3,          'Single-arm rate; no comparator group'),
    ('Luquiens',    2025): ('Risk difference (%)',          -44,           'Abstinence rate difference'),
    ('MacLean',     1961): ('Improvement rate (%)',         49,            'Single-arm improvement rate'),
    ('Marvania',    2024): ('Within-group change (%)',      51.98,         'AASE pre-post; no comparator'),
    ('Nicholas',    2022): ("Hedges' g",                    0.45,          'AUDIT change'),
    ("O'Reilly",    1964): ('Abstinence rate (%)',          38,            'Single-arm rate'),
    ('Pagni',       2025): ('Partial eta squared',          0.07,          'Openness scale'),
    ('Pagni',       2024): ('t',                            5.568,         'fMRI craving reduction; df=3'),
    ('Pahnke',      1970): ('Two-group proportions (%)',    '53 vs 33',    'High vs low dose'),
    ('Rieser',      2025): ("Cohen's d",                    0.151,         ''),
    ('Rothberg',    2020): ('Odds ratio',                   5.0,           'OR approximate'),
    ('Sessa',       2021): ('Within-group mean change',     '18.7 vs 130.6', 'units/wk pre vs 9mo, no comparator'),
    ('Sessa',       2019): ('Abstinence rate (%)',          50,            '2/4 abstinent; case series'),
    ('Smart',       1966): ('Two-group proportions (%)',    '33.7 vs 19.6', 'LSD vs control abstinence gain; ns'),
    ('Smith',       1958): ('Improvement rate (%)',         50,            '12/24; single-arm'),
    ('Terasaki',    2022): ('Risk ratio',                   0.37,          'KET vs LA arm'),
    ('Thurgur',     2025): ('Bayesian posterior probability', 0.63,        'Flat prior'),
    ('Tomsovic',    1970): ('Chi-squared',                  7.19,          'df=1; LSD vs control I'),
    ('Yoon',        2019): ('Response rate (%)',            100,           'Case series 5/5'),
}


def first_author_surname(citation: str) -> str:
    """Return the surname of the first author from a citation string.

    Normalizes curly apostrophes (e.g., O\u2019Reilly) to straight ones so
    keys in EFFECT_SIZE_EXTRACTIONS can use plain ASCII apostrophes.
    """
    surname = re.split(r'[,;]', str(citation).strip(), maxsplit=1)[0].strip()
    return surname.replace('\u2019', "'").replace('\u2018', "'")


def extract_effect_size_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add `metric` and `measure` columns derived from Outcome via the lookup table."""
    metrics, measures = [], []
    unmatched = []
    for _, row in df.iterrows():
        key = (first_author_surname(row['Citation/Title']), int(row['Year']))
        if key in EFFECT_SIZE_EXTRACTIONS:
            metric, measure, _note = EFFECT_SIZE_EXTRACTIONS[key]
            metrics.append(metric if metric is not None else np.nan)
            measures.append(measure if measure is not None else np.nan)
        else:
            unmatched.append(key)
            metrics.append(np.nan)
            measures.append(np.nan)
    if unmatched:
        raise KeyError(
            f"No effect-size extraction defined for {len(unmatched)} row(s): {unmatched}. "
            "Add entries to EFFECT_SIZE_EXTRACTIONS."
        )
    df = df.copy()
    df['metric'] = metrics
    df['measure'] = measures
    # Reorder so metric/measure sit right after the original Outcome column
    cols = list(df.columns)
    cols.remove('metric')
    cols.remove('measure')
    out_idx = cols.index('Outcome')
    cols = cols[:out_idx + 1] + ['metric', 'measure'] + cols[out_idx + 1:]
    return df[cols]


def recode_binary(series: pd.Series) -> pd.Series:
    """Convert a binary column to {0, 1, 'Does not apply', NaN}.

    Resulting dtype is object so the integer codes can coexist with the
    'Does not apply' string label.
    """
    numeric = pd.to_numeric(series, errors='coerce')
    out = pd.Series(np.nan, index=series.index, dtype=object)
    out[numeric == 0] = 0
    out[numeric == 1] = 1
    out[numeric == 3] = 'Does not apply'
    return out


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Strip whitespace and replace '.' with NaN across string-like columns
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].astype('string').str.strip()
        df[col] = df[col].replace({'.': pd.NA, '': pd.NA})

    # 2. Coerce designated numeric columns
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'Retention (%)' in df.columns:
        df['Retention (%)'] = df['Retention (%)'].round(1)

    # 3. Collapse country categories
    if 'Country_USvsNonUS' in df.columns:
        df['Country_USvsNonUS'] = (
            df['Country_USvsNonUS'].map(COUNTRY_MAP).fillna(df['Country_USvsNonUS'])
        )

    # 4. Age_Median: stray numeric '45' -> '30-50'; ordered categorical
    if 'Age_Median' in df.columns:
        df['Age_Median'] = df['Age_Median'].astype('string').replace({'45': '30-50'})
        df['Age_Median'] = pd.Categorical(
            df['Age_Median'], categories=AGE_CATEGORIES, ordered=True
        )

    # 5. Recode binary columns: 3 -> 'Does not apply'; 0/1 preserved as ints
    for col in BINARY_COLS:
        if col in df.columns:
            df[col] = recode_binary(df[col])

    # 6. Ordered categorical for baseline severity
    if 'BaseStatus' in df.columns:
        df['BaseStatus'] = pd.Categorical(
            df['BaseStatus'], categories=SEVERITY_CATEGORIES, ordered=True
        )

    # 7. Split Outcome into metric + measure
    df = extract_effect_size_fields(df)

    return df


def main():
    df_raw = pd.read_excel(INPUT)
    df_clean = clean(df_raw)

    print(f"Rows: {len(df_clean)} | Columns: {len(df_clean.columns)}")

    print("\nCountry_USvsNonUS after collapse:")
    print(df_clean['Country_USvsNonUS'].value_counts(dropna=False).to_string())

    print("\nAge_Median after fix:")
    print(df_clean['Age_Median'].value_counts(dropna=False).to_string())

    print("\nBaseStatus after fix:")
    print(df_clean['BaseStatus'].value_counts(dropna=False).to_string())

    print("\nBinary columns now containing 'Does not apply':")
    found = False
    for col in BINARY_COLS:
        n = (df_clean[col] == 'Does not apply').sum()
        if n:
            print(f"  {col}: {n}")
            found = True
    if not found:
        print("  (none)")

    print("\nMetric distribution (new column):")
    print(df_clean['metric'].value_counts(dropna=False).to_string())

    print("\nMetric × measure preview (first 10):")
    print(df_clean[['Year', 'metric', 'measure']].head(10).to_string())

    df_clean.to_excel(OUTPUT, index=False)
    print(f"\nWritten to: {OUTPUT}")


if __name__ == '__main__':
    main()
