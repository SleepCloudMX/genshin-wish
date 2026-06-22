#!/usr/bin/env python
"""A组: 任务1 (n_up-to-pulls) 全方法对比 — 方案1/2/3/4/CLT."""

import json as _json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import trim_mean

from genshin_wish._constants import CHARACTER_POOL, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._gold import build_gold_pdf, get_gold_pdfs
from genshin_wish._dp_golds import _dp_golds_task1, golds_to_pulls
from genshin_wish.character import CharacterState, up_distribution

OUTPUT = Path("output/analysis/task1-n_up-to-pulls")
QUANTILES = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
DP_PULLS_MAX_N = 7
DP_PATH_MAX_N = 20
TRIM_FRAC = 0.2  # trim 20% from each tail
ERROR_BAR = "minmax"  # "minmax" | "std3" | "none"

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
# Timing helpers
# ---------------------------------------------------------------------------


def _timeit(fn, n_runs: int = 50) -> dict:
    """Run *fn* n_runs times, return trimmed mean + min/max/std."""
    times: list[float] = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    arr = np.array(times)
    return {
        "time_ms": float(trim_mean(arr, TRIM_FRAC)),
        "time_min": float(np.min(arr)),
        "time_max": float(np.max(arr)),
        "time_std": float(np.std(arr)),
        "n_runs": n_runs,
    }


def _dist_metrics(dist, timing: dict) -> dict:
    return {
        "expected": dist.expected,
        "quantiles": {q: dist.quantile(q) for q in QUANTILES},
        **timing,
    }


def _pdf_metrics(pdf: np.ndarray, timing: dict) -> dict:
    cdf = np.cumsum(pdf)
    return {
        "expected": float(np.sum(np.arange(len(pdf)) * pdf)),
        "quantiles": {q: int(np.searchsorted(cdf, q)) for q in QUANTILES},
        **timing,
    }


