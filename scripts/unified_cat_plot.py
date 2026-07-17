"""
Unified Tier 2 categorical plot: all conditions and substances in a single figure.

Usage:
    python scripts/unified_cat_plot.py

Output:
    figures/Unified_Tier2_CatPlot.png
"""

import importlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot  as plt
import numpy as np
import pandas as pd

_BASE    = Path(__file__).parent.parent
_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import _lib as lib

# ── Categories ────────────────────────────────────────────────────────────────

CONDITIONS = [
    ('alcohol', 'Alcohol Use Disorder'),
    ('opioid',  'Opioid Use Disorder'),
    ('smoking', 'Tobacco Use Disorder'),
]

CATEGORY_ORDER = [
    'negative', 'null', 'small_positive', 'moderate_positive',
    'large_positive', 'single_arm_positive', 'unclassifiable',
]

CATEGORY_DISPLAY = {
    'negative':            'Negative',
    'null':                'Null / NS',
    'small_positive':      'Small\nPositive',
    'moderate_positive':   'Moderate\nPositive',
    'large_positive':      'Large\nPositive',
    'single_arm_positive': 'Positive\n(no comparator)',
    'unclassifiable':      'Unclas-\nsifiable',
}

CATEGORY_SHADING = {
    'negative':            '#fce8e8',
    'null':                '#f5f5f5',
    'small_positive':      '#eaf4ea',
    'moderate_positive':   '#d4edda',
    'large_positive':      '#b8dfc8',
    'single_arm_positive': '#e8f0fc',
    'unclassifiable':      '#f0f0f0',
}

# Extended colour map (identical to unified_forest_plot.py)
SUBSTANCE_ORDER_UNIFIED = [
    'Psilocybin', 'LSD', 'Mescaline', 'Ayahuasca', 'Ibogaine', 'OtherPsychedelic',
    'MDMA', 'Ketamine', 'Cannabis',
]

SUBSTANCE_DISPLAY = {
    'Psilocybin':        'Psilocybin',
    'LSD':               'LSD',
    'Mescaline':         'Mescaline',
    'Ayahuasca':         'Ayahuasca',
    'Ibogaine':          'Ibogaine',
    'OtherPsychedelic':  'Other classical',
    'MDMA':              'MDMA',
    'Ketamine':          'Ketamine',
    'Cannabis':          'Cannabis',
}

SUBSTANCE_COLORS = {
    **lib.SUBSTANCE_COLORS,
    'Ibogaine':          '#9467bd',
    'Ayahuasca':         '#8c564b',
    'Mescaline':         '#e377c2',
    'OtherPsychedelic':  '#7f7f7f',
    'Cannabis':          '#17becf',
}

# ── Visual constants (matches unified_forest_plot.py) ─────────────────────────

_COND_BG   = '#EDF1FA'
_COND_FG   = '#162040'
_SUB_FG    = '#2c2c2c'
_SEP_COLOR = '#cccccc'

plt.rcParams.update({
    'font.family':        'sans-serif',
    'font.size':          9,
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.linewidth':     0.8,
    'figure.dpi':         150,
})

# ── Data loading ───────────────────────────────────────────────────────────────

def _load_tier2(condition: str):
    cap        = condition.capitalize()
    tier1_path = _BASE / 'tables' / f'{cap}_Tier1_HedgesG.xlsx'
    if not tier1_path.exists():
        print(f"  Skipping {condition}: Tier-1 table not found.")
        return None
    cfg = importlib.import_module(f'_config_{condition}')
    if not hasattr(cfg, 'TIER2_RATINGS'):
        return None

    tier1    = pd.read_excel(tier1_path)
    excluded = tier1[tier1['confidence'] == 'excluded'].copy()

    rows = []
    for _, r in excluded.iterrows():
        parts = str(r['study']).rsplit(' ', 1)
        try:
            key = (parts[0], int(parts[1]))
        except (IndexError, ValueError):
            key = (r['study'], int(r['Year']))

        rating = cfg.TIER2_RATINGS.get(key, {
            'category': 'unclassifiable',
            'basis':    'No TIER2_RATINGS entry defined.',
        })
        rows.append({
            'study':       r['study'],
            'Year':        int(r['Year']),
            'N':           r['N'],
            'substance':   r['substance'],
            'category':    rating['category'],
            'basis':       rating.get('basis', ''),
            'computed_or': rating.get('computed_or', None),
        })
    return pd.DataFrame(rows) if rows else None


