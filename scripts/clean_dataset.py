"""Clean a psychedelic-trial extraction dataset for a given condition.

Usage:
    python scripts/clean_dataset.py --condition alcohol
    python scripts/clean_dataset.py --condition smoking
    python scripts/clean_dataset.py --condition opioid   # raises NotImplementedError

Replaces clean_alcohol_dataset.py with a condition-agnostic pipeline.
Output: data/<Condition>_Dataset_Cleaned.xlsx
"""

import argparse
import importlib
import sys
from pathlib import Path

import pandas as pd

_BASE    = Path(__file__).parent.parent
_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import _lib as lib

VALID_CONDITIONS = ('alcohol', 'smoking', 'opioid')


def load_config(condition: str):
    """Import and validate the per-condition config module."""
    cfg = importlib.import_module(f'_config_{condition}')
    if not cfg.EFFECT_SIZE_EXTRACTIONS:
        raise NotImplementedError(
            f"{condition.capitalize()} extractions not yet hand-coded — populate "
            f"EFFECT_SIZE_EXTRACTIONS and CONVERSION_RULES in _config_{condition}.py."
        )
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Clean a psychedelic-trial extraction dataset.')
    parser.add_argument(
        '--condition', required=True, choices=VALID_CONDITIONS,
        help='Which condition dataset to clean.')
    args = parser.parse_args()

    condition = args.condition
    cfg       = load_config(condition)

    input_path  = _BASE / cfg.INPUT_FILE
    output_path = _BASE / 'data' / f'{condition.capitalize()}_Dataset_Cleaned.xlsx'

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    df_raw   = pd.read_excel(input_path)
    df_clean = lib.clean(df_raw, cfg)

    print(f"Rows: {len(df_clean)} | Columns: {len(df_clean.columns)}")

    if 'Country_USvsNonUS' in df_clean.columns:
        print("\nCountry_USvsNonUS after collapse:")
        print(df_clean['Country_USvsNonUS'].value_counts(dropna=False).to_string())

    if 'Age_Median' in df_clean.columns:
        print("\nAge_Median after fix:")
        print(df_clean['Age_Median'].value_counts(dropna=False).to_string())

    if 'BaseStatus' in df_clean.columns:
        print("\nBaseStatus after fix:")
        print(df_clean['BaseStatus'].value_counts(dropna=False).to_string())

    print("\nMetric distribution:")
    print(df_clean['metric'].value_counts(dropna=False).to_string())

    df_clean.to_excel(output_path, index=False)
    print(f"\nWritten to: {output_path}")


if __name__ == '__main__':
    main()
