"""
Tier 1 conversion: standardize alcohol-trial effect sizes to Hedges' g.

Inputs:
    Alcohol_Dataset_Cleaned.xlsx  (output of clean_alcohol_dataset.py)

Outputs:
    Alcohol_Tier1_HedgesG.xlsx                per-study converted effect sizes + metadata
    Alcohol_Tier1_ForestPlot_GridSpec.png     three-panel layout (labels | CI | stats)
    Alcohol_Tier1_ForestPlot_YAxis.png        single-axes layout with y-axis tick labels

Conversion formulas (all yield Cohen's d, then Hedges-corrected to g):
    Cohen's d         d (already standardized)
    Hedges' g         g (already standardized)
    F (1 df num)      d = 2 * sqrt(F / df_error)
    Partial eta^2     d = 2 * sqrt(eta_p / (1 - eta_p))            [between-subjects]
    Chi-squared (1)   phi = sqrt(chi2 / N); d = 2*phi/sqrt(1-phi^2)
    Odds ratio        d = log(OR) * sqrt(3) / pi                   [Hasselblad-Hedges]
    Risk ratio        d ~ log(RR) * sqrt(3) / pi                   [rare-event approx]

Hedges' bias correction:
    g = d * J,  where J = 1 - 3 / (4*df - 1),  df = n_total - 2

Variance (assumes balanced groups, n1 = n2 = N/2 when only N reported):
    Var(g) = (n1+n2)/(n1*n2) + g^2 / (2*(n1+n2))

Confidence flags:
    clean      direct conversion, balanced-groups assumption reasonable
    approx     conversion required strong assumptions or rough approximation
    excluded   Tier 1 not feasible (multi-df F numerator, within-subjects t, etc.)
"""

import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — safe on Windows without display
import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

_BASE          = Path(__file__).parent.parent
INPUT          = _BASE / 'data'    / 'Alcohol_Dataset_Cleaned.xlsx'
OUT_TABLE      = _BASE / 'tables'  / 'Alcohol_Tier1_HedgesG.xlsx'
OUT_PLOT_GS    = _BASE / 'figures' / 'Alcohol_Tier1_ForestPlot_GridSpec.png'
OUT_PLOT_YAXIS = _BASE / 'figures' / 'Alcohol_Tier1_ForestPlot_YAxis.png'

