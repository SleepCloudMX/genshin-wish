#!/usr/bin/env python
"""Compare solvers for long-term UP distribution: accuracy, speed, convergence.

Solves:
  A — 55/45 naive convolution
  C — 55/45 FFT iteration
  D — 55/45 CLT
  E — 4-state capture radiance exact (ground truth, N<=20)
  F — 4-state capture radiance CLT

DEPRECATED: superseded by task1_n_up_to_pulls.py (A组 benchmark).
Kept for reference only.
"""

import time
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from scipy.fft import fft, ifft
from scipy.stats import norm

from genshin_wish._constants import CHARACTER_POOL, STABLE_P, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._gold import get_gold_pdfs
from genshin_wish.long_term import _solve_exact
from genshin_wish.viz._base import setup_style

setup_style()

OUTPUT = Path("output/analysis/solver-compare")
OUTPUT.mkdir(parents=True, exist_ok=True)

ACC_N = 100      # accuracy and convergence range
SPEED_NS = [1, 5, 10, 20, 50, 100]
QUANTILES = [0.01, 0.10, 0.30, 0.50, 0.70, 0.90, 0.99]
QLABELS = ["1%", "10%", "30%", "50%", "70%", "90%", "99%"]
COLORS = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]

p_up = CAPTURE_RADIANCE_WIN_RATE
pdfs = get_gold_pdfs(CHARACTER_POOL)
p_gold = pdfs[1]


def _quantiles(cdf, max_len=None):
    if max_len:
        cdf = cdf[:max_len]
    return {q: float(np.searchsorted(cdf, q)) for q in QUANTILES}


# ---- A: 55/45 naive ----

p_up_single = 0.45 * np.convolve(p_gold, p_gold).copy()
p_up_single[:len(p_gold)] += 0.55 * p_gold


def solve_naive_conv(N):
    pdf = np.array([1.0], dtype=np.float64)
    result = {}
    for n in range(1, N + 1):
        pdf = np.convolve(pdf, p_up_single)
        result[n] = _quantiles(np.cumsum(pdf))
    return result


# ---- C: 55/45 FFT ----

def solve_fft_iter(N):
    L = 180 * N + 1
    phi = fft(p_up_single, n=L)
    result = {}
    for n in range(1, N + 1):
        pdf = np.real(ifft(phi ** n))
        result[n] = _quantiles(np.cumsum(pdf), max_len=L)
    return result


# ---- D: 55/45 CLT ----

mu_55 = float(np.sum(np.arange(len(p_up_single)) * p_up_single))
var_55 = float(np.sum((np.arange(len(p_up_single)) ** 2) * p_up_single)) - mu_55**2


def solve_clt_55(N):
    result = {}
    for n in range(1, N + 1):
        mu_n = n * mu_55
        std_n = np.sqrt(n * var_55)
        result[n] = {q: float(norm.ppf(q, mu_n, std_n)) for q in QUANTILES}
    return result


# ---- E: 4-state exact ----

p_gold2 = np.convolve(p_gold, p_gold)


def solve_4state_exact(N):
    results = _solve_exact(N, list(p_up), p_gold, p_gold2)
    return {n: _quantiles(np.cumsum(results[n])) for n in range(1, N + 1)}


# ---- F: 4-state CLT ----

def _clt_4state_moments():
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


MU_4, VAR_4 = _clt_4state_moments()


def solve_clt_4state(N):
    result = {}
    for n in range(1, N + 1):
        mu_n = n * MU_4
        std_n = np.sqrt(n * VAR_4)
        result[n] = {q: float(norm.ppf(q, mu_n, std_n)) for q in QUANTILES}
    return result


# ============ Compute ============

solvers = {"A": solve_naive_conv, "C": solve_fft_iter, "D": solve_clt_55,
           "E": solve_4state_exact, "F": solve_clt_4state}

# --- Full data (N=1..100, all solvers) ---
print(f"Computing all solvers (N=1..{ACC_N})...")
acc_data = {}
for name, fn in solvers.items():
    t0 = time.perf_counter()
    acc_data[name] = fn(ACC_N)
    print(f"  {name}: {time.perf_counter()-t0:.2f}s")

# --- Speed benchmarks ---
print(f"Speed: benchmarking N={SPEED_NS}...")
speed_data: dict[str, list[float]] = {name: [] for name in solvers}
for n in SPEED_NS:
    for name, fn in solvers.items():
        runs = []
        for _ in range(3):
            t0 = time.perf_counter()
            fn(n)
            runs.append(time.perf_counter() - t0)
        speed_data[name].append(np.median(runs) * 1000)

exact_q = acc_data["E"]

# ============ Figure 1: Accuracy A vs E (N=5..100) ============

ns = np.arange(1, ACC_N + 1)
tick_ns = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

fig, ax = plt.subplots(figsize=(14, 7))

