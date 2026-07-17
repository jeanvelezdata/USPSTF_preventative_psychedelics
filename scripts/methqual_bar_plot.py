"""
Methodological Quality bar graph: Pre-1980 vs 2010+ (Alcohol).

Usage:
    python scripts/methqual_bar_plot.py

Output:
    figures/Alcohol_MethQual_BarPlot.png
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

_BASE = Path(__file__).parent.parent

# ── Data (Table 2, Alcohol_Descriptive_Analyses.docx) ─────────────────────────

CRITERIA = [
    "Randomization",
    "Any blinding",
    "Double-blind or above",
    "Comparator/control group",
    "Power reported or discussed",
    "≥80% retention",
    "Validated outcome scale",
    "Confounders assessed",
    "Inclusion/exclusion criteria stated",
    "≥13/14 design criteria described",
    "Funding/COI disclosed",
    "Primary care interface",
]

PRE1980 = [54, 46, 15, 69,  0, 54, 31, 69, 54,  8, 62,  0]
POST2010 = [70, 55, 50, 65, 35, 95, 100, 75, 100, 60, 100,  5]

# ── Visual constants (matches unified plots) ───────────────────────────────────

_COND_BG  = '#EDF1FA'
_COND_FG  = '#162040'
_ERA_PRE  = '#8096b8'   # muted slate-blue  → Pre-1980
_ERA_POST = '#162040'   # dark navy          → 2010+
_GRID_CLR = '#e0e0e0'

plt.rcParams.update({
    'font.family':        'sans-serif',
    'font.size':          9,
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.linewidth':     0.8,
    'xtick.major.width':  0.8,
    'figure.dpi':         150,
})

# ── Layout ─────────────────────────────────────────────────────────────────────

n = len(CRITERIA)
bar_h  = 0.35
y_pos  = np.arange(n)

fig_w  = 9.5
fig_h  = max(6.0, n * 0.60 + 2.2)
fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor='white')
ax.set_facecolor('white')

# Alternating row shading
for i in range(n):
    if i % 2 == 0:
        ax.axhspan(i - 0.5, i + 0.5, color=_COND_BG, alpha=0.55, zorder=0, lw=0)

# Vertical grid lines
for x in range(0, 110, 20):
    ax.axvline(x, color=_GRID_CLR, lw=0.6, zorder=1)

# Bars
bars_pre  = ax.barh(y_pos + bar_h / 2, PRE1980,  height=bar_h,
                    color=_ERA_PRE,  alpha=0.90, zorder=2, label='Pre-1980 (n=13)')
bars_post = ax.barh(y_pos - bar_h / 2, POST2010, height=bar_h,
                    color=_ERA_POST, alpha=0.92, zorder=2, label='2010+ (n=20)')

# Percentage labels inside/outside bars
for bar, val in zip(bars_pre, PRE1980):
    w = bar.get_width()
    offset = 1.5
    ha = 'left'
    color_txt = _ERA_PRE if w < 12 else 'white'
    x_txt = w + offset if w < 12 else w - offset
    ha = 'left' if w < 12 else 'right'
    ax.text(x_txt, bar.get_y() + bar.get_height() / 2,
            f"{val}%", va='center', ha=ha, fontsize=8.0,
            color=color_txt, fontweight='bold')

for bar, val in zip(bars_post, POST2010):
    w = bar.get_width()
    offset = 1.5
    color_txt = _ERA_POST if w < 12 else 'white'
    x_txt = w + offset if w < 12 else w - offset
    ha = 'left' if w < 12 else 'right'
    ax.text(x_txt, bar.get_y() + bar.get_height() / 2,
            f"{val}%", va='center', ha=ha, fontsize=8.0,
            color=color_txt, fontweight='bold')

# ── Axes formatting ────────────────────────────────────────────────────────────

ax.set_yticks(y_pos)
ax.set_yticklabels(CRITERIA, fontsize=9.5)
ax.set_xlim(0, 115)
ax.set_xlabel("Studies meeting criterion (%)", fontsize=9.5, labelpad=6)
ax.set_xticks([0, 20, 40, 60, 80, 100])
ax.xaxis.set_tick_params(labelsize=8.5)

ax.spines['left'].set_color('#888888')
ax.spines['bottom'].set_color('#888888')
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3, width=0.8)

ax.invert_yaxis()

# ── Legend ────────────────────────────────────────────────────────────────────

pre_patch  = mpatches.Patch(color=_ERA_PRE,  label='Pre-1980  (n = 13)')
post_patch = mpatches.Patch(color=_ERA_POST, label='2010+  (n = 20)')
ax.legend(
    handles=[pre_patch, post_patch],
    loc='lower right', fontsize=9,
    framealpha=0.95, edgecolor='#bbbbbb',
    handlelength=1.4, handleheight=0.9,
)

# ── Title ─────────────────────────────────────────────────────────────────────

fig.suptitle(
    "Methodological Quality by Era: Psychedelic-Assisted Therapy for Alcohol Use Disorder",
    fontsize=11, fontweight='bold', y=0.99, va='top',
)

fig.tight_layout(rect=[0, 0, 1, 0.97])

# ── Save ──────────────────────────────────────────────────────────────────────

out_path = _BASE / 'figures' / 'Alcohol_MethQual_BarPlot.png'
out_path.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)
print(f"Bar plot written to: {out_path}")