# -----------------------------------------------------------------------------
# Per-study conversion rules
#
# Keyed by (first_author_surname, year). Direction multiplier defaults to +1;
# set to -1 when the favored direction is the opposite of the metric's natural
# sign (e.g., RR < 1 for a "bad" outcome means treatment WINS).
# -----------------------------------------------------------------------------
CONVERSION_RULES = {
    ('Bogenschutz', 2015): {'method': 'd',     'confidence': 'clean'},
    ('Bogenschutz', 2022): {'method': 'g',     'confidence': 'clean'},
    ('Bowen',       1970): {'method': None,    'confidence': 'excluded',
                            'note': 'No outcome statistic reported'},
    ('Dakwar',      2020): {'method': 'F', 'df_error': 797, 'confidence': 'approx',
                            'note': 'F is interaction term with large df_error; rough'},
    ('Das',         2019): {'method': 'eta_p', 'confidence': 'clean'},
    ('Denson',      1970): {'method': None,    'confidence': 'excluded',
                            'note': 'No outcome statistic reported'},
    ('Dusen',       1967): {'method': None,    'confidence': 'excluded',
                            'note': 'Group means without SDs; ns'},
    ('Gent',        2024): {'method': None,    'confidence': 'excluded',
                            'note': 'F has 2 df numerator (3-arm); not 1-df comparison'},
    ('Grabski',     2022): {'method': None,    'confidence': 'excluded',
                            'note': 'Mean difference reported without SDs'},
    ('Heinzerling', 2023): {'method': None,    'confidence': 'excluded',
                            'note': 'F has 6 df numerator; repeated-measures design'},
    ('Hollister',   1969): {'method': 'F', 'df_error': 50, 'confidence': 'clean',
                            'direction': -1,
                            'note': 'Sig. F unfavorable to LSD vs dextroamphetamine'},
    ('Jensen',      2024): {'method': 'd',     'confidence': 'clean'},
    ('Jensen',      1963): {'method': None,    'confidence': 'excluded',
                            'note': 'Two-group proportions; downgrade to Tier 2'},
    ('Johnson',     1969): {'method': None,    'confidence': 'excluded',
                            'note': 'Reported only as "NS"'},
    ('Kurland',     1967): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm rate; no comparator'},
    ('Luquiens',    2025): {'method': None,    'confidence': 'excluded',
                            'note': 'Risk difference only; downgrade to Tier 2'},
    ('MacLean',     1961): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm improvement rate'},
    ('Marvania',    2024): {'method': None,    'confidence': 'excluded',
                            'note': 'Within-group AASE change; no comparator'},
    ('Nicholas',    2022): {'method': 'g',     'confidence': 'clean'},
    ("O'Reilly",    1964): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm abstinence rate'},
    ('Pagni',       2025): {'method': 'eta_p', 'confidence': 'approx',
                            'note': 'Small N=84, partial eta^2 conversion approximate'},
    ('Pagni',       2024): {'method': None,    'confidence': 'excluded',
                            'note': 'Within-subjects t (df=3); not between-groups'},
    ('Pahnke',      1970): {'method': None,    'confidence': 'excluded',
                            'note': 'Two dose-group proportions; downgrade to Tier 2'},
    ('Rieser',      2025): {'method': 'd',     'confidence': 'clean'},
    ('Rothberg',    2020): {'method': 'OR',    'confidence': 'approx',
                            'note': 'OR reported as approx (~5); no cell counts'},
    ('Sessa',       2021): {'method': None,    'confidence': 'excluded',
                            'note': 'Within-group mean change; no comparator'},
    ('Sessa',       2019): {'method': None,    'confidence': 'excluded',
                            'note': 'Case series 2/4 abstinent; no comparator'},
    ('Smart',       1966): {'method': None,    'confidence': 'excluded',
                            'note': 'Two-group proportions; downgrade to Tier 2'},
    ('Smith',       1958): {'method': None,    'confidence': 'excluded',
                            'note': 'Single-arm improvement rate'},
    ('Terasaki',    2022): {'method': 'RR', 'direction': -1, 'confidence': 'approx',
                            'note': 'RR=0.37 = LESS readmission (favors ketamine); sign flipped'},
    ('Thurgur',     2025): {'method': None,    'confidence': 'excluded',
                            'note': 'Bayesian posterior not directly convertible'},
    ('Tomsovic',    1970): {'method': 'chi2',  'confidence': 'approx',
                            'note': 'Primary chi^2 (LSD vs control I, nonschiz, abstinence)'},
    ('Yoon',        2019): {'method': None,    'confidence': 'excluded',
                            'note': 'Case series 5/5 response; no comparator'},
}

# Substance display order in forest plot
SUBSTANCE_ORDER = ['Psilocybin', 'Ketamine', 'MDMA', 'LSD']
SUBSTANCE_COLS = ['Psilocybin', 'LSD', 'Ketamine', 'MDMA', 'Ayahuasca',
                  'Mescaline', 'Ibogaine', 'Cannabis', 'OtherPsychedelic']

C_GRAY  = "#636363"   # mid-gray for reference lines
C_LGRAY = "#bdbdbd"   # light gray for benchmarks and legend edges

# Visual styling — colorblind-safe palette, prints OK in grayscale
SUBSTANCE_COLORS = {
    'Psilocybin': '#1f77b4',  # blue
    'Ketamine':   '#2ca02c',  # green
    'MDMA':       '#ff7f0e',  # orange
    'LSD':        '#d62728',  # red
}


# -----------------------------------------------------------------------------
# Conversion helpers
# -----------------------------------------------------------------------------

def hedges_J(dof: float) -> float:
    """Hedges' bias correction factor (Hedges & Olkin 1985 approximation)."""
    if dof < 2:
        return float('nan')
    return 1 - 3 / (4*dof - 1)


def variance_g(g: float, n_total: float) -> float:
    """Sampling variance of Hedges' g, balanced-groups assumption."""
    n1 = n2 = n_total / 2
    return (n1 + n2)/(n1*n2) + g**2 / (2*(n1+n2))


