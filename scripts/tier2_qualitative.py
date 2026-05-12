"""
Tier 2 qualitative classification for studies where Tier 1 conversion fails.

Usage:
    python scripts/tier2_qualitative.py --condition alcohol
    python scripts/tier2_qualitative.py --condition smoking

Inputs:
    data/<Condition>_Dataset_Cleaned.xlsx   (output of clean_dataset.py)
    tables/<Condition>_Tier1_HedgesG.xlsx   (output of tier1_hedges_g.py)

Outputs:
    tables/<Condition>_Tier2_Qualitative.xlsx  per-study classification table
    figures/<Condition>_Tier2_CatPlot.png      categorical strip plot

Categories (ordered left to right on the plot):
    negative             Favors comparator
    null                 Non-significant or NS-only report
    small_positive       OR < 1.5 or g < 0.5
    moderate_positive    OR 1.5–3 or g 0.5–0.8
    large_positive       OR ≥ 3 or g ≥ 0.8
    single_arm_positive  Positive direction; no comparator group (Option B)
    unclassifiable       Insufficient data to classify
"""

import argparse
import importlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_BASE    = Path(__file__).parent.parent
_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import _lib as lib

plt.rcParams.update({
    'font.family':       'sans-serif',
    'font.size':         11,
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'axes.linewidth':    0.8,
    'figure.dpi':        150,
})

VALID_CONDITIONS = ('alcohol', 'smoking', 'opioid')

CATEGORY_ORDER = [
    'negative',
    'null',
    'small_positive',
    'moderate_positive',
    'large_positive',
    'single_arm_positive',
    'unclassifiable',
]

CATEGORY_LABELS = {
    'negative':            'Negative',
    'null':                'Null / NS',
    'small_positive':      'Small Positive (OR<1.5 or g<0.5)',
    'moderate_positive':   'Moderate Positive (OR 1.5-3 or g 0.5-0.8)',
    'large_positive':      'Large Positive (OR>=3 or g>=0.8)',
    'single_arm_positive': 'Positive (Single-arm, no comparator)',
    'unclassifiable':      'Unclassifiable',
}

# Shorter labels used only for plot column headers (thresholds in subtitle).
_PLOT_HEADERS = {
    'negative':            'Negative',
    'null':                'Null / NS',
    'small_positive':      'Small\nPositive',
    'moderate_positive':   'Moderate\nPositive',
    'large_positive':      'Large\nPositive',
    'single_arm_positive': 'Positive\n(Single-arm)',
    'unclassifiable':      'Unclas-\nsifiable',
}

# Subtle background shading per category column (hex, no #)
CATEGORY_SHADING = {
    'negative':            '#fce8e8',
    'null':                '#f5f5f5',
    'small_positive':      '#eaf4ea',
    'moderate_positive':   '#d4edda',
    'large_positive':      '#b8dfc8',
    'single_arm_positive': '#e8f0fc',
    'unclassifiable':      '#f9f9f9',
}


def load_config(condition: str):
    cfg = importlib.import_module(f'_config_{condition}')
    if not hasattr(cfg, 'TIER2_RATINGS'):
        raise AttributeError(
            f"_config_{condition}.py has no TIER2_RATINGS dict — "
            "add it before running Tier 2."
        )
    return cfg


def build_tier2_results(
    df: pd.DataFrame,
    tier1: pd.DataFrame,
    cfg,
) -> pd.DataFrame:
    """Merge Tier-1-excluded studies with TIER2_RATINGS from config."""
    excluded = tier1[tier1['confidence'] == 'excluded'].copy()

    rows = []
    missing = []
    for _, r in excluded.iterrows():
        key = (lib.first_author_surname(str(r['study']).rsplit(' ', 1)[0]), int(r['Year']))
        # Tier 1 stores study as "Surname YEAR" — split off the year to rebuild the key.
        # More robust: reconstruct from the study string directly.
        parts = str(r['study']).rsplit(' ', 1)
        try:
            key = (parts[0], int(parts[1]))
        except (IndexError, ValueError):
            key = (r['study'], int(r['Year']))

        rating = cfg.TIER2_RATINGS.get(key)
        if rating is None:
            missing.append(key)
            rating = {
                'category': 'unclassifiable',
                'basis':    'No TIER2_RATINGS entry defined for this study.',
            }

        rows.append({
            'study':           r['study'],
            'Year':            int(r['Year']),
            'N':               r['N'],
            'substance':       r['substance'],
            'tier1_metric':    r.get('metric', ''),
            'tier1_measure':   r.get('measure', ''),
            'tier1_note':      r.get('note', ''),
            'tier2_category':  rating['category'],
            'category_label':  CATEGORY_LABELS[rating['category']].replace('\n', ' '),
            'basis':           rating.get('basis', ''),
            'computed_or':     rating.get('computed_or', None),
        })

    if missing:
        print(
            f"  WARNING: {len(missing)} excluded study/studies have no TIER2_RATINGS entry "
            f"and will be marked 'unclassifiable': {missing}",
            file=sys.stderr,
        )

    result = pd.DataFrame(rows)
    result['tier2_category'] = pd.Categorical(
        result['tier2_category'], categories=CATEGORY_ORDER, ordered=True
    )
    return result.sort_values(['tier2_category', 'Year']).reset_index(drop=True)


