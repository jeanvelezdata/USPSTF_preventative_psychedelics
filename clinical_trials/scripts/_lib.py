"""Schema, value domains and validators for the clinical-trial extraction.

Authoritative Python encoding of clinical_codebook.md §4–§5 and the §8 gate.
merge_validate.py, reconcile_manifest.py and apply_config_proposals.py all
import from here so the column set and value domains are defined exactly once.

Two missingness conventions coexist in clinical_master and the split is by
field origin, not field meaning (codebook §3):

  * the 54 carried source variables use the numeric codes 1 / 0 / 3 / "."
    so scripts/_lib.recode_binary(), BINARY_COLS and descriptive_analyses.py
    keep working untouched;
  * the 18 added QC/provenance fields use Y/N-style string enums so the AE
    gate-consistency rules transfer verbatim from the observational pipeline.

Nothing here is condition-specific; Condition is a column, not a file.
"""

from __future__ import annotations

from typing import Any, Callable

# ── Column sets (design §6.1) ────────────────────────────────────────────

# The 54 columns carried verbatim from the frozen files: all 56 original
# columns minus `url or link to pdf` and `Study Design Type`. Spellings are
# preserved exactly, including the misspelling `Clincial Trial YN` and the
# punctuation in `Funding/COI YN`, `Retention (%)`, `Followup in months`,
# `Implementation Outcome`, `Double+Blind` and `Pos Result Y/N`.
CARRIED_FIELDS: list[str] = [
    'Citation/Title', 'Condition', 'Year',
    'Pos Result Y/N', 'Outcome', 'SD', 'PVal',
    'Clincial Trial YN', 'RandomizationYN', 'BlindingYN', 'Double+Blind',
    'Comparator', 'SampleSize_NFinal', 'PrimaryCare', 'Power', 'Retention (%)',
    'ConfoundYN', 'InclusionExclusionCriteria', 'ValidatedScaleMeasYN',
    'MethodologyDescribedYN', 'Funding/COI YN',
    'BaseStatus', 'Age_Median', 'PercentFem', 'RaceEthnicity_BIPOCPercent',
    'SocioeconomicStatusYN', 'Country_USvsNonUS', 'RecruitmentRepresentYN',
    'InterventionDescription', 'InterventionTherapy', 'HarmsAssessed',
    'CulturalFraming', 'IndigenousFramework', 'Reciprocity',
    'Followup in months', 'BehaviorChangeMeasured', 'PhysicalChangeMeasured',
    'MentalHealthChangeMeasured', 'QualityOfLifeMeasured', 'Implementation Outcome',
    'ReductionMeasured', 'CessationMeasured', 'RelapseMeasured', 'MortalityMeasured',
    'Psilocybin', 'Ayahuasca', 'LSD', 'Mescaline', 'Ibogaine', 'MDMA',
    'Ketamine', 'Cannabis', 'OtherPsychedelic', 'MultiplePsychedelic',
]

ADDED_FIELDS: list[str] = [
    'StudyID',
    'EligibleYN', 'EligibilityFailedCriterion', 'EligibilityNote',
    'BaseStatusReportedYN',
    'SafetyReported', 'AnyAEReported', 'NumDistinctAEs', 'NParticipantsWithAE',
    'AE_denominator', 'ArmScope', 'WorstSeverity',
    'text_source', 'text_format',
    'Model', 'PromptVersion', 'RubricVersion', 'Temperature', 'SourcePDF',
]

# Computed by write_outputs after the merge, so they are master columns but are
# never present on an extraction response and are exempt from the column check.
DERIVED_FIELDS: frozenset[str] = frozenset({'BaseStatusReportedYN'})

# StudyID leads the master so the CSV is readable; the rest keep source order.
ARTICLE_FIELDS: list[str] = ['StudyID'] + CARRIED_FIELDS + [
    f for f in ADDED_FIELDS if f != 'StudyID'
]

AE_EVENT_FIELDS: list[str] = [
    'AE_ID', 'StudyID', 'AE_type', 'Description', 'NAffected', 'Onset',
    'Severity', 'SeverityIndeterminate', 'SeveritySource',
    'InterventionRequired', 'MeetsFDASerious',
]

PROVENANCE_FIELDS: list[str] = [
    'Model', 'PromptVersion', 'RubricVersion', 'Temperature',
    'text_source', 'text_format', 'SourcePDF',
]

# The four fields that position the forest plot (codebook §4.3). A rationale
# entry is mandatory for each on every article, not only the non-obvious ones.
TIER1_FIELDS: list[str] = ['Outcome', 'SD', 'PVal', 'SampleSize_NFinal']