def convert_to_d(method: str, measure, n_total: float, params: dict):
    """Compute Cohen's d from the supplied metric. Returns d (signed)."""
    m = float(measure)
    if method == 'd':
        return m
    if method == 'g':
        # 'g' path is handled directly in compute(), short-circuiting Hedges step
        return m
    if method == 'F':
        return 2 * math.sqrt(m / params['df_error'])
    if method == 'eta_p':
        if m <= 0 or m >= 1:
            return float('nan')
        return 2 * math.sqrt(m / (1 - m))
    if method == 'chi2':
        phi = math.sqrt(m / n_total)
        if phi >= 1:
            phi = 0.99
        return 2 * phi / math.sqrt(1 - phi**2)
    if method == 'OR':
        return math.log(m) * math.sqrt(3) / math.pi
    if method == 'RR':
        return math.log(m) * math.sqrt(3) / math.pi
    raise ValueError(f"Unknown method: {method}")


def compute(rule: dict, measure, n_total: float):
    """Return dict with d, g, var_g, se_g, ci_lo, ci_hi or None if excluded."""
    method = rule.get('method')
    if method is None or pd.isna(measure) or pd.isna(n_total):
        return None

    direction = rule.get('direction', 1)
    d = convert_to_d(method, measure, n_total, rule) * direction

    # Apply Hedges' correction (skip if input was already 'g')
    if method == 'g':
        g = d  # already corrected
    else:
        df = n_total - 2
        g = d * hedges_J(df)

    v = variance_g(g, n_total)
    se = math.sqrt(v)
    return {
        'd': d, 'g': g, 'var_g': v, 'se_g': se,
        'ci_lo': g - 1.96*se, 'ci_hi': g + 1.96*se,
    }


# -----------------------------------------------------------------------------
# Data assembly
# -----------------------------------------------------------------------------

def first_author_surname(citation: str) -> str:
    surname = re.split(r'[,;]', str(citation).strip(), maxsplit=1)[0].strip()
    return surname.replace('’', "'").replace('‘', "'")


def short_label(citation: str) -> str:
    """Return a short 'Surname Year' style label."""
    return first_author_surname(citation)


def primary_substance(row) -> str:
    for col in SUBSTANCE_COLS:
        v = row.get(col)
        try:
            if pd.notna(v) and float(v) == 1:
                return col
        except (TypeError, ValueError):
            continue
    return 'Unknown'


