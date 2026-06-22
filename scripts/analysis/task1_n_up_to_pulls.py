#!/usr/bin/env python
"""A组: 任务1 (n_up-to-pulls) 全方法对比 — 方案1/2/3/4/CLT."""

import json as _json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from genshin_wish._constants import CHARACTER_POOL, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._gold import build_gold_pdf, get_gold_pdfs
from genshin_wish._dp_golds import _dp_golds_task1, golds_to_pulls
from genshin_wish.character import CharacterState, up_distribution

OUTPUT = Path("output/analysis/task1-n_up-to-pulls")
QUANTILES = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
DP_PULLS_MAX_N = 7
DP_PATH_MAX_N = 20

_p_cond = build_gold_pdf(CHARACTER_POOL)
_p_up = list(CAPTURE_RADIANCE_WIN_RATE)


# ---------------------------------------------------------------------------
# 方案1 (dp-pulls) — per-pull DP
# ---------------------------------------------------------------------------


def _dp_pulls_task1(n_uncertain: int, k_miss_start: int) -> np.ndarray:
    max_pulls = n_uncertain * 2 * CHARACTER_POOL.hard_pity + 1
    result = np.zeros(max_pulls + 1, dtype=np.float64)
    total_done = 0.0
    state: dict[tuple[int, int, int, int], float] = {
        (k_miss_start, 0, 0, 0): 1.0
    }

    for pull in range(1, max_pulls + 1):
        new_state: dict[tuple[int, int, int, int], float] = defaultdict(float)
        for (k, pity, nu, gflag), prob in state.items():
            gold_prob = _p_cond[pity + 1]
            new_state[(k, min(pity + 1, 89), nu, gflag)] += prob * (1.0 - gold_prob)
            if gflag:
                new_state[(k, 0, nu + 1, 0)] += prob * gold_prob
            else:
                pw = _p_up[k]
                new_state[(0, 0, nu + 1, 0)] += prob * gold_prob * pw
                if k < 3:
                    new_state[(k + 1, 0, nu, 1)] += prob * gold_prob * (1.0 - pw)

        done = 0.0
        remaining: dict[tuple[int, int, int, int], float] = defaultdict(float)
        for key, prob in new_state.items():
            _k, _pity, nu, gflag = key
            if nu >= n_uncertain and gflag == 0:
                done += prob
            else:
                remaining[key] += prob

        result[pull] = done
        total_done += done
        state = remaining
        if total_done > 1.0 - 1e-12:
            break

    return result / result.sum()


# ---------------------------------------------------------------------------
# Timing helper
# ---------------------------------------------------------------------------