# ── Value domains ────────────────────────────────────────────────────────

# Numeric-coded binaries accepting 1 / 0 / 3 / "." (codebook §3.1).
BINARY_SOURCE_COLS: list[str] = [
    'Pos Result Y/N', 'Clincial Trial YN', 'RandomizationYN', 'BlindingYN',
    'Double+Blind', 'Comparator', 'PrimaryCare', 'Power', 'ConfoundYN',
    'InclusionExclusionCriteria', 'ValidatedScaleMeasYN', 'MethodologyDescribedYN',
    'Funding/COI YN', 'SocioeconomicStatusYN', 'RecruitmentRepresentYN',
    'InterventionTherapy', 'HarmsAssessed', 'CulturalFraming',
    'IndigenousFramework', 'Reciprocity',
]

# The nine outcome binaries are documented with no `3` code (codebook §4.8);
# a 3 would not break recode_binary() but is not a valid emission, so it is a
# warning rather than a block.
OUTCOME_BINARY_COLS: list[str] = [
    'BehaviorChangeMeasured', 'PhysicalChangeMeasured', 'MentalHealthChangeMeasured',
    'QualityOfLifeMeasured', 'Implementation Outcome', 'ReductionMeasured',
    'CessationMeasured', 'RelapseMeasured', 'MortalityMeasured',
]

# Substance flags are 1/0 only (codebook §4.9) — primary_substance() reads them
# directly and any other value silently routes a study to 'Unknown' grey.
SUBSTANCE_BINARY_COLS: list[str] = [
    'Psilocybin', 'Ayahuasca', 'LSD', 'Mescaline', 'Ibogaine', 'MDMA',
    'Ketamine', 'Cannabis', 'OtherPsychedelic', 'MultiplePsychedelic',
]

# The nine keyed substances, excluding the MultiplePsychedelic roll-up.
SUBSTANCE_FLAGS: list[str] = [c for c in SUBSTANCE_BINARY_COLS if c != 'MultiplePsychedelic']

PERCENT_COLS: list[str] = ['Retention (%)', 'PercentFem', 'RaceEthnicity_BIPOCPercent']

CONDITIONS: tuple[str, ...] = ('Alcohol', 'Smoking', 'Opioid')
BASE_STATUS: tuple[str, ...] = ('Severe', 'Moderate', 'Mild')
AGE_BRACKETS: tuple[str, ...] = ('<30', '30-50', '50+')
COUNTRIES: tuple[str, ...] = ('US', 'NonUS', 'Both')
ELIGIBILITY_FAILURES: tuple[str, ...] = (
    'not_clinical_trial', 'no_sud_outcome', 'out_of_scope_substance', 'both', 'NA',
)
ARM_SCOPES: tuple[str, ...] = ('psychedelic_arm', 'pooled', 'NA')
WORST_SEVERITIES: tuple[str, ...] = ('Mild', 'Moderate', 'Severe', 'None', 'NA')
TEXT_SOURCES: tuple[str, ...] = ('born-digital', 'OCR', 'manual')
TEXT_FORMATS: tuple[str, ...] = ('markdown', 'text')

AE_TYPES: tuple[str, ...] = ('AE', 'challenging_experience', 'both')
ONSETS: tuple[str, ...] = ('in-session', 'post-session-acute', 'delayed', 'unknown')
SEVERITIES: tuple[str, ...] = ('Mild', 'Moderate', 'Severe')
SEVERITY_SOURCES: tuple[str, ...] = ('author', 'rubric')

SEVERITY_RANK: dict[str, int] = {'Mild': 1, 'Moderate': 2, 'Severe': 3}

# The 14 MethodologyDescribedYN criteria, in fixed order (codebook §4.4).
METHODOLOGY_CRITERIA: list[str] = [
    'objective', 'design', 'setting', 'eligibility', 'intervention', 'comparator',
    'outcomes', 'sample_size_power', 'randomization', 'blinding',
    'statistical_methods', 'results', 'harms', 'funding_coi',
]
METHODOLOGY_THRESHOLD = 13

# The seven conversion methods scripts/_lib.convert_to_d() implements. A
# config proposal may only claim confidence='clean' on one of these (§5.3).
SUPPORTED_METHODS: tuple[str, ...] = ('d', 'g', 'eta_p', 'F', 'chi2', 'OR', 'RR')

CONFIDENCE_BANDS: tuple[str, ...] = ('clean', 'approx', 'excluded')

TIER2_CATEGORIES: tuple[str, ...] = (
    'negative', 'null', 'small_positive', 'moderate_positive', 'large_positive',
    'single_arm_positive', 'unclassifiable',
)