# ── Layout construction ────────────────────────────────────────────────────────

def _sort_studies(df: pd.DataFrame) -> pd.DataFrame:
    known  = [s for s in SUBSTANCE_ORDER_UNIFIED if s in df['substance'].values]
    others = sorted(set(df['substance'].unique()) - set(SUBSTANCE_ORDER_UNIFIED))
    df = df.copy()
    df['substance'] = pd.Categorical(
        df['substance'], categories=known + others, ordered=True
    )
    return df.sort_values(['substance', 'Year']).reset_index(drop=True)


def build_layout(all_tier2: dict) -> tuple:
    layout: list[dict] = []
    all_cats: set      = set()

    for condition, label in CONDITIONS:
        if condition not in all_tier2:
            continue
        df = all_tier2[condition]
        if df is None or df.empty:
            continue

        all_cats.update(df['category'].unique())
        layout.append({'kind': 'condition_header', 'text': label})

        df = _sort_studies(df)
        last_sub = None
        for _, r in df.iterrows():
            sub = str(r['substance'])
            if sub != last_sub:
                layout.append({'kind': 'substance_header', 'text': sub})
                last_sub = sub
            layout.append({'kind': 'study', 'data': r.to_dict()})

        layout.append({'kind': 'spacer'})

    if layout and layout[-1]['kind'] == 'spacer':
        layout.pop()

    active_cats = [c for c in CATEGORY_ORDER if c in all_cats]
    return layout, active_cats


# ── Main plot ──────────────────────────────────────────────────────────────────