def build_results(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        key = (first_author_surname(r['Citation/Title']), int(r['Year']))
        rule = CONVERSION_RULES.get(key, {'method': None, 'confidence': 'excluded',
                                          'note': 'Rule not defined'})
        n = float(r['SampleSize_NFinal'])
        result = compute(rule, r.get('measure'), n)
        rows.append({
            'study': f"{key[0]} {key[1]}",
            'Year': key[1],
            'N': int(n) if not pd.isna(n) else None,
            'substance': primary_substance(r),
            'metric': r.get('metric'),
            'measure': r.get('measure'),
            'method': rule.get('method'),
            'confidence': rule.get('confidence'),
            'note': rule.get('note', ''),
            'd':      result['d']      if result else None,
            'g':      result['g']      if result else None,
            'var_g':  result['var_g']  if result else None,
            'se_g':   result['se_g']   if result else None,
            'ci_lo':  result['ci_lo']  if result else None,
            'ci_hi':  result['ci_hi']  if result else None,
        })
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Forest plot — shared helpers
# -----------------------------------------------------------------------------

def _build_layout(results: pd.DataFrame):
    """Filter to convertible studies, sort, build interleaved header+study list."""
    plot_df = results[results['g'].notna()].copy()
    plot_df['substance'] = pd.Categorical(
        plot_df['substance'], categories=SUBSTANCE_ORDER, ordered=True
    )
    plot_df = plot_df.sort_values(['substance', 'Year']).reset_index(drop=True)

    layout, last_sub = [], None
    for _, r in plot_df.iterrows():
        if r['substance'] != last_sub:
            layout.append({'kind': 'header', 'text': str(r['substance'])})
            last_sub = r['substance']
        layout.append({'kind': 'study', 'data': r.to_dict()})

    ci_los = plot_df['ci_lo'].values
    ci_his = plot_df['ci_hi'].values
    x_min  = min(np.min(ci_los), -0.5) - 0.25
    x_max  = max(np.max(ci_his),  1.5) + 0.25
    return layout, x_min, x_max


def _draw_ci_row(ax, r: dict, y: float) -> None:
    """CI line, end caps, and square point estimate on axes with data coordinates."""
    color    = SUBSTANCE_COLORS.get(r['substance'], '#444')
    is_clean = r['confidence'] == 'clean'
    alpha    = 1.0 if is_clean else 0.6
    ms       = float(np.clip(1.0 / r['var_g'] * 12, 40, 280))

    ax.plot([r['ci_lo'], r['ci_hi']], [y, y],
            color=color, alpha=alpha, lw=1.6, zorder=2, solid_capstyle='round')
    ax.plot([r['ci_lo'], r['ci_lo']], [y - 0.18, y + 0.18],
            color=color, alpha=alpha, lw=1.4)
    ax.plot([r['ci_hi'], r['ci_hi']], [y - 0.18, y + 0.18],
            color=color, alpha=alpha, lw=1.4)
    if is_clean:
        ax.scatter(r['g'], y, s=ms, color=color, marker='s',
                   edgecolor='white', lw=0.8, zorder=3)
    else:
        ax.scatter(r['g'], y, s=ms, facecolor='white',
                   edgecolor=color, marker='s', lw=1.6, zorder=3)


def _ref_lines(ax, x_min: float, x_max: float) -> None:
    """Zero reference (dashed) and Cohen benchmarks (dotted) on the forest axes."""
    ax.axvline(0, color=C_GRAY, lw=0.9, linestyle='--', zorder=1)
    for b in (0.2, 0.5, 0.8):
        ax.axvline(b, color=C_LGRAY, lw=0.4, ls=':', alpha=0.6, zorder=0)


def _legend(fig) -> None:
    clean_h  = mlines.Line2D([], [], color=C_GRAY, marker='s', markersize=7,
                              markerfacecolor=C_GRAY, markeredgecolor='white', lw=1.4,
                              label='Filled = direct conversion (clean)')
    approx_h = mlines.Line2D([], [], color=C_GRAY, marker='s', markersize=7,
                              markerfacecolor='white', markeredgecolor=C_GRAY, lw=1.4,
                              label='Hollow = approximate conversion')
    weight_h = mlines.Line2D([], [], lw=0, alpha=0,
                              label='Marker size ∝ inverse-variance weight  (n₁ = n₂ = N/2)')
    fig.legend(handles=[clean_h, approx_h, weight_h],
               loc='lower center', bbox_to_anchor=(0.5, 0.0),
               ncol=3, fontsize=9, framealpha=0.9, edgecolor=C_LGRAY)


# -----------------------------------------------------------------------------
# Forest plot — Approach 1: three-panel GridSpec (labels | CI | stats)
# -----------------------------------------------------------------------------

def make_forest_plot_gridspec(results: pd.DataFrame, out_path) -> None:
    """
    Three separate axes joined by GridSpec: a label panel on the left, the
    forest (CI) panel in the middle, and a monospace stats panel on the right.
    No text is placed in data coordinates to manufacture gutters — each panel
    has its own coordinate system and proper axes width.
    """
    layout, x_min, x_max = _build_layout(results)
    n_rows = len(layout)
    y_top  = n_rows

    fig_h = max(5.0, 0.45 * n_rows + 2.0)
    fig   = plt.figure(figsize=(11.5, fig_h))
    gs    = fig.add_gridspec(1, 3, width_ratios=[2.8, 3.8, 2.1], wspace=0.03)

    ax_lbl  = fig.add_subplot(gs[0])
    ax_ci   = fig.add_subplot(gs[1], sharey=ax_lbl)
    ax_stat = fig.add_subplot(gs[2], sharey=ax_lbl)

    # Strip every panel to bare minimum; only the forest panel keeps a bottom spine
    for ax in (ax_lbl, ax_ci, ax_stat):
        ax.set_yticks([])
        ax.set_xticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
    ax_ci.spines['bottom'].set_visible(True)
    ax_ci.spines['bottom'].set_position(('outward', 4))
    ax_ci.set_xticks(ax_ci.get_xticks())   # restore CI panel ticks after blanket clear

    ax_lbl.set_xlim(0, 1)
    ax_ci.set_xlim(x_min, x_max)
    ax_stat.set_xlim(0, 1)
    ax_lbl.set_ylim(0.5, y_top + 1.2)   # sharey propagates to the other two

    _ref_lines(ax_ci, x_min, x_max)

    # Column headers one row above the data
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
        _draw_ci_row(ax_ci, r, y)

        # Label panel: right-aligned
        ax_lbl.text(0.97, y, f"{r['study']} (N={r['N']})",
                    va='center', ha='right', fontsize=9.5)

        # Stats panel: left-aligned monospace
        tag   = '' if r['confidence'] == 'clean' else ' *'
        stats = f"{r['g']:+.2f}  [{r['ci_lo']:+.2f}, {r['ci_hi']:+.2f}]{tag}"
        ax_stat.text(0.04, y, stats,
                     va='center', ha='left', fontsize=8.5, family='monospace')

    ax_ci.set_xlabel(
        "Hedges' g  (← favors comparator  |  favors psychedelic →)",
        fontsize=10, labelpad=6
    )
    fig.suptitle(
        "Tier 1 Standardized Effect Sizes — Psychedelics for Alcohol Use Disorder",
        fontsize=12, y=0.98
    )
    _legend(fig)

    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.02, right=0.98)
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)