def _null_metrics() -> dict:
    return {
        "expected": None, "quantiles": None,
        "time_ms": None, "time_min": None, "time_max": None,
        "time_std": None, "n_runs": 0,
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

        # --- dp-pulls (11 runs) ---
        if n_up <= DP_PULLS_MAX_N:
            def _run_pulls():
                _dp_pulls_task1(n_up, 0)
            timing = _timeit(_run_pulls, n_runs=11)
            pdf = _dp_pulls_task1(n_up, 0)
            data["dp-pulls"][str(n_up)] = _pdf_metrics(pdf, timing)
        else:
            data["dp-pulls"][str(n_up)] = _null_metrics()

        # --- dp-path (50 runs — fast) ---
        if n_up <= DP_PATH_MAX_N:
            def _run_path():
                up_distribution(state, n_up, method="dp-path")
            timing = _timeit(_run_path, n_runs=50)
            dist = up_distribution(state, n_up, method="dp-path")
            data["dp-path"][str(n_up)] = _dist_metrics(dist, timing)
        else:
            data["dp-path"][str(n_up)] = _null_metrics()

        # --- dp-state (11 at large n, 50 otherwise) ---
        nr_state = 11 if n_up >= 150 else 50
        def _run_state():
            up_distribution(state, n_up, method="dp-state")
        timing = _timeit(_run_state, n_runs=nr_state)
        dist = up_distribution(state, n_up, method="dp-state")
        data["dp-state"][str(n_up)] = _dist_metrics(dist, timing)

        # --- dp-golds (50 runs — fast) ---
        def _run_golds():
            gp = _dp_golds_task1(n_up, 0)
            golds_to_pulls(gp)
        timing = _timeit(_run_golds, n_runs=50)
        gp = _dp_golds_task1(n_up, 0)
        dist = golds_to_pulls(gp)
        data["dp-golds"][str(n_up)] = _dist_metrics(dist, timing)

        # --- CLT (50 runs — fast) ---
        def _run_clt():
            up_distribution(state, n_up, method="clt")
        timing = _timeit(_run_clt, n_runs=50)
        dist = up_distribution(state, n_up, method="clt")
        data["CLT"][str(n_up)] = _dist_metrics(dist, timing)

    # Save JSON
    (OUTPUT / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- Plots ---
    _plot_speed(data, n_range)
    _plot_clt_error(data, n_range)
    _plot_clt_per_n(data, n_range)

    print(f"Done — {OUTPUT}")


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


def _plot_speed(data: dict, n_range: list[int], error_bar: str = "") -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    eb = error_bar or ERROR_BAR

    def _draw_speed(ax, names, ns_filter, show_band=True):
        for name in names:
            ns = [n for n in n_range if ns_filter(n) and data[name][str(n)]["time_ms"] is not None]
            times = [data[name][str(n)]["time_ms"] for n in ns]
            line = ax.plot(ns, times, "o-", markersize=4, label=name)[0]
            if show_band and eb != "none":
                if eb == "std3":
                    t_std = [data[name][str(n)].get("time_std", 0) for n in ns]
                    lo = [max(0, t - 3 * s) for t, s in zip(times, t_std)]
                    hi = [t + 3 * s for t, s in zip(times, t_std)]
                else:  # minmax
                    lo = [data[name][str(n)].get("time_min", t) for n, t in zip(ns, times)]
                    hi = [data[name][str(n)].get("time_max", t) for n, t in zip(ns, times)]
                ax.fill_between(ns, lo, hi, alpha=0.15, color=line.get_color())

    # Full range (without dp-pulls)
    fig, ax = plt.subplots(figsize=(10, 6))
    _draw_speed(ax, ["dp-path", "dp-state", "dp-golds", "CLT"], lambda n: True)
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
    _draw_speed(ax, ["dp-pulls", "dp-path", "dp-state", "dp-golds", "CLT"],
                lambda n: n <= 20, show_band=False)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_title("Task 1 speed comparison (n≤20)")
    ax.set_yscale("log")
    ax.set_xticks([n for n in small_n if n % 2 == 0])
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUTPUT / "speed-detail.png", dpi=200)
    plt.close(fig)


def _q(entry: dict, key: float) -> float:
    """Get quantile value, handling float/string keys from JSON round-trip."""
    qs = entry["quantiles"]
    return qs.get(key, qs.get(str(key), 0))


def _plot_clt_error(data: dict, n_range: list[int]) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    colors = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    linestyles = [":", "--", "-", "-", "-", "--", ":"]

    n_early = [n for n in n_range if n <= 20]
    n_late = [n for n in n_range if n >= 10]

    abs_dir = OUTPUT / "accuracy-clt-abs"
    abs_dir.mkdir(parents=True, exist_ok=True)
    for label, ns, filename in [
        ("1–20", n_early, "early.png"),
        ("10–500", n_late, "late.png"),
    ]:
        fig, ax = plt.subplots(figsize=(12, 7))
        for qi, q in enumerate(QUANTILES):
            errors = []
            for n in ns:
                e = _q(data["dp-state"][str(n)], q) / n
                c = _q(data["CLT"][str(n)], q) / n
                errors.append(abs(e - c))
            ax.plot(ns, errors, color=colors[qi], linestyle=linestyles[qi],
                    linewidth=2, label=f"{int(q * 100)}%")
        ax.set_title(f"Task 1 CLT absolute error (n={label})", fontsize=14)
        ax.set_xlabel("$n_\\text{up}$")
        ax.set_ylabel("error (pulls / UP)")
        ax.legend(loc="upper right", ncol=4, fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(abs_dir / filename, dpi=200)
        plt.close(fig)

    rel_dir = OUTPUT / "accuracy-clt-rel"
    rel_dir.mkdir(parents=True, exist_ok=True)
    for label, ns, filename in [
        ("1–20", n_early, "early.png"),
        ("10–500", n_late, "late.png"),
    ]:
        fig, ax = plt.subplots(figsize=(12, 7))
        for qi, q in enumerate(QUANTILES):
            errors = []
            for n in ns:
                e = _q(data["dp-state"][str(n)], q) / n
                c = _q(data["CLT"][str(n)], q) / n
                errors.append(abs(e - c) / max(e, 1.0) * 100)
            ax.plot(ns, errors, color=colors[qi], linestyle=linestyles[qi],
                    linewidth=2, label=f"{int(q * 100)}%")
        ax.set_title(f"Task 1 CLT relative error (n={label})", fontsize=14)
        ax.set_xlabel("$n_\\text{up}$")
        ax.set_ylabel("relative error (%)")
        ax.legend(loc="upper right", ncol=4, fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(rel_dir / filename, dpi=200)
        plt.close(fig)


def _plot_clt_per_n(data: dict, n_range: list[int]) -> None:
    """Per-UP absolute error divided by n_up (error convergence rate)."""
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    colors = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    linestyles = [":", "--", "-", "-", "-", "--", ":"]

    n_early = [n for n in n_range if n <= 20]
    n_late = [n for n in n_range if n >= 10]

    out_dir = OUTPUT / "accuracy-clt-abs-per-n_up"
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, ns, filename in [
        ("1–20", n_early, "early.png"),
        ("10–500", n_late, "late.png"),
    ]:
        fig, ax = plt.subplots(figsize=(12, 7))
        for qi, q in enumerate(QUANTILES):
            errors = []
            for n in ns:
                e = _q(data["dp-state"][str(n)], q) / n
                c = _q(data["CLT"][str(n)], q) / n
                errors.append(abs(e - c) / n)
            ax.plot(ns, errors, color=colors[qi], linestyle=linestyles[qi],
                    linewidth=2, label=f"{int(q * 100)}%")
        ax.set_title(f"Task 1 CLT per-UP error / n_up (n={label})", fontsize=14)
        ax.set_xlabel("$n_\\text{up}$")
        ax.set_ylabel("error (pulls / UP) / $n_\\text{up}$")
        ax.legend(loc="upper right", ncol=4, fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / filename, dpi=200)
        plt.close(fig)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--plot-only", action="store_true",
                   help="Skip computation, regenerate plots from data.json")
    p.add_argument("--error-bar", choices=["minmax", "std3", "none"],
                   default="minmax",
                   help="Error bar style (default: minmax)")
    args = p.parse_args()

    if args.plot_only:
        print("Plot-only mode — loading data.json ...", flush=True)
        data = _json.loads((OUTPUT / "data.json").read_text(encoding="utf-8"))
        n_range = [int(k) for k in data["dp-state"].keys()]
        n_range.sort()
        _plot_speed(data, n_range, error_bar=args.error_bar)
        _plot_clt_error(data, n_range)
        _plot_clt_per_n(data, n_range)
        print(f"Plots regenerated — {OUTPUT}")
    else:
        ERROR_BAR = args.error_bar
        main()
