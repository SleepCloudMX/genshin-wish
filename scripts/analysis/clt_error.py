#!/usr/bin/env python
"""Quantify CLT approximation error vs exact 4-state capture-radiance model.

Computes per-UP pull distributions for N=1..100 using exact iterative
convolution over 4 k_miss states, then compares against CLT at 7 key
quantiles. Exports plots and data.json.

DEPRECATED: superseded by task1_n_up_to_pulls.py (A组 benchmark).
Kept for reference only.
"""

import json as _json
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from scipy.stats import norm

from genshin_wish._constants import CHARACTER_POOL, STABLE_P, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._gold import get_gold_pdfs
from genshin_wish.long_term import _solve_exact
from genshin_wish.viz._base import setup_style

setup_style()

OUTPUT = Path("output/analysis/clt-error")
OUTPUT.mkdir(parents=True, exist_ok=True)

MAX_N = 100
START_N = 5
QUANTILES = [0.01, 0.10, 0.30, 0.50, 0.70, 0.90, 0.99]
QLABELS = ["1%", "10%", "30%", "50%", "70%", "90%", "99%"]
COLORS = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]

p_up = CAPTURE_RADIANCE_WIN_RATE
pdfs = get_gold_pdfs(CHARACTER_POOL)
p_gold = pdfs[1]
p_gold2 = np.convolve(p_gold, p_gold)


def exact_quantiles(max_n: int) -> dict[int, dict[float, float]]:
    results = _solve_exact(max_n, list(p_up), p_gold, p_gold2)
    return {n: {q: float(np.searchsorted(np.cumsum(results[n]), q)) for q in QUANTILES}
            for n in range(1, max_n + 1)}


def clt_moments():
    mu_1 = 0.0; m2_sum = 0.0
    for s, pi in enumerate(STABLE_P):
        mu_win = float(np.sum(np.arange(len(p_gold)) * p_gold))
        mu_loss = 2.0 * mu_win
        mu_s = p_up[s] * mu_win + (1 - p_up[s]) * mu_loss
        var_win = float(np.sum((np.arange(len(p_gold)) ** 2) * p_gold)) - mu_win**2
        m2_s = p_up[s] * (var_win + mu_win**2) + (1 - p_up[s]) * (2 * var_win + mu_loss**2)
        mu_1 += pi * mu_s
        m2_sum += pi * m2_s
    return mu_1, m2_sum - mu_1**2


MU_1, VAR_1 = clt_moments()


def clt_quantiles(max_n):
    STD_1 = np.sqrt(VAR_1)
    return {n: {q: float(n * MU_1 + np.sqrt(n) * STD_1 * norm.ppf(q)) for q in QUANTILES}
            for n in range(1, max_n + 1)}


# ---- Compute ----

print(f"Computing exact 4-state distribution (N=1..{MAX_N})...")
exact_q = exact_quantiles(MAX_N)
print(f"Computing CLT approximation (N=1..{MAX_N})...")
clt_q = clt_quantiles(MAX_N)

# ---- Pre-compute errors ----

ns = np.arange(1, MAX_N + 1)
abs_err: dict[float, np.ndarray] = {}
rel_err: dict[float, np.ndarray] = {}
for q in QUANTILES:
    epu = np.array([exact_q[n][q] / n for n in ns])
    cpu = np.array([clt_q[n][q] / n for n in ns])
    abs_err[q] = np.abs(epu - cpu)
    rel_err[q] = abs_err[q] / np.maximum(epu, 1.0) * 100

# ---- Figure 1: Absolute error ----

tick_ns = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
plot_ns = ns[START_N - 1:]

fig1, ax1 = plt.subplots(figsize=(14, 7))
for qi, (q, label, color) in enumerate(zip(QUANTILES, QLABELS, COLORS)):
    ls = ":" if q in (0.01, 0.99) else "--" if q in (0.10, 0.90) else "-"
    ax1.plot(plot_ns, abs_err[q][START_N - 1:], color=color, linestyle=ls, linewidth=2, label=label)
ax1.set_title("绝对误差 |exact - CLT| (抽 / UP)", fontsize=14)
ax1.set_xlabel("UP 数 N", fontsize=12)
ax1.set_ylabel("误差 (抽 / UP)", fontsize=12)
ax1.legend(loc="upper right", ncol=4, fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_xticks(tick_ns)
fig1.tight_layout()
fig1.savefig(OUTPUT / "clt-error-abs.png", dpi=200)
plt.close(fig1)
print(f"Saved {OUTPUT / 'clt-error-abs.png'}")

# ---- Figure 2: Relative error ----

fig2, ax2 = plt.subplots(figsize=(14, 7))
for qi, (q, label, color) in enumerate(zip(QUANTILES, QLABELS, COLORS)):
    ls = ":" if q in (0.01, 0.99) else "--" if q in (0.10, 0.90) else "-"
    ax2.plot(plot_ns, rel_err[q][START_N - 1:], color=color, linestyle=ls, linewidth=2, label=label)
ax2.set_title("相对误差 |exact - CLT| / exact (%)", fontsize=14)
ax2.set_xlabel("UP 数 N", fontsize=12)
ax2.set_ylabel("相对误差 (%)", fontsize=12)
ax2.axhline(2.0, color="gray", linestyle="--", alpha=0.5, linewidth=1)
ax2.text(MAX_N * 0.95, 2.2, "2%", ha="right", fontsize=9, color="gray")
ax2.legend(loc="upper right", ncol=4, fontsize=9)
ax2.grid(True, alpha=0.3)
ax2.set_xticks(tick_ns)
fig2.tight_layout()
fig2.savefig(OUTPUT / "clt-error-rel.png", dpi=200)
plt.close(fig2)
print(f"Saved {OUTPUT / 'clt-error-rel.png'}")

# ---- Export data.json ----

export_ns = [5, 10, 20, 50, 100]
per_up = {}
for n in export_ns:
    per_up[str(n)] = {
        "exact": {f"{q:.0%}": round(exact_q[n][q] / n, 1) for q in QUANTILES},
        "clt":   {f"{q:.0%}": round(clt_q[n][q] / n, 1) for q in QUANTILES},
    }

convergence = {}
for q, label in zip(QUANTILES, QLABELS):
    for n in ns:
        if rel_err[q][n - 1] < 2.0:
            convergence[label] = {"N": int(n), "rel_err_pct": round(float(rel_err[q][n - 1]), 1),
                                   "abs_err_per_up": round(float(abs_err[q][n - 1]), 2)}
            break

data = {
    "steady_state": {"per_up_expected": round(MU_1, 1), "per_up_std": round(np.sqrt(VAR_1), 1)},
    "convergence_rel_2pct": convergence,
    "per_up_quantiles": per_up,
    "parameters": {
        "character_pool": {"base_rate": 0.006, "soft_pity_start": 74, "hard_pity": 90, "step": 0.06},
        "capture_radiance_win_rates": p_up,
        "stable_p": STABLE_P,
    },
}

(OUTPUT / "data.json").write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {OUTPUT / 'data.json'}")