# -----------------------------------------------------------------------------
# Forest plot — Approach 2: single axes, y-axis tick labels (no stats column)
# -----------------------------------------------------------------------------

def make_forest_plot_yaxis(results: pd.DataFrame, out_path) -> None:
    """
    Single axes with study labels on the proper y-axis and group headers as
    bold tick labels. No text is placed in data coordinates. No stats column.
    Closest in structure to standard published forest plots.
    """
    layout, x_min, x_max = _build_layout(results)
    n_rows = len(layout)
    y_top  = n_rows

    fig_h = max(5.0, 0.45 * n_rows + 2.0)
    fig, ax = plt.subplots(figsize=(8.5, fig_h))
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0.5, y_top + 1.0)

    _ref_lines(ax, x_min, x_max)

    # Build tick positions/labels and draw CI rows in one pass
    tick_ys, tick_labels, is_header_row = [], [], []
    for i, item in enumerate(layout):
        y = y_top - i
        tick_ys.append(y)
        if item['kind'] == 'header':
            tick_labels.append(item['text'])
            is_header_row.append(True)
            ax.hlines(y - 0.5, x_min, x_max, color='lightgray', lw=0.5)
        else:
            r = item['data']
            tick_labels.append(f"{r['study']}  (N={r['N']})")
            is_header_row.append(False)
            _draw_ci_row(ax, r, y)

    # Apply y-axis tick labels, then bold the substance-header entries
    ax.set_yticks(tick_ys)
    ax.set_yticklabels(tick_labels, fontsize=9.5)
    ax.tick_params(axis='y', length=0, pad=8)
    for tick_obj, header in zip(ax.get_yticklabels(), is_header_row):
        if header:
            tick_obj.set_fontweight('bold')
            tick_obj.set_fontsize(11)

    # Spines
    for sp in ('left', 'top', 'right'):
        ax.spines[sp].set_visible(False)
    ax.spines['bottom'].set_position(('outward', 6))

    ax.set_xlabel(
        "Hedges' g  (← favors comparator  |  favors psychedelic →)",
        fontsize=10.5, labelpad=8
    )
    ax.set_title(
        "Tier 1 Standardized Effect Sizes — Psychedelics for Alcohol Use Disorder",
        fontsize=12, pad=14, loc='left'
    )
    _legend(fig)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    df = pd.read_excel(INPUT)
    results = build_results(df)

    # Counts by confidence
    print("Conversion outcomes:")
    print(results['confidence'].value_counts(dropna=False).to_string())
    print()

    # Summary of the convertible set
    conv = results[results['g'].notna()].copy()
    print(f"Studies with computed Hedges' g: {len(conv)}")
    print(f"  by confidence:  clean={ (conv['confidence']=='clean').sum() }, "
          f"approx={ (conv['confidence']=='approx').sum() }")
    print(f"  by substance: { conv['substance'].value_counts().to_dict() }")
    print()
    print("Effect-size table (Tier 1 convertible studies):")
    show_cols = ['study', 'substance', 'method', 'confidence',
                 'g', 'se_g', 'ci_lo', 'ci_hi']
    print(conv[show_cols].round(3).to_string(index=False))

    # Save full table (including excluded studies, for traceability)
    results.to_excel(OUT_TABLE, index=False)
    print(f"\nResults table written to: {OUT_TABLE}")

    make_forest_plot_gridspec(results, OUT_PLOT_GS)
    print(f"Forest plot (GridSpec) written to:  {OUT_PLOT_GS}")

    make_forest_plot_yaxis(results, OUT_PLOT_YAXIS)
    print(f"Forest plot (Y-axis)   written to:  {OUT_PLOT_YAXIS}")


if __name__ == '__main__':
    main()
