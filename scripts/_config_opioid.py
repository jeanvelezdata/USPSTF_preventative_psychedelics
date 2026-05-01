"""Per-condition configuration for opioid psychedelic trials — stub.

TODO: Populate EFFECT_SIZE_EXTRACTIONS and CONVERSION_RULES once
      data/Opioid_Dataset.xlsx has been hand-coded by the author.
"""

CONDITION_NAME = 'opioid'
INPUT_FILE = 'data/Opioid_Dataset.xlsx'

# TODO: Add one entry per study after Opioid_Dataset.xlsx is available.
# Format: (first_author_surname, year): (metric, measure, note)
EFFECT_SIZE_EXTRACTIONS: dict = {}

# TODO: Add one entry per study after Opioid_Dataset.xlsx is available.
# Format: (first_author_surname, year): {'method': ..., 'confidence': ..., 'note': ...}
CONVERSION_RULES: dict = {}


def _require_populated() -> None:
    """Raise NotImplementedError if the config has not been filled in."""
    if not EFFECT_SIZE_EXTRACTIONS:
        raise NotImplementedError(
            "Opioid extractions not yet hand-coded — populate "
            "EFFECT_SIZE_EXTRACTIONS and CONVERSION_RULES in _config_opioid.py."
        )