def _metrics(pdf: np.ndarray, t_ms: float) -> dict:
    cdf = np.cumsum(pdf)
    return {
        "expected": float(np.sum(np.arange(len(pdf)) * pdf)),
        "quantiles": {q: int(np.searchsorted(cdf, q)) for q in QUANTILES},
        "time_ms": t_ms,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    n_range = list(range(1, 21)) + list(range(25, 101, 5)) + list(range(150, 501, 50))
    methods = ["dp-pulls", "dp-path", "dp-state", "dp-golds", "CLT"]
    data: dict[str, dict[str, dict]] = {m: {} for m in methods}

    for ni, n_up in enumerate(n_range):
        print(f"  n={n_up} ({ni+1}/{len(n_range)})", flush=True)
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)

        # --- dp-pulls ---
        if n_up <= DP_PULLS_MAX_N:
            t0 = time.perf_counter()
            pdf = _dp_pulls_task1(n_up, 0)
            t = (time.perf_counter() - t0) * 1000
            data["dp-pulls"][str(n_up)] = _metrics(pdf, t)
        else:
            data["dp-pulls"][str(n_up)] = {
                "expected": None, "quantiles": None, "time_ms": None
            }

        # --- dp-path ---
        if n_up <= DP_PATH_MAX_N:
            t0 = time.perf_counter()
            dist = up_distribution(state, n_up, method="dp-path")
            t = (time.perf_counter() - t0) * 1000
            data["dp-path"][str(n_up)] = {
                "expected": dist.expected,
                "quantiles": {q: dist.quantile(q) for q in QUANTILES},
                "time_ms": t,
            }
        else:
            data["dp-path"][str(n_up)] = {
                "expected": None, "quantiles": None, "time_ms": None
            }

        # --- dp-state ---
        t0 = time.perf_counter()
        dist = up_distribution(state, n_up, method="dp-state")
        t = (time.perf_counter() - t0) * 1000
        data["dp-state"][str(n_up)] = {
            "expected": dist.expected,
            "quantiles": {q: dist.quantile(q) for q in QUANTILES},
            "time_ms": t,
        }

        # --- dp-golds ---
        t0 = time.perf_counter()
        gold_probs = _dp_golds_task1(n_up, 0)
        dist = golds_to_pulls(gold_probs)
        t = (time.perf_counter() - t0) * 1000
        data["dp-golds"][str(n_up)] = {
            "expected": dist.expected,
            "quantiles": {q: dist.quantile(q) for q in QUANTILES},
            "time_ms": t,
        }

        # --- CLT ---
        t0 = time.perf_counter()
        dist = up_distribution(state, n_up, method="clt")
        t = (time.perf_counter() - t0) * 1000
        data["CLT"][str(n_up)] = {
            "expected": dist.expected,
            "quantiles": {q: dist.quantile(q) for q in QUANTILES},
            "time_ms": t,
        }

    # Save JSON
    (OUTPUT / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- Plots ---
    _plot_speed(data, n_range)
    _plot_clt_error(data, n_range)

    print(f"Done — {OUTPUT}")


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


def _plot_speed(data: dict, n_range: list[int]) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    # Speed (without dp-pulls)
    fig, ax = plt.subplots(figsize=(10, 6))
    for name in ["dp-path", "dp-state", "dp-golds", "CLT"]:
        ns = [n for n in n_range if data[name][str(n)]["time_ms"] is not None]
        times = [data[name][str(n)]["time_ms"] for n in ns]
        ax.plot(ns, times, "o-", markersize=4, label=name)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_title("Task 1 speed comparison")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUTPUT / "speed.png", dpi=200)
    plt.close(fig)

    # Detail (with dp-pulls, small n)
    fig, ax = plt.subplots(figsize=(10, 6))
    small_n = [n for n in n_range if n <= 20]
    for name in ["dp-pulls", "dp-path", "dp-state", "dp-golds", "CLT"]:
        ns = [n for n in small_n if data[name][str(n)]["time_ms"] is not None]
        times = [data[name][str(n)]["time_ms"] for n in ns]
        ax.plot(ns, times, "o-", markersize=4, label=name)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_title("Task 1 speed comparison (n≤20)")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUTPUT / "speed-detail.png", dpi=200)
    plt.close(fig)


def _plot_clt_error(data: dict, n_range: list[int]) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    colors = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    linestyles = [":", "--", "-", "-", "-", "--", ":"]

    # Absolute error
    fig, ax = plt.subplots(figsize=(12, 7))
    for qi, q in enumerate(QUANTILES):
        ns = n_range
        errors = []
        for n in ns:
            e = data["dp-state"][str(n)]["quantiles"][q] / n
            c = data["CLT"][str(n)]["quantiles"][q] / n
            errors.append(abs(e - c))
        ax.plot(ns, errors, color=colors[qi], linestyle=linestyles[qi],
                linewidth=2, label=f"{int(q * 100)}%")
    ax.set_title("Task 1 CLT absolute error (vs dp-state)", fontsize=14)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("error (pulls / UP)")
    ax.legend(loc="upper right", ncol=4, fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT / "accuracy-clt-abs.png", dpi=200)
    plt.close(fig)

    # Relative error
    fig, ax = plt.subplots(figsize=(12, 7))
    for qi, q in enumerate(QUANTILES):
        ns = n_range
        errors = []
        for n in ns:
            e = data["dp-state"][str(n)]["quantiles"][q] / n
            c = data["CLT"][str(n)]["quantiles"][q] / n
            errors.append(abs(e - c) / max(e, 1.0) * 100)
        ax.plot(ns, errors, color=colors[qi], linestyle=linestyles[qi],
                linewidth=2, label=f"{int(q * 100)}%")
    ax.set_title("Task 1 CLT relative error (vs dp-state)", fontsize=14)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("relative error (%)")
    ax.legend(loc="upper right", ncol=4, fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT / "accuracy-clt-rel.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
