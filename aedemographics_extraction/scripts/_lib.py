"""Shared schema, enums, and type/gate-check helpers for the AE/demographics
extraction pipeline (aedemographics_extraction/). Standalone from the
USPSTF alcohol/smoking/opioid pipeline in scripts/ — no imports either way.

Field definitions mirror observational_codebook.md sections 3-4.
"""

from __future__ import annotations

from typing import Any

# ── Output column order ────────────────────────────────────────────────────

ARTICLE_FIELDS: list[str] = [
    'StudyID', 'Citation', 'Title', 'Year', 'Corpus/Prefix', 'Condition',
    'Substance', 'IsObservational', 'N', 'AE_denominator', 'ArmScope',
    'PctFemale', 'GenderCategory', 'PctBIPOC', 'PctIndigenous',
    'SafetyReported', 'AnyAEReported', 'NumDistinctAEs', 'NParticipantsWithAE',
    'WorstSeverity', 'text_source', 'Model', 'PromptVersion', 'RubricVersion',
    'Temperature',
]

AE_EVENT_FIELDS: list[str] = [
    'AE_ID', 'StudyID', 'AE_type', 'Description', 'Onset', 'Severity',
    'SeverityIndeterminate', 'SeveritySource', 'InterventionRequired',
    'MeetsFDASerious',
]

# Provenance fields that must be non-empty for every article (design doc §8).
PROVENANCE_FIELDS: list[str] = [
    'Model', 'PromptVersion', 'RubricVersion', 'Temperature', 'text_source',
]

# ── Enums (observational_codebook.md §3-4) ─────────────────────────────────

IS_OBSERVATIONAL        = {'Y', 'N'}
CONDITION                = {'Alcohol', 'Smoking', 'Opioid'}
ARM_SCOPE               = {'psychedelic_arm', 'pooled', 'NA'}
SAFETY_REPORTED         = {'Y', 'N'}
ANY_AE_REPORTED         = {'Y', 'N', 'NA'}
WORST_SEVERITY          = {'Mild', 'Moderate', 'Severe', 'None', 'NA'}
TEXT_SOURCE             = {'born-digital', 'OCR', 'manual'}
AE_TYPE                 = {'AE', 'challenging_experience', 'both'}
ONSET                   = {'in-session', 'post-session-acute', 'delayed', 'unknown'}
SEVERITY                = {'Mild', 'Moderate', 'Severe'}
SEVERITY_INDETERMINATE  = {'Y', 'N'}
SEVERITY_SOURCE         = {'author', 'rubric'}
INTERVENTION_REQUIRED   = {'Y', 'N', '.'}
MEETS_FDA_SERIOUS       = {'Y', 'N'}

SEVERITY_RANK: dict[str, int] = {'Mild': 1, 'Moderate': 2, 'Severe': 3}


# ── Low-level value checkers ────────────────────────────────────────────────

def _is_bool(v: Any) -> bool:
    """True bools slip past int checks in Python; reject them explicitly."""
    return isinstance(v, bool)


def is_enum(v: Any, allowed: set) -> bool:
    return isinstance(v, str) and v in allowed


def is_nonneg_int(v: Any) -> bool:
    if _is_bool(v):
        return False
    if isinstance(v, int):
        return v >= 0
    if isinstance(v, str) and v.strip().lstrip('-').isdigit():
        return int(v) >= 0
    return False


def is_int_or(v: Any, *string_values: str) -> bool:
    """Non-negative integer, or one of the given literal string values."""
    if isinstance(v, str) and v in string_values:
        return True
    return is_nonneg_int(v)


def is_percent_or_dot(v: Any) -> bool:
    """Number 0-100, or the literal string '.'"""
    if v == '.':
        return True
    if _is_bool(v):
        return False
    if isinstance(v, (int, float)):
        return 0 <= v <= 100
    return False


def is_four_digit_year(v: Any) -> bool:
    if _is_bool(v):
        return False
    if isinstance(v, int):
        return 1000 <= v <= 9999
    if isinstance(v, str) and v.isdigit():
        return 1000 <= int(v) <= 9999
    return False


def is_number(v: Any) -> bool:
    return not _is_bool(v) and isinstance(v, (int, float))


def is_nonempty_text(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ''


def as_number(v: Any) -> float | None:
    """Best-effort numeric coercion for gate comparisons; None if not numeric."""
    if _is_bool(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


# ── Per-field type/enum validators ──────────────────────────────────────────
# Each returns True if `v` is a valid value for that field. Used by
# merge_validate.py's type/enum check (design doc §8, codebook §7).

ARTICLE_VALIDATORS: dict[str, Any] = {
    'StudyID':             is_nonempty_text,
    'Citation':             is_nonempty_text,
    'Title':                is_nonempty_text,
    'Year':                 is_four_digit_year,
    'Corpus/Prefix':        lambda v: isinstance(v, str),
    'Condition':            lambda v: v == '.' or is_enum(v, CONDITION),
    'Substance':            lambda v: isinstance(v, str),
    'IsObservational':      lambda v: is_enum(v, IS_OBSERVATIONAL),
    'N':                    lambda v: v == '.' or is_nonneg_int(v),
    'AE_denominator':       lambda v: is_int_or(v, 'Not numbered', '.'),
    'ArmScope':             lambda v: is_enum(v, ARM_SCOPE),
    'PctFemale':            is_percent_or_dot,
    'GenderCategory':       lambda v: isinstance(v, str),
    'PctBIPOC':             is_percent_or_dot,
    'PctIndigenous':        is_percent_or_dot,
    'SafetyReported':       lambda v: is_enum(v, SAFETY_REPORTED),
    'AnyAEReported':        lambda v: is_enum(v, ANY_AE_REPORTED),
    'NumDistinctAEs':       lambda v: is_int_or(v, 'Not numbered', 'NA'),
    'NParticipantsWithAE':  lambda v: is_int_or(v, '.', 'NA'),
    'WorstSeverity':        lambda v: is_enum(v, WORST_SEVERITY),
    'text_source':          lambda v: is_enum(v, TEXT_SOURCE),
    'Model':                is_nonempty_text,
    'PromptVersion':        is_nonempty_text,
    'RubricVersion':        is_nonempty_text,
    'Temperature':          is_number,
}

AE_EVENT_VALIDATORS: dict[str, Any] = {
    'AE_ID':                 is_nonempty_text,
    'StudyID':                is_nonempty_text,
    'AE_type':                lambda v: is_enum(v, AE_TYPE),
    'Description':            lambda v: isinstance(v, str),
    'Onset':                  lambda v: is_enum(v, ONSET),
    'Severity':               lambda v: is_enum(v, SEVERITY),
    'SeverityIndeterminate':  lambda v: is_enum(v, SEVERITY_INDETERMINATE),
    'SeveritySource':         lambda v: is_enum(v, SEVERITY_SOURCE),
    'InterventionRequired':   lambda v: is_enum(v, INTERVENTION_REQUIRED),
    'MeetsFDASerious':        lambda v: is_enum(v, MEETS_FDA_SERIOUS),
}
