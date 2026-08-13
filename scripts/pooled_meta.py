"""
Random-effects pooling of the Tier 1 Hedges' g estimates across all conditions.

Produces the summary the manuscript reports in §3.3 (Benchmarking) and in the
"Preventive Psychedelic Intervention" row of Table 5: DerSimonian–Laird pooled
g with 95% CI, the equivalent odds ratio, heterogeneity (Q, tau-squared, I2),
the 95% prediction interval, and the leave-one-out range.

Inputs:
    tables/<Condition>_Tier1_HedgesG.xlsx   (output of tier1_hedges_g.py)

Output:
    tables/Tier1_PooledMeta.txt

Usage:
    python scripts/pooled_meta.py

Only rows with confidence != 'excluded' contribute; those are exactly the
trials plotted in figures/Unified_Tier1_ForestPlot.png.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

_BASE = Path(__file__).parent.parent

CONDITIONS = ['Alcohol', 'Opioid', 'Smoking']
OUTPUT = _BASE / 'tables' / 'Tier1_PooledMeta.txt'


def normal_sf(z: float) -> float:
    """Upper-tail standard normal probability."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def chi2_sf(x: float, df: int) -> float:
    """Upper-tail chi-squared probability, via the regularized incomplete gamma
    (Numerical Recipes gser/gcf). scipy is not a dependency of this project."""
    a, x2 = df / 2.0, x / 2.0
    if x2 <= 0:
        return 1.0
    if x2 < a + 1.0:                                   # series expansion
        term = total = 1.0 / a
        for n in range(1, 500):
            term *= x2 / (a + n)
            total += term
            if abs(term) < abs(total) * 1e-12:
                break
        return 1.0 - total * math.exp(-x2 + a * math.log(x2) - math.lgamma(a))
    b, c = x2 + 1.0 - a, 1e30                          # continued fraction
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h * math.exp(-x2 + a * math.log(x2) - math.lgamma(a))


def pool(g: np.ndarray, var: np.ndarray) -> dict:
    """DerSimonian–Laird random-effects pooling."""
    w_fixed = 1.0 / var
    q = float(np.sum(w_fixed * g ** 2) - np.sum(w_fixed * g) ** 2 / np.sum(w_fixed))
    df = len(g) - 1
    c = float(np.sum(w_fixed) - np.sum(w_fixed ** 2) / np.sum(w_fixed))
    tau2 = max(0.0, (q - df) / c) if c else 0.0

    w = 1.0 / (var + tau2)
    est = float(np.sum(w * g) / np.sum(w))
    se = float(math.sqrt(1.0 / np.sum(w)))
    z = est / se
    i2 = max(0.0, 100.0 * (q - df) / q) if q > 0 else 0.0

    # 95% prediction interval for a future trial, on the normal quantile — the
    # basis the published interval (-0.33 to 1.25) was computed on. The
    # Higgins-Thompson-Spiegelhalter t(k-2) version is wider (-0.40 to 1.32 at
    # k = 16); switching conventions is a decision for the authors, not a
    # side effect of making the number reproducible.
    pi_half = 1.96 * math.sqrt(tau2 + se ** 2)

    return {
        'k': len(g), 'g': est, 'se': se, 'z': z, 'p': 2 * normal_sf(abs(z)),
        'ci_lo': est - 1.96 * se, 'ci_hi': est + 1.96 * se,
        'q': q, 'df': df, 'q_p': chi2_sf(q, df), 'tau2': tau2, 'i2': i2,
        'pi_lo': est - pi_half, 'pi_hi': est + pi_half,
    }


def to_or(g: float) -> float:
    """Hedges' g to odds ratio via the logistic conversion (d = log(OR) x sqrt(3)/pi)."""
    return math.exp(g * math.pi / math.sqrt(3))


def load_tier1() -> pd.DataFrame:
    frames = []
    for short in CONDITIONS:
        path = _BASE / 'tables' / f'{short}_Tier1_HedgesG.xlsx'
        if not path.exists():
            raise SystemExit(f'ERROR: {path} not found — run run_pipeline.py first.')
        df = pd.read_excel(path)
        df['condition'] = short
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    return combined[combined.confidence != 'excluded'].reset_index(drop=True)


def main() -> None:
    df = load_tier1()
    g, var = df.g.to_numpy(float), df.var_g.to_numpy(float)
    res = pool(g, var)
    total_n = int(pd.to_numeric(df.N, errors='coerce').sum())

    loo = []
    for i in range(len(df)):
        mask = np.ones(len(df), bool)
        mask[i] = False
        loo.append((pool(g[mask], var[mask])['g'], df.study.iloc[i]))
    loo.sort()

    lines = [
        'Tier 1 random-effects pooling (DerSimonian–Laird)',
        f'Trials: {res["k"]}   Total N: {total_n:,}',
        '',
        f'Pooled Hedges g = {res["g"]:.2f} (95% CI {res["ci_lo"]:.2f}–{res["ci_hi"]:.2f}); '
        f'z = {res["z"]:.2f}, p = {res["p"]:.2e}',
        f'Equivalent odds ratio = {to_or(res["g"]):.2f} '
        f'({to_or(res["ci_lo"]):.2f}–{to_or(res["ci_hi"]):.2f})',
        '',
        f'Heterogeneity: Q = {res["q"]:.1f} on {res["df"]} df, p = {res["q_p"]:.2e}; '
        f'tau^2 = {res["tau2"]:.3f}; I^2 = {res["i2"]:.0f}%',
        f'95% prediction interval: {res["pi_lo"]:.2f} to {res["pi_hi"]:.2f}',
        '',
        f'Leave-one-out range: g = {loo[0][0]:.2f} (omitting {loo[0][1]}) '
        f'to g = {loo[-1][0]:.2f} (omitting {loo[-1][1]})',
        '',
        'Contributing trials:',
    ]
    for _, r in df.sort_values('g', ascending=False).iterrows():
        lines.append(f'  {r.study:<20} {r.condition:<8} {r.substance:<16} '
                     f'g = {r.g:+.3f}  (SE {r.se_g:.3f})  {r.confidence}')

    text = '\n'.join(lines)
    OUTPUT.write_text(text + '\n', encoding='utf-8')
    print(text)
    print(f'\nWritten to: {OUTPUT}')


if __name__ == '__main__':
    main()