def _build_plot_layout(results: pd.DataFrame) -> list[dict]:
    """Sort by substance then year; insert substance-group headers."""
    df = results[results['tier2_category'] != 'unclassifiable'].copy()

    order = lib.SUBSTANCE_ORDER
    known  = [s for s in order if s in df['substance'].values]
    others = sorted(set(df['substance'].unique()) - set(order))
    full_order = known + others

    df['substance'] = pd.Categorical(df['substance'], categories=full_order, ordered=True)
    df = df.sort_values(['substance', 'Year']).reset_index(drop=True)

    # Append unclassifiable rows at the bottom (no substance header)
    uncls = results[results['tier2_category'] == 'unclassifiable'].copy()

    layout: list[dict] = []
    last_sub = None
    for _, r in df.iterrows():
        if r['substance'] != last_sub:
            layout.append({'kind': 'header', 'text': str(r['substance'])})
            last_sub = r['substance']
        layout.append({'kind': 'study', 'data': r.to_dict()})

    if not uncls.empty:
        layout.append({'kind': 'header', 'text': 'Unclassifiable'})
        for _, r in uncls.iterrows():
            layout.append({'kind': 'study', 'data': r.to_dict()})

    return layout


def make_cat_plot(results: pd.DataFrame, out_path: Path, condition: str) -> None:
    layout = _build_plot_layout(results)
    if not layout:
        print(f"  No Tier 2 studies for {condition}; plot skipped.")
        return

    present     = set(results['tier2_category'].astype(str))
    active_cats = [c for c in CATEGORY_ORDER if c in present]

    n_rows  = len(layout)
    n_cats  = len(active_cats)
    cat_x   = {cat: i for i, cat in enumerate(active_cats)}

    fig_h = max(5.0, 0.42 * n_rows + 2.5)
    fig   = plt.figure(figsize=(12.0, fig_h))
    gs    = fig.add_gridspec(1, 2, width_ratios=[1.4, 5.5], wspace=0.02)

    ax_lbl = fig.add_subplot(gs[0])
    ax_cat = fig.add_subplot(gs[1], sharey=ax_lbl)

    for ax in (ax_lbl, ax_cat):
        ax.set_yticks([])
        ax.set_xticks([])
        ax.patch.set_visible(False)   # exclude blank axis background from tight bbox
        for sp in ax.spines.values():
            sp.set_visible(False)

    y_top = n_rows
    ax_lbl.set_xlim(0, 1)
    ax_cat.set_xlim(-0.6, n_cats - 0.4)
    ax_lbl.set_ylim(0.5, y_top + 1.5)

    # Category column backgrounds
    for cat in active_cats:
        x     = cat_x[cat]
        color = CATEGORY_SHADING[cat]
        ax_cat.axvspan(x - 0.45, x + 0.45, color=color, alpha=0.55, zorder=0)

    # Vertical separators
    for x in range(n_cats - 1):
        ax_cat.axvline(x + 0.5, color='#cccccc', lw=0.5, zorder=1)

    # Column header labels (top)
    for cat in active_cats:
        x = cat_x[cat]
        lbl = _PLOT_HEADERS[cat]
        ax_cat.text(x, y_top + 1.1, lbl, va='bottom', ha='center',
                    fontsize=8.5, color='#333333', linespacing=1.3,
                    fontweight='bold')

    ax_lbl.text(0.97, y_top + 1.1, 'Study', fontweight='bold',
                va='bottom', ha='right', fontsize=10)

    # Study rows
    for i, item in enumerate(layout):
        y = y_top - i
        if item['kind'] == 'header':
            ax_lbl.text(0.97, y, item['text'], fontweight='bold',
                        va='center', ha='right', fontsize=11)
            ax_cat.hlines(y - 0.5, -0.6, n_cats - 0.4,
                          color='lightgray', lw=0.5, zorder=1)
            continue

        r     = item['data']
        color = lib.SUBSTANCE_COLORS.get(r['substance'], '#444444')
        x_pos = cat_x.get(str(r['tier2_category']), n_cats - 1)

        ax_cat.scatter(x_pos, y, s=110, color=color,
                       edgecolors='white', linewidths=0.8, zorder=3)

        n_label = f" (N={r['N']})" if r['N'] and not (isinstance(r['N'], float) and np.isnan(r['N'])) else ''
        ax_lbl.text(0.97, y, f"{r['study']}{n_label}",
                    va='center', ha='right', fontsize=9.0)

        # Annotate OR where available
        if r.get('computed_or') and not (isinstance(r['computed_or'], float) and np.isnan(r['computed_or'])):
            ax_cat.text(x_pos, y - 0.28, f"OR={r['computed_or']:.2f}",
                        va='top', ha='center', fontsize=7.0, color='#555555')

    # Legend for substances
    seen = {item['data']['substance'] for item in layout if item['kind'] == 'study'}
    handles = [
        mpatches.Patch(color=lib.SUBSTANCE_COLORS.get(s, '#444444'), label=s)
        for s in lib.SUBSTANCE_ORDER if s in seen
    ]
    others = [s for s in seen if s not in lib.SUBSTANCE_ORDER]
    for s in sorted(others):
        handles.append(mpatches.Patch(color='#444444', label=s))

    fig.legend(handles=handles, loc='lower center',
               bbox_to_anchor=(0.5, 0.0), ncol=min(len(handles), 5),
               fontsize=9, framealpha=0.9, edgecolor='#bdbdbd')

    cond_label = condition.capitalize()
    fig.suptitle(
        f"Tier 2 Qualitative Classification — Psychedelics for {cond_label} Use Disorder",
        fontsize=12, y=0.99,
    )
    fig.text(
        0.5, 0.963,
        "Thresholds: small = OR<1.5 or g<0.5;  moderate = OR 1.5–3 or g 0.5–0.8;  large = OR≥3 or g≥0.8",
        ha='center', va='top', fontsize=8.5, color='#555555', style='italic',
    )

    fig.subplots_adjust(top=0.90, bottom=0.12, left=0.02, right=0.98)
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Tier 2 qualitative classification for Tier-1-excluded studies.')
    parser.add_argument(
        '--condition', required=True, choices=VALID_CONDITIONS,
        help='Which condition to process.')
    args = parser.parse_args()

    condition = args.condition
    cfg       = load_config(condition)
    cond_cap  = condition.capitalize()

    input_path  = _BASE / 'data'    / f'{cond_cap}_Dataset_Cleaned.xlsx'
    tier1_path  = _BASE / 'tables'  / f'{cond_cap}_Tier1_HedgesG.xlsx'
    out_table   = _BASE / 'tables'  / f'{cond_cap}_Tier2_Qualitative.xlsx'
    out_plot    = _BASE / 'figures' / f'{cond_cap}_Tier2_CatPlot.png'

    for p in (input_path, tier1_path):
        if not p.exists():
            print(f"ERROR: Required file not found: {p}", file=sys.stderr)
            sys.exit(1)

    df    = pd.read_excel(input_path)
    tier1 = pd.read_excel(tier1_path)

    results = build_tier2_results(df, tier1, cfg)

    print(f"Tier 2 studies classified: {len(results)}")
    counts = results['tier2_category'].value_counts().reindex(CATEGORY_ORDER, fill_value=0)
    for cat, n in counts.items():
        if n:
            print(f"  {cat:<22} {n}")
    print()

    show_cols = ['study', 'substance', 'tier2_category', 'computed_or', 'basis']
    out_str = results[show_cols].to_string(index=False)
    print(out_str.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8'))

    results.to_excel(out_table, index=False)
    print(f"\nResults table written to: {out_table}")

    make_cat_plot(results, out_plot, condition)
    print(f"Category plot written to:  {out_plot}")


if __name__ == '__main__':
    main()