def make_unified_cat_plot(out_path: Path) -> None:

    all_tier2 = {}
    for condition, _ in CONDITIONS:
        df = _load_tier2(condition)
        if df is not None and not df.empty:
            all_tier2[condition] = df

    layout, active_cats = build_layout(all_tier2)
    if not any(item['kind'] == 'study' for item in layout):
        print("No Tier 2 studies found; plot skipped.")
        return

    n_rows = len(layout)
    n_cats = len(active_cats)
    cat_x  = {cat: i for i, cat in enumerate(active_cats)}

    y_top  = n_rows + 1

    row_h  = 0.32
    fig_h  = max(7.0, row_h * n_rows + 3.6)
    fig_w  = 14.0

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor='white')
    gs  = fig.add_gridspec(1, 2, width_ratios=[2.5, 5.0], wspace=0.02)
    ax_lbl = fig.add_subplot(gs[0])
    ax_cat = fig.add_subplot(gs[1], sharey=ax_lbl)

    for ax in (ax_lbl, ax_cat):
        ax.set_yticks([])
        ax.set_xticks([])
        ax.patch.set_visible(False)
        for sp in ax.spines.values():
            sp.set_visible(False)

    ax_lbl.set_xlim(0, 1)
    ax_cat.set_xlim(-0.55, n_cats - 0.45)
    ax_lbl.set_ylim(0.2, y_top + 1.2)

    # ── Category column backgrounds and vertical separators ────────────────────
    for cat in active_cats:
        x = cat_x[cat]
        ax_cat.axvspan(x - 0.45, x + 0.45,
                       color=CATEGORY_SHADING[cat], alpha=0.65, zorder=0)
    for x in range(n_cats - 1):
        ax_cat.axvline(x + 0.5, color='#c8c8c8', lw=0.6, zorder=1)

    # ── Column headers ─────────────────────────────────────────────────────────
    hdr_y = y_top + 0.4
    ax_lbl.text(0.04, hdr_y, 'Study', fontweight='bold',
                va='center', ha='left', fontsize=10)
    ax_lbl.text(0.96, hdr_y, 'N', fontweight='bold',
                va='center', ha='right', fontsize=10)

    for cat in active_cats:
        x = cat_x[cat]
        ax_cat.text(x, hdr_y, CATEGORY_DISPLAY[cat],
                    va='center', ha='center', fontsize=8.5,
                    fontweight='bold', color='#2a2a2a',
                    linespacing=1.3, multialignment='center')

    # Horizontal rule below column headers
    rule_y = y_top - 0.35
    for ax in (ax_lbl, ax_cat):
        ax.axhline(rule_y, color='#666', lw=0.9, zorder=4)

    # ── Draw rows ──────────────────────────────────────────────────────────────
    for i, item in enumerate(layout):
        y = y_top - 1 - i

        if item['kind'] == 'condition_header':
            for ax in (ax_lbl, ax_cat):
                ax.axhspan(y - 0.48, y + 0.52, color=_COND_BG, zorder=0, lw=0)
            ax_lbl.plot([0.005, 0.005], [y - 0.48, y + 0.52],
                        color=_COND_FG, lw=3.5, zorder=5,
                        solid_capstyle='butt', clip_on=False)
            ax_lbl.text(0.04, y, item['text'],
                        fontweight='bold', fontsize=11,
                        va='center', ha='left', color=_COND_FG)

        elif item['kind'] == 'substance_header':
            label_text = SUBSTANCE_DISPLAY.get(item['text'], item['text'])
            sub_color  = SUBSTANCE_COLORS.get(item['text'], _SUB_FG)
            ax_lbl.scatter([0.045], [y], s=36, color=sub_color,
                           marker='s', zorder=3)
            ax_lbl.text(0.10, y, label_text,
                        fontweight='bold', fontstyle='italic',
                        fontsize=9.5, va='center', ha='left', color=_SUB_FG)
            ax_cat.axhline(y - 0.5, color=_SEP_COLOR, lw=0.4, zorder=0)

        elif item['kind'] == 'spacer':
            ax_cat.axhline(y + 0.3, color='#aaaaaa', lw=0.7, zorder=0)

        elif item['kind'] == 'study':
            r   = item['data']
            cat = str(r['category'])
            x   = cat_x.get(cat, n_cats - 1)
            color = SUBSTANCE_COLORS.get(str(r['substance']), '#444444')

            ax_cat.scatter(x, y, s=95, color=color,
                           edgecolors='white', linewidths=0.8, zorder=3)

            ax_lbl.text(0.14, y, r['study'],
                        va='center', ha='left', fontsize=9)

            n_val = r['N']
            if n_val is not None and not (isinstance(n_val, float) and np.isnan(n_val)):
                ax_lbl.text(0.96, y, str(int(n_val)),
                            va='center', ha='right', fontsize=9)

            # OR annotation below the dot (where available)
            or_val = r.get('computed_or')
            if or_val is not None and not (isinstance(or_val, float) and np.isnan(or_val)):
                ax_cat.text(x, y - 0.24, f"OR={or_val:.2f}",
                            va='top', ha='center', fontsize=6.5,
                            color='#555555', style='italic')

    # ── Legend ────────────────────────────────────────────────────────────────
    present_subs = {
        str(item['data']['substance'])
        for item in layout if item['kind'] == 'study'
    }
    sub_handles = [
        mpatches.Patch(
            color=SUBSTANCE_COLORS.get(s, '#444'),
            label=SUBSTANCE_DISPLAY.get(s, s),
        )
        for s in SUBSTANCE_ORDER_UNIFIED if s in present_subs
    ]

    n_legend_rows = max(1, (len(sub_handles) + 4) // 5)
    bottom_pad    = max(0.10, (1.3 + 0.30 * n_legend_rows) / fig_h)
    fig.subplots_adjust(top=0.965, bottom=bottom_pad, left=0.02, right=0.99)

    fig.legend(
        handles=sub_handles,
        loc='lower center', bbox_to_anchor=(0.5, 0.0),
        ncol=min(5, len(sub_handles)),
        fontsize=8.5, framealpha=0.95, edgecolor='#bbbbbb',
        columnspacing=1.2, handlelength=1.5,
    )

    # ── Title and subtitle ─────────────────────────────────────────────────────
    fig.suptitle(
        "Tier 2 Qualitative Classification: Psychedelic-Assisted Therapies "
        "for Substance Use Disorders",
        fontsize=12, fontweight='bold', y=0.995, va='top',
    )
    fig.text(
        0.5, 0.985,
        "Thresholds: small = OR < 1.5 or g < 0.5;  "
        "moderate = OR 1.5–3 or g 0.5–0.8;  "
        "large = OR ≥ 3 or g ≥ 0.8",
        ha='center', va='top', fontsize=8.0,
        color='#555555', style='italic',
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Unified Tier 2 cat plot written to: {out_path}")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    out_path = _BASE / 'figures' / 'Unified_Tier2_CatPlot.png'
    make_unified_cat_plot(out_path)