for qi, (q, label, color) in enumerate(zip(QUANTILES, QLABELS, COLORS)):
    ls = ":" if q in (0.01, 0.99) else "--" if q in (0.10, 0.90) else "-"
    err = np.array([abs(acc_data["A"][n][q] / n - exact_q[n][q] / n) for n in ns])
    ax.plot(ns[4:], err[4:], color=color, linestyle=ls, linewidth=2, label=label)

ax.set_title("A (55/45 naive) vs E (4-state exact), N=5..100", fontsize=14)
ax.set_xlabel("UP 数 N", fontsize=12)
ax.set_ylabel("绝对误差 (抽 / UP)", fontsize=12)
ax.legend(loc="upper right", ncol=4, fontsize=9)
ax.grid(True, alpha=0.3)
ax.set_xticks(tick_ns)
fig.tight_layout()
fig.savefig(OUTPUT / "accuracy-model.png", dpi=200)
plt.close(fig)
print(f"Saved {OUTPUT / 'accuracy-model.png'}")

# ============ Figure 2: Convergence (median per UP, N=1..100) ============

fig, ax = plt.subplots(figsize=(14, 7))

styles = {"A": ("#ff7f0e", "--"), "C": ("#2ca02c", "-."), "D": ("#d62728", ":"),
          "F": ("#1f77b4", "-")}

for name, (color, ls) in styles.items():
    med = [acc_data[name][n][0.50] / n for n in ns]
    ax.plot(ns, med, color=color, linestyle=ls, linewidth=1.5, label=name)

# E (exact) as scatter overlay
e_med = [exact_q[n][0.50] / n for n in ns]
ax.scatter(ns, e_med, color="#1f77b4", s=15, zorder=10, label="E (exact)")

ax.axhline(MU_4, color="gray", linestyle=":", alpha=0.5, linewidth=1)
ax.text(ACC_N * 0.95, MU_4 + 0.3, f"{MU_4:.1f}", ha="right", fontsize=9, color="gray")

ax.set_title("各方案中位数收敛 (每 UP 平均抽数 vs N)", fontsize=14)
ax.set_xlabel("UP 数 N", fontsize=12)
ax.set_ylabel("每 UP 平均抽数", fontsize=12)
ax.legend(loc="upper right", ncol=3, fontsize=9)
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(OUTPUT / "convergence.png", dpi=200)
plt.close(fig)
print(f"Saved {OUTPUT / 'convergence.png'}")

# ============ Figure 3: Speed ============

fig, ax = plt.subplots(figsize=(14, 8))
st = {"A": "o-", "C": "^-", "D": "d:", "E": "p-", "F": "h--"}
for name in ["A", "C", "D", "E", "F"]:
    ax.plot(SPEED_NS, speed_data[name], st[name], linewidth=2, markersize=8, label=name)

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_title("Solver speed comparison (N=1..100)", fontsize=14)
ax.set_xlabel("UP 数 N", fontsize=12)
ax.set_ylabel("耗时 (ms)", fontsize=12)
ax.legend(loc="upper left", fontsize=10)
ax.grid(True, alpha=0.3, which="both")
ax.set_xticks(SPEED_NS)
ax.set_xticklabels([str(n) for n in SPEED_NS])
fig.tight_layout()
fig.savefig(OUTPUT / "speed-comparison.png", dpi=200)
plt.close(fig)
print(f"Saved {OUTPUT / 'speed-comparison.png'}")

# ============ Export data.json ============

import json as _json

# Per-UP quantile values for A and E at N=5,10,20,50,100
export_ns = [5, 10, 20, 50, 100]
per_up = {}
for n in export_ns:
    per_up[str(n)] = {
        "A": {f"{q:.0%}": round(acc_data["A"][n][q] / n, 1) for q in QUANTILES},
        "E": {f"{q:.0%}": round(exact_q[n][q] / n, 1) for q in QUANTILES},
    }

speed_export = {str(n): {name: round(speed_data[name][ni], 1) for name in ["A", "C", "D", "E", "F"]}
                for ni, n in enumerate(SPEED_NS)}

data = {
    "steady_state": {"per_up_expected": round(MU_4, 1), "per_up_std": round(np.sqrt(VAR_4), 1)},
    "speed_ms": speed_export,
    "per_up_quantiles": per_up,
    "models": {
        "A": "55/45 naive convolution",
        "C": "55/45 FFT iteration",
        "D": "55/45 CLT (normal approx)",
        "E": "4-state capture radiance exact",
        "F": "4-state capture radiance CLT",
    },
    "parameters": {
        "character_pool": {"base_rate": 0.006, "soft_pity_start": 74, "hard_pity": 90, "step": 0.06},
        "capture_radiance_win_rates": [0.50009, 0.54800, 0.59150, 1.0],
        "stable_p": [0.550404, 0.274707, 0.124167, 0.0507224],
    },
}

(OUTPUT / "data.json").write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {OUTPUT / 'data.json'}")
