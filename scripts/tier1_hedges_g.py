"""
Tier 1 conversion: standardize effect sizes to Hedges' g, per condition.

Usage:
    python scripts/tier1_hedges_g.py --condition alcohol
    python scripts/tier1_hedges_g.py --condition smoking

Inputs:
    data/<Condition>_Dataset_Cleaned.xlsx   (output of clean_dataset.py)

Outputs:
    tables/<Condition>_Tier1_HedgesG.xlsx       per-study Hedges' g table
    figures/<Condition>_Tier1_ForestPlot.png    three-panel GridSpec forest plot

Conversion formulas (all yield Cohen's d, then Hedges-corrected to g):
    Cohen's d         d (already standardized)
    Hedges' g         g (already standardized)
    F (1 df num)      d = 2 * sqrt(F / df_error)
    Partial eta^2     d = 2 * sqrt(eta_p / (1 - eta_p))   [between-subjects]
    Chi-squared (1)   phi = sqrt(chi2 / N); d = 2*phi/sqrt(1-phi^2)
    Odds ratio        d = log(OR) * sqrt(3) / pi           [Hasselblad-Hedges]
    Risk ratio        d ~ log(RR) * sqrt(3) / pi           [rare-event approx]

Hedges' bias correction:
    g = d * J,  where J = 1 - 3 / (4*df - 1),  df = n_total - 2

Variance (balanced groups, n1 = n2 = N/2 when only N is reported):
    Var(g) = (n1+n2)/(n1*n2) + g^2 / (2*(n1+n2))

Confidence flags:
    clean      direct conversion, balanced-groups assumption reasonable
    approx     conversion required strong assumptions or rough approximation
    excluded   Tier 1 not feasible (multi-df F, within-subjects, etc.)
"""

import argparse
import importlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

_BASE    = Path(__file__).parent.parent
_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS))

import _lib as lib

plt.rcParams.update({
    "font.family":        "sans-serif",
    "font.size":          11,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.linewidth":     0.8,
    "xtick.major.width":  0.8,
    "ytick.major.width":  0.8,
    "figure.dpi":         150,
})

VALID_CONDITIONS = ('alcohol', 'smoking', 'opioid')


def load_config(condition: str):
    cfg = importlib.import_module(f'_config_{condition}')
    if not cfg.CONVERSION_RULES:
        raise NotImplementedError(
            f"{condition.capitalize()} conversion rules not yet hand-coded — populate "
            f"CONVERSION_RULES in _config_{condition}.py."
        )
    return cfg


# ── Forest plot: three-panel GridSpec (labels | CI | stats) ──────────────────

def make_forest_plot(results: pd.DataFrame, out_path: Path, condition: str) -> None:
    layout, x_min, x_max = lib._build_layout(results)
    if not layout:
        print(f"  No convertible studies for {condition}; forest plot skipped.")
        return

    n_rows = len(layout)
    y_top  = n_rows

    fig_h = max(5.0, 0.45 * n_rows + 2.0)
    fig   = plt.figure(figsize=(11.5, fig_h))
    gs    = fig.add_gridspec(1, 3, width_ratios=[2.8, 3.8, 2.1], wspace=0.03)

    ax_lbl  = fig.add_subplot(gs[0])
    ax_ci   = fig.add_subplot(gs[1], sharey=ax_lbl)
    ax_stat = fig.add_subplot(gs[2], sharey=ax_lbl)

    for ax in (ax_lbl, ax_ci, ax_stat):
        ax.set_yticks([])
        ax.set_xticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
    ax_ci.spines['bottom'].set_visible(True)
    ax_ci.spines['bottom'].set_position(('outward', 4))
    ax_ci.set_xticks(ax_ci.get_xticks())

    ax_lbl.set_xlim(0, 1)
    ax_ci.set_xlim(x_min, x_max)
    ax_stat.set_xlim(0, 1)
    ax_lbl.set_ylim(0.5, y_top + 1.2)

    lib._ref_lines(ax_ci, x_min, x_max)

    ax_lbl.text(0.97, y_top + 0.75, 'Study', fontweight='bold',
                va='center', ha='right', fontsize=10)
    ax_stat.text(0.04, y_top + 0.75, 'g  [95 % CI]', fontweight='bold',
                 va='center', ha='left', fontsize=10, family='monospace')

    for i, item in enumerate(layout):
        y = y_top - i
        if item['kind'] == 'header':
            ax_lbl.text(0.97, y, item['text'], fontweight='bold',
                        va='center', ha='right', fontsize=11)
            ax_ci.hlines(y - 0.5, x_min, x_max, color='lightgray', lw=0.5)
            continue

        r = item['data']
        lib._draw_ci_row(ax_ci, r, y)
        ax_lbl.text(0.97, y, f"{r['study']} (N={r['N']})",
                    va='center', ha='right', fontsize=9.5)
        tag   = '' if r['confidence'] == 'clean' else ' *'
        stats = f"{r['g']:+.2f}  [{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}]{tag}"
        ax_stat.text(0.04, y, stats,
                     va='center', ha='left', fontsize=8.5, family='monospace')

    cond_label = condition.capitalize()
    ax_ci.set_xlabel(
        "Hedges' g  (← favors comparator  |  favors psychedelic →)",
        fontsize=10, labelpad=6
    )
    fig.suptitle(
        f"Tier 1 Standardized Effect Sizes — Psychedelics for "
        f"{cond_label} Use Disorder",
        fontsize=12, y=0.98
    )
    lib._legend(fig)

    bottom_pad = max(0.10, 1.0 / fig_h)
    fig.subplots_adjust(top=0.93, bottom=bottom_pad, left=0.02, right=0.98)
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Compute Tier 1 Hedges\' g conversions for a condition.')
    parser.add_argument(
        '--condition', required=True, choices=VALID_CONDITIONS,
        help='Which condition to process.')
    args = parser.parse_args()

    condition = args.condition
    cfg       = load_config(condition)

    cond_cap   = condition.capitalize()
    input_path = _BASE / 'data' / f'{cond_cap}_Dataset_Cleaned.xlsx'
    out_table  = _BASE / 'tables'  / f'{cond_cap}_Tier1_HedgesG.xlsx'
    out_plot   = _BASE / 'figures' / f'{cond_cap}_Tier1_ForestPlot.png'

    if not input_path.exists():
        print(f"ERROR: Cleaned dataset not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    df      = pd.read_excel(input_path)
    results = lib.build_results(df, cfg.CONVERSION_RULES)

    print("Conversion outcomes:")
    print(results['confidence'].value_counts(dropna=False).to_string())
    print()

    conv = results[results['g'].notna()].copy()
    print(f"Studies with computed Hedges' g: {len(conv)}")
    if len(conv):
        print(f"  by confidence:  clean={( conv['confidence']=='clean').sum()}, "
              f"approx={(conv['confidence']=='approx').sum()}")
        print(f"  by substance: {conv['substance'].value_counts().to_dict()}")
        print()
        show_cols = ['study', 'substance', 'method', 'confidence',
                     'g', 'se_g', 'ci_lo', 'ci_hi']
        print(conv[show_cols].round(3).to_string(index=False))

    results.to_excel(out_table, index=False)
    print(f"\nResults table written to: {out_table}")

    make_forest_plot(results, out_plot, condition)
    print(f"Forest plot written to:   {out_plot}")


if __name__ == '__main__':
    main()