# Pinned versions stamped into every request and asserted on every response.
MODEL = 'claude-sonnet-5'
PROMPT_VERSION = 'v1.2'
RUBRIC_VERSION = 'v1'
TEMPERATURE = 0

# ── Primitive predicates ─────────────────────────────────────────────────

NOT_REPORTED = '.'


def is_nonempty_text(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != '' and v.strip() != NOT_REPORTED


def is_number(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str):
        try:
            float(v.strip())
            return True
        except ValueError:
            return False
    return False


def as_number(v: Any) -> float | None:
    return float(str(v).strip()) if is_number(v) else None


def is_integer(v: Any) -> bool:
    n = as_number(v)
    return n is not None and float(n).is_integer()


def is_missing(v: Any) -> bool:
    """The source-variable not-reported marker. Only the literal '.' counts."""
    return v == NOT_REPORTED


def binary_code(allow_3: bool = True) -> Callable[[Any], bool]:
    allowed = {0, 1, 3} if allow_3 else {0, 1}

    def check(v: Any) -> bool:
        if is_missing(v):
            return True
        n = as_number(v)
        return n is not None and int(n) == n and int(n) in allowed

    return check


def strict_binary(v: Any) -> bool:
    """1/0 only — no 3, no '.'. Used for the substance flags."""
    n = as_number(v)
    return n is not None and int(n) == n and int(n) in (0, 1)


def one_of(*values: str, allow_missing: bool = True) -> Callable[[Any], bool]:
    allowed = set(values)

    def check(v: Any) -> bool:
        if allow_missing and is_missing(v):
            return True
        return isinstance(v, str) and v in allowed

    return check


def percent(v: Any) -> bool:
    if is_missing(v):
        return True
    n = as_number(v)
    return n is not None and 0 <= n <= 100


def nonneg_number(v: Any) -> bool:
    if is_missing(v):
        return True
    n = as_number(v)
    return n is not None and n >= 0


def positive_integer_or(*sentinels: str) -> Callable[[Any], bool]:
    allowed = set(sentinels)

    def check(v: Any) -> bool:
        if isinstance(v, str) and v in allowed:
            return True
        n = as_number(v)
        return n is not None and float(n).is_integer() and n >= 0

    return check


def free_text(v: Any) -> bool:
    """Any string (including '.') or a number. Rejects None and containers."""
    return isinstance(v, (str, int, float)) and not isinstance(v, bool)


def year(v: Any) -> bool:
    n = as_number(v)
    return n is not None and float(n).is_integer() and 1900 <= n <= 2100


# ── Derived: baseline-severity reporting (codebook §4.5) ─────────────────

# Studies whose analysed sample did not have the target condition at baseline,
# so there was no baseline status to report. Keyed by StudyID.
BASE_STATUS_NOT_REPORTED: frozenset[str] = frozenset({'Nicholas 2022'})


def base_status_reported(study_id: Any, sample_size: Any) -> str:
    """`BaseStatusReportedYN` for one row.

    Naming the target condition as a baseline diagnosis counts as reporting
    baseline status whether or not a severity band is graded, so this is '1'
    wherever a study has an analysed sample — deliberately independent of
    whether `BaseStatus` carries a band. Two exceptions: a study with no
    analysed sample (review, protocol, wrong source document) has nothing to
    characterise and takes '.', not '0'; a sample that did not have the
    condition at baseline takes '0'.
    """
    if is_missing(sample_size) or not is_number(sample_size):
        return '.'
    return '0' if study_id in BASE_STATUS_NOT_REPORTED else '1'


# ── Field validators (codebook §4) ───────────────────────────────────────

ARTICLE_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    # Identity and condition
    'StudyID':        is_nonempty_text,
    'Citation/Title': is_nonempty_text,
    'Condition':      one_of(*CONDITIONS, allow_missing=False),
    'Year':           year,

    # Tier-1 effect-size fields. Deliberately permissive on type — `Outcome`
    # may be a number, a labelled descriptor ("OR = 2.1", "63% vs 27%") or
    # "."; correctness is enforced by the mandatory rationale entry and the
    # old/new Tier-1 comparison, not by a type check that would reject
    # legitimate text.
    'Outcome':           free_text,
    'SD':                free_text,
    'PVal':              free_text,
    'SampleSize_NFinal': positive_integer_or(NOT_REPORTED),

    # Design and methodological quality
    'Pos Result Y/N':             binary_code(),
    'Clincial Trial YN':          binary_code(),
    'RandomizationYN':            binary_code(),
    'BlindingYN':                 binary_code(),
    'Double+Blind':               binary_code(),
    'Comparator':                 binary_code(),
    'PrimaryCare':                binary_code(),
    'Power':                      binary_code(),
    'Retention (%)':              percent,
    'ConfoundYN':                 binary_code(),
    'InclusionExclusionCriteria': binary_code(),
    'ValidatedScaleMeasYN':       binary_code(),
    'MethodologyDescribedYN':     binary_code(),
    'Funding/COI YN':             binary_code(),

    # Population and generalizability
    'BaseStatus':                 one_of(*BASE_STATUS),
    'Age_Median':                 one_of(*AGE_BRACKETS),
    'PercentFem':                 percent,
    'RaceEthnicity_BIPOCPercent': percent,
    'SocioeconomicStatusYN':      binary_code(),
    'Country_USvsNonUS':          one_of(*COUNTRIES),
    'RecruitmentRepresentYN':     binary_code(),

    # Intervention and harms
    'InterventionDescription': free_text,
    'InterventionTherapy':     binary_code(),
    'HarmsAssessed':           binary_code(),

    # Equity and cultural framing
    'CulturalFraming':     binary_code(),
    'IndigenousFramework': binary_code(),
    'Reciprocity':         binary_code(),

    # Outcomes and follow-up
    'Followup in months': nonneg_number,

    # Eligibility (added)
    'EligibleYN':                 one_of('Y', 'N', allow_missing=False),
    'EligibilityFailedCriterion': one_of(*ELIGIBILITY_FAILURES, allow_missing=False),
    'EligibilityNote':            free_text,

    # Baseline-severity reporting (added, derived — see derive_base_status_reported)
    'BaseStatusReportedYN':       binary_code(),

    # AE gate (added)
    'SafetyReported':      one_of('Y', 'N', allow_missing=False),
    'AnyAEReported':       one_of('Y', 'N', 'NA', allow_missing=False),
    'NumDistinctAEs':      positive_integer_or('Not numbered', 'NA'),
    'NParticipantsWithAE': positive_integer_or(NOT_REPORTED, 'NA'),
    'AE_denominator':      positive_integer_or('Not numbered', NOT_REPORTED),
    'ArmScope':            one_of(*ARM_SCOPES, allow_missing=False),
    'WorstSeverity':       one_of(*WORST_SEVERITIES, allow_missing=False),

    # Provenance (added)
    'text_source':    one_of(*TEXT_SOURCES, allow_missing=False),
    'text_format':    one_of(*TEXT_FORMATS, allow_missing=False),
    'Model':          is_nonempty_text,
    'PromptVersion':  is_nonempty_text,
    'RubricVersion':  is_nonempty_text,
    'Temperature':    is_number,
    'SourcePDF':      is_nonempty_text,
}

