"""
Unified Tier 1 forest plot: all conditions and substances in a single figure.

Usage:
    python scripts/unified_forest_plot.py

Output:
    figures/Unified_Tier1_ForestPlot.png
"""

import importlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

_BASE    = Path(__file__).parent.parent
_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import _lib as lib

# ── Ordering and colours ───────────────────────────────────────────────────────

CONDITIONS = [
    ('alcohol', 'Alcohol Use Disorder'),
    ('opioid',  'Opioid Use Disorder'),
    ('smoking', 'Tobacco Use Disorder'),
]

# Substances present in the current data, in display order by drug class
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

# Extend the base colour map with substances not in per-condition plots
SUBSTANCE_COLORS = {
    **lib.SUBSTANCE_COLORS,         # Psilocybin, Ketamine, MDMA, LSD
    'Ibogaine':         '#9467bd',  # purple
    'Ayahuasca':        '#8c564b',  # brown
    'Mescaline':        '#e377c2',  # pink
    'OtherPsychedelic': '#7f7f7f',  # grey
    'Cannabis':         '#17becf',  # cyan
}

# ── Visual constants ───────────────────────────────────────────────────────────

_COND_BG   = '#EDF1FA'   # light blue band for condition headers
_COND_FG   = '#162040'   # dark navy text for condition headers
_SUB_FG    = '#2c2c2c'   # substance sub-header text
_SEP_COLOR = '#cccccc'   # horizontal separator lines
_NULL_COLOR = '#4d4d4d'  # null (g=0) reference line

plt.rcParams.update({
    'font.family':        'sans-serif',
    'font.size':          9,
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.linewidth':     0.8,
    'xtick.major.width':  0.8,
    'figure.dpi':         150,
})

# ── Data loading ───────────────────────────────────────────────────────────────

def _load_condition(condition: str) -> pd.DataFrame | None:
    cond_cap   = condition.capitalize()
    input_path = _BASE / 'data' / f'{cond_cap}_Dataset_Cleaned.xlsx'
    if not input_path.exists():
        print(f"  Skipping {condition}: cleaned dataset not found.")
        return None
    cfg = importlib.import_module(f'_config_{condition}')
    if not cfg.CONVERSION_RULES:
        return None
    df = pd.read_excel(input_path)
    return lib.build_results(df, cfg.CONVERSION_RULES)


# ── Layout construction ────────────────────────────────────────────────────────

def _sort_studies(df: pd.DataFrame) -> pd.DataFrame:
    known  = [s for s in SUBSTANCE_ORDER_UNIFIED if s in df['substance'].values]
    others = sorted(set(df['substance'].unique()) - set(SUBSTANCE_ORDER_UNIFIED))
    df = df.copy()
    df['substance'] = pd.Categorical(df['substance'], categories=known + others, ordered=True)
    return df.sort_values(['substance', 'Year']).reset_index(drop=True)


def build_layout(
    all_results: dict[str, pd.DataFrame],
) -> tuple[list[dict], float, float]:
    """Return (layout, x_min, x_max) across all conditions."""
    layout: list[dict] = []
    ci_vals: list[float] = []

    for condition, label in CONDITIONS:
        if condition not in all_results:
            continue
        plot_df = all_results[condition][all_results[condition]['g'].notna()].copy()
        if plot_df.empty:
            continue

        layout.append({'kind': 'condition_header', 'text': label})
        plot_df = _sort_studies(plot_df)

        last_sub: str | None = None
        for _, r in plot_df.iterrows():
            sub = str(r['substance'])
            if sub != last_sub:
                layout.append({'kind': 'substance_header', 'text': sub})
                last_sub = sub
            layout.append({'kind': 'study', 'data': r.to_dict()})
            ci_vals.extend([float(r['ci_lo']), float(r['ci_hi'])])

        layout.append({'kind': 'spacer'})

    # Drop trailing spacer
    if layout and layout[-1]['kind'] == 'spacer':
        layout.pop()

    if ci_vals:
        x_min = min(min(ci_vals), -0.5) - 0.35
        x_max = max(max(ci_vals),  1.5) + 0.35
    else:
        x_min, x_max = -1.0, 3.0

    return layout, x_min, x_max


# ── CI row rendering ───────────────────────────────────────────────────────────