# The nine outcome binaries and the ten substance flags, added programmatically
# so their differing rules stay visible as rules rather than as repetition.
for _col in OUTCOME_BINARY_COLS:
    ARTICLE_VALIDATORS[_col] = binary_code()
for _col in SUBSTANCE_BINARY_COLS:
    ARTICLE_VALIDATORS[_col] = strict_binary

AE_EVENT_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    'AE_ID':                 is_nonempty_text,
    'StudyID':               is_nonempty_text,
    'AE_type':               one_of(*AE_TYPES, allow_missing=False),
    'Description':           is_nonempty_text,
    'NAffected':             positive_integer_or(NOT_REPORTED),
    'Onset':                 one_of(*ONSETS, allow_missing=False),
    'Severity':              one_of(*SEVERITIES, allow_missing=False),
    'SeverityIndeterminate': one_of('Y', 'N', allow_missing=False),
    'SeveritySource':        one_of(*SEVERITY_SOURCES, allow_missing=False),
    'InterventionRequired':  one_of('Y', 'N'),
    'MeetsFDASerious':       one_of('Y', 'N', allow_missing=False),
}

assert len(CARRIED_FIELDS) == 54, f'expected 54 carried fields, got {len(CARRIED_FIELDS)}'
assert len(ADDED_FIELDS) == 19, f'expected 19 added fields, got {len(ADDED_FIELDS)}'
assert len(ARTICLE_FIELDS) == 73, f'expected 73 master columns, got {len(ARTICLE_FIELDS)}'
assert set(ARTICLE_VALIDATORS) == set(ARTICLE_FIELDS), (
    'validator set and column set disagree: '
    f'{set(ARTICLE_FIELDS) ^ set(ARTICLE_VALIDATORS)}'
)