def _draw_row(ax, r: dict, y: float) -> None:
    color    = SUBSTANCE_COLORS.get(str(r['substance']), '#444')
    is_clean = r['confidence'] == 'clean'
    alpha    = 1.0 if is_clean else 0.70
    ms       = float(np.clip(1.0 / r['var_g'] * 14, 36, 300))

    ax.plot([r['ci_lo'], r['ci_hi']], [y, y],
            color=color, alpha=alpha, lw=1.5, zorder=2, solid_capstyle='round')
    for x_cap in (r['ci_lo'], r['ci_hi']):
        ax.plot([x_cap, x_cap], [y - 0.17, y + 0.17],
                color=color, alpha=alpha, lw=1.3)
    if is_clean:
        ax.scatter(r['g'], y, s=ms, color=color, marker='s',
                   edgecolors='white', linewidths=0.7, zorder=3)
    else:
        ax.scatter(r['g'], y, s=ms, facecolors='white',
                   edgecolors=color, marker='s', linewidths=1.5, zorder=3)


# ── Main plot ──────────────────────────────────────────────────────────────────

def make_unified_forest_plot(out_path: Path) -> None:

    # Load data
    all_results: dict[str, pd.DataFrame] = {}
    for condition, _ in CONDITIONS:
        res = _load_condition(condition)
        if res is not None:
            all_results[condition] = res

    layout, x_min, x_max = build_layout(all_results)
    if not any(item['kind'] == 'study' for item in layout):
        print("No convertible studies; plot skipped.")
        return

    n_rows = len(layout)
    # y positions: header at y_top, rows descend from y_top - 1
    y_top  = n_rows + 1

    row_h  = 0.36          # inches per layout row
    fig_h  = max(7.0, row_h * n_rows + 3.2)
    fig_w  = 13.0

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor='white')
    gs  = fig.add_gridspec(1, 3, width_ratios=[2.9, 4.5, 2.2], wspace=0.02)
    ax_lbl  = fig.add_subplot(gs[0])
    ax_ci   = fig.add_subplot(gs[1], sharey=ax_lbl)
    ax_stat = fig.add_subplot(gs[2], sharey=ax_lbl)

    # Spine cleanup — only bottom spine on the CI panel
    for ax in (ax_lbl, ax_ci, ax_stat):
        ax.set_yticks([])
        ax.set_xticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
    ax_ci.spines['bottom'].set_visible(True)
    ax_ci.spines['bottom'].set_linewidth(0.8)
    ax_ci.spines['bottom'].set_position(('outward', 4))

    ax_lbl.set_xlim(0, 1)
    ax_ci.set_xlim(x_min, x_max)
    ax_stat.set_xlim(0, 1)
    ax_lbl.set_ylim(0.2, y_top + 0.9)

    # Reference lines in CI panel
    ax_ci.axvline(0, color=_NULL_COLOR, lw=1.0, linestyle='--', zorder=1)
    for b in (0.2, 0.5, 0.8):
        ax_ci.axvline( b, color='#c8c8c8', lw=0.5, ls=':', alpha=0.8, zorder=0)
        ax_ci.axvline(-b, color='#c8c8c8', lw=0.5, ls=':', alpha=0.5, zorder=0)

    # ── Column headers ─────────────────────────────────────────────────────────
    hdr_y = y_top + 0.3
    ax_lbl.text(0.04, hdr_y, 'Study', fontweight='bold',
                va='center', ha='left', fontsize=10)
    ax_lbl.text(0.96, hdr_y, 'N', fontweight='bold',
                va='center', ha='right', fontsize=10)
    ci_mid = (x_min + x_max) / 2
    ax_ci.text(ci_mid, hdr_y, "Hedges' g  (95% CI)",
               fontweight='bold', va='center', ha='center', fontsize=10)
    ax_stat.text(0.04, hdr_y, 'g  [95% CI]', fontweight='bold',
                 va='center', ha='left', fontsize=10, family='monospace')

    # Thin rule below column headers
    rule_y = y_top - 0.35
    for ax in (ax_lbl, ax_ci, ax_stat):
        ax.axhline(rule_y, color='#666', lw=0.9, zorder=4)

    # ── Draw rows ──────────────────────────────────────────────────────────────
    for i, item in enumerate(layout):
        y = y_top - 1 - i  # rows descend

        if item['kind'] == 'condition_header':
            for ax in (ax_lbl, ax_ci, ax_stat):
                ax.axhspan(y - 0.48, y + 0.52, color=_COND_BG, zorder=0, lw=0)
            # Left border accent (thin coloured bar at x=0 edge)
            ax_lbl.plot([0.005, 0.005], [y - 0.48, y + 0.52],
                        color=_COND_FG, lw=3.5, zorder=5,
                        solid_capstyle='butt', clip_on=False)
            ax_lbl.text(0.04, y, item['text'],
                        fontweight='bold', fontsize=11,
                        va='center', ha='left', color=_COND_FG)

        elif item['kind'] == 'substance_header':
            label_text = SUBSTANCE_DISPLAY.get(item['text'], item['text'])
            sub_color  = SUBSTANCE_COLORS.get(item['text'], _SUB_FG)
            # Small colour swatch before the label
            ax_lbl.scatter([0.045], [y], s=36, color=sub_color,
                           marker='s', zorder=3)
            ax_lbl.text(0.10, y, label_text,
                        fontweight='bold', fontstyle='italic',
                        fontsize=9.5, va='center', ha='left', color=_SUB_FG)
            ax_ci.axhline(y - 0.5, color=_SEP_COLOR, lw=0.5, zorder=0)

        elif item['kind'] == 'spacer':
            ax_ci.axhline(y + 0.3, color='#aaaaaa', lw=0.7, zorder=0)

        elif item['kind'] == 'study':
            r = item['data']
            _draw_row(ax_ci, r, y)

            study_label = r['study']
            ax_lbl.text(0.14, y, study_label,
                        va='center', ha='left', fontsize=9)
            ax_lbl.text(0.96, y, f"{int(r['N'])}",
                        va='center', ha='right', fontsize=9)

            tag   = '' if r['confidence'] == 'clean' else '†'
            stats = f"{r['g']:+.2f}  [{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}]{tag}"
            ax_stat.text(0.04, y, stats, va='center', ha='left',
                         fontsize=8.5, family='monospace')

    # ── X-axis ticks and label ─────────────────────────────────────────────────
    step    = 0.5
    t_start = np.ceil(x_min / step) * step
    t_end   = np.floor(x_max / step) * step
    x_ticks = np.arange(t_start, t_end + step * 0.1, step)
    ax_ci.set_xticks(x_ticks)
    ax_ci.tick_params(axis='x', labelsize=8.5, length=3, width=0.8, pad=3)
    ax_ci.set_xlabel(
        "← Favours comparator          Hedges' g          Favours psychedelic →",
        fontsize=9, labelpad=6
    )

    # ── Title ─────────────────────────────────────────────────────────────────
    fig.suptitle(
        "Tier 1 Standardized Effect Sizes: Psychedelic-Assisted Therapies "
        "for Substance Use Disorders",
        fontsize=12, fontweight='bold', y=0.995, va='top',
    )

    # ── Legend ────────────────────────────────────────────────────────────────
    present_subs = {
        str(item['data']['substance'])
        for item in layout if item['kind'] == 'study'
    }

    clean_h  = mlines.Line2D([], [], color='#606060', marker='s', markersize=6,
                              markerfacecolor='#606060', markeredgecolor='white',
                              lw=1.2, label='Direct conversion (clean)')
    approx_h = mlines.Line2D([], [], color='#606060', marker='s', markersize=6,
                              markerfacecolor='white', markeredgecolor='#606060',
                              lw=1.4, label='Approximate conversion (†)')
    weight_h = mlines.Line2D([], [], lw=0, alpha=0,
                              label='Marker size ∝ inverse-variance weight')
    sub_handles = [
        mpatches.Patch(color=SUBSTANCE_COLORS.get(s, '#444'),
                       label=SUBSTANCE_DISPLAY.get(s, s))
        for s in SUBSTANCE_ORDER_UNIFIED if s in present_subs
    ]

    fig.legend(
        handles=[clean_h, approx_h, weight_h] + sub_handles,
        loc='lower center', bbox_to_anchor=(0.5, 0.0),
        ncol=min(4, 3 + len(sub_handles)),
        fontsize=8.5, framealpha=0.95, edgecolor='#bbbbbb',
        columnspacing=1.2, handlelength=1.5,
    )

    n_legend_rows = max(1, (3 + len(sub_handles) + 3) // 4)
    bottom_pad    = max(0.08, (1.0 + 0.32 * n_legend_rows) / fig_h)
    fig.subplots_adjust(top=0.97, bottom=bottom_pad, left=0.02, right=0.98)

    # ── Save ──────────────────────────────────────────────────────────────────

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Unified forest plot written to: {out_path}")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    out_path = _BASE / 'figures' / 'Unified_Tier1_ForestPlot.png'
    make_unified_forest_plot(out_path)
