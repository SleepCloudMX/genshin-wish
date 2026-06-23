#!/usr/bin/env python
"""A组: 任务1 (n_up-to-pulls) — 全方法速度与精度对比.

对比 dp-pulls / dp-path / dp-state / dp-golds / CLT 在 n=1..500 的性能，
输出 speed.png、speed-detail.png、accuracy-clt-abs/、accuracy-clt-rel/、
accuracy-clt-abs-per-n_up/ 及 data.json。

使用示例::

    # 默认参数 (fast=50 runs, slow=11 runs, trim=0.2)
    python scripts/analysis/task1_n_up_to_pulls.py

    # 自定义运行次数
    python scripts/analysis/task1_n_up_to_pulls.py --n-runs-fast 100 --n-runs-slow 20

    # 只重新绘图 (不重跑计算)
    python scripts/analysis/task1_n_up_to_pulls.py --plot-only --trim 0.3 --error-bar std3

    # 拟合 & 标注斜率
    python scripts/analysis/task1_n_up_to_pulls.py --plot-only --fit
"""

import json as _json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit
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
N_RUNS_FAST = 50  # runs for fast solvers
N_RUNS_SLOW = 11  # runs for slow solvers (dp-pulls, dp-state n≥150)
FIT = False  # draw fit lines + slope annotations on speed.png

METHOD_COLORS = {
    "dp-pulls": "#d62728",  # red
    "dp-path":  "#ff7f0e",  # orange
    "dp-state": "#1f77b4",  # blue
    "dp-golds": "#2ca02c",  # green
    "CLT":      "#9467bd",  # purple
}

_p_cond = build_gold_pdf(CHARACTER_POOL)
_p_up = list(CAPTURE_RADIANCE_WIN_RATE)

import matplotlib
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.set_loglevel("error")

from genshin_wish.viz._base import setup_style
setup_style()


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
    """Run *fn* n_runs times, return trimmed mean + raw timings."""
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
        "time_all": times,
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
        "time_std": None, "time_all": [], "n_runs": 0,
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
            def _run_pulls():
                _dp_pulls_task1(n_up, 0)
            timing = _timeit(_run_pulls, n_runs=N_RUNS_SLOW)
            pdf = _dp_pulls_task1(n_up, 0)
            data["dp-pulls"][str(n_up)] = _pdf_metrics(pdf, timing)
        else:
            data["dp-pulls"][str(n_up)] = _null_metrics()

        # --- dp-path ---
        if n_up <= DP_PATH_MAX_N:
            def _run_path():
                up_distribution(state, n_up, method="dp-path")
            timing = _timeit(_run_path, n_runs=N_RUNS_FAST)
            dist = up_distribution(state, n_up, method="dp-path")
            data["dp-path"][str(n_up)] = _dist_metrics(dist, timing)
        else:
            data["dp-path"][str(n_up)] = _null_metrics()

        # --- dp-state ---
        nr_state = N_RUNS_SLOW if n_up >= 150 else N_RUNS_FAST
        def _run_state():
            up_distribution(state, n_up, method="dp-state")
        timing = _timeit(_run_state, n_runs=nr_state)
        dist = up_distribution(state, n_up, method="dp-state")
        data["dp-state"][str(n_up)] = _dist_metrics(dist, timing)

        # --- dp-golds ---
        def _run_golds():
            gp = _dp_golds_task1(n_up, 0)
            golds_to_pulls(gp)
        timing = _timeit(_run_golds, n_runs=N_RUNS_FAST)
        gp = _dp_golds_task1(n_up, 0)
        dist = golds_to_pulls(gp)
        data["dp-golds"][str(n_up)] = _dist_metrics(dist, timing)

        # --- CLT ---
        def _run_clt():
            up_distribution(state, n_up, method="clt")
        timing = _timeit(_run_clt, n_runs=N_RUNS_FAST)
        dist = up_distribution(state, n_up, method="clt")
        data["CLT"][str(n_up)] = _dist_metrics(dist, timing)

    # Save JSON
    (OUTPUT / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- Plots ---
    _plot_speed(data, n_range, fit=FIT)
    _plot_clt_error(data, n_range)
    _plot_clt_per_n(data, n_range)

    print(f"Done — {OUTPUT}")


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


def _trimmed_stats(raw: list[float], trim_frac: float) -> dict:
    """Return {mean, min, max, std} from the trimmed subset of *raw*."""
    arr = np.sort(np.array(raw))
    n = len(arr)
    n_cut = int(n * trim_frac)
    if n_cut * 2 >= n:
        n_cut = (n - 1) // 2
    trimmed = arr[n_cut : n - n_cut]
    return {
        "mean": float(np.mean(trimmed)),
        "min": float(np.min(trimmed)),
        "max": float(np.max(trimmed)),
        "std": float(np.std(trimmed)),
    }


def _plot_speed(data: dict, n_range: list[int], error_bar: str = "",
                trim_frac: float = 0.0, fit: bool = False) -> None:
    from matplotlib import pyplot as plt
    plt.rcParams['axes.unicode_minus'] = False

    eb = error_bar or ERROR_BAR
    trim = trim_frac or TRIM_FRAC

    def _draw_speed(ax, names, ns_filter, show_band=True):
        for name in names:
            ns = [n for n in n_range if ns_filter(n) and data[name][str(n)]["time_ms"] is not None]
            times = []
            los = []
            his = []
            for n in ns:
                raw = data[name][str(n)].get("time_all")
                if raw and len(raw) > 0:
                    stats = _trimmed_stats(raw, trim)
                    times.append(stats["mean"])
                    los.append(stats["min"])
                    his.append(stats["max"])
                    if eb == "std3":
                        los[-1] = max(0, stats["mean"] - 3 * stats["std"])
                        his[-1] = stats["mean"] + 3 * stats["std"]
                else:
                    times.append(data[name][str(n)]["time_ms"])
                    los.append(data[name][str(n)].get("time_min", times[-1]))
                    his.append(data[name][str(n)].get("time_max", times[-1]))
            line = ax.plot(ns, times, "o-", markersize=4, label=name,
                          color=METHOD_COLORS.get(name))[0]
            if show_band and eb != "none":
                ax.fill_between(ns, los, his, alpha=0.15, color=line.get_color())

    # Full range
    fig, ax = plt.subplots(figsize=(10, 6))
    methods = ["dp-pulls", "dp-path", "dp-state", "dp-golds", "CLT"]
    _draw_speed(ax, methods, lambda n: True)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_title("Task 1 speed comparison")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    if fit:
        _add_fit_lines(ax, data, n_range, methods)
    fig.tight_layout()
    fig.savefig(OUTPUT / "speed.png", dpi=200)
    plt.close(fig)

    # Detail (with dp-pulls, small n)
    fig, ax = plt.subplots(figsize=(10, 6))
    small_n = [n for n in n_range if n <= 20]
    _draw_speed(ax, ["dp-pulls", "dp-path", "dp-state", "dp-golds", "CLT"],
                lambda n: n <= 20)
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


FIT_N_MIN = 10  # dp-golds fit starts from this n


def _add_fit_lines(ax, data: dict, n_range: list[int], methods: list[str]) -> None:
    """Draw dashed fit lines with slope annotations on log-log axes."""
    for name in methods:
        ns_all = np.array([n for n in n_range if data[name][str(n)]["time_ms"] is not None])
        times_all = np.array([data[name][str(n)]["time_ms"] for n in ns_all])

        if name == "dp-path":
            # exp(a * n + b) + c  — seed from log-linear fit (c=0)
            c0 = np.polyfit(ns_all, np.log(np.maximum(times_all, 1e-9)), 1)
            p0 = [c0[0], c0[1], 0.0]
            bounds = ([0, -np.inf, 0], [np.inf, np.inf, times_all[0]])
            popt, _ = curve_fit(_exp_offset, ns_all, times_all, p0=p0,
                                bounds=bounds, method="trf", maxfev=10000)
            a, b, c = popt
            mask = ns_all >= 7
            ns_line = np.linspace(ns_all[mask][0], ns_all[-1], 200)
            times_line = _exp_offset(ns_line, a, b, c)
            label = "O(2ⁿ)"
            xytext = (4, 0)
            va = "center"
        else:
            # power law: log t = k * log n + b
            if name in ("dp-golds", "dp-state"):
                mask = ns_all >= FIT_N_MIN
                ns_fit = ns_all[mask]
                ts_fit = times_all[mask]
                ns_start = ns_fit[0]
            else:
                ns_fit = ns_all
                ts_fit = times_all
                ns_start = ns_all[0]
            coeffs = np.polyfit(np.log(ns_fit), np.log(ts_fit), 1)
            k, b = coeffs
            ns_line = np.linspace(ns_start, ns_all[-1], 2)
            times_line = np.exp(b + k * np.log(ns_line))
            label = f"k≈{k:.3f}"
            xytext = (0, -8)
            va = "top"

        color = METHOD_COLORS.get(name)
        ax.plot(ns_line, times_line, "--", color=color, lw=1, alpha=0.35)
        ax.annotate(label, xy=(ns_line[-1], times_line[-1]),
                    xytext=xytext, textcoords="offset points",
                    fontsize=7, color=color, va=va, alpha=0.65)


def _exp_offset(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """exp(a * x + b) + c"""
    return np.exp(a * x + b) + c


def _q(entry: dict, key: float) -> float:
    """Get quantile value, handling float/string keys from JSON round-trip."""
    qs = entry["quantiles"]
    return qs.get(key, qs.get(str(key), 0))


def _plot_clt_error(data: dict, n_range: list[int]) -> None:
    from matplotlib import pyplot as plt
    plt.rcParams['axes.unicode_minus'] = False

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
                e = _q(data["dp-state"][str(n)], q)
                c = _q(data["CLT"][str(n)], q)
                errors.append(abs(e - c))
            ax.plot(ns, errors, color=colors[qi], linestyle=linestyles[qi],
                    linewidth=2, label=f"{int(q * 100)}%")
        ax.set_title(f"Task 1 CLT absolute error (n={label})", fontsize=14)
        ax.set_xlabel("$n_\\text{up}$")
        ax.set_ylabel("error (pulls)")
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
                e = _q(data["dp-state"][str(n)], q)
                c = _q(data["CLT"][str(n)], q)
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
    """CLT per-UP absolute error (pulls divided by n_up)."""
    from matplotlib import pyplot as plt
    plt.rcParams['axes.unicode_minus'] = False

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
                errors.append(abs(e - c))
            ax.plot(ns, errors, color=colors[qi], linestyle=linestyles[qi],
                    linewidth=2, label=f"{int(q * 100)}%")
        ax.set_title(f"Task 1 CLT per-UP absolute error (n={label})", fontsize=14)
        ax.set_xlabel("$n_\\text{up}$")
        ax.set_ylabel("error (pulls / UP)")
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
    p.add_argument("--trim", type=float, default=0.2,
                   help="Trim fraction for trimmed mean (default: 0.2)")
    p.add_argument("--n-runs-fast", type=int, default=50,
                   help="Runs for fast solvers (default: 50)")
    p.add_argument("--n-runs-slow", type=int, default=11,
                   help="Runs for slow solvers (default: 11)")
    p.add_argument("--fit", action="store_true",
                   help="Fit & annotate slope lines on speed.png")
    args = p.parse_args()

    if args.plot_only:
        print(f"Plot-only mode (trim={args.trim}) — loading data.json ...", flush=True)
        data = _json.loads((OUTPUT / "data.json").read_text(encoding="utf-8"))
        n_range = [int(k) for k in data["dp-state"].keys()]
        n_range.sort()
        _plot_speed(data, n_range, error_bar=args.error_bar, trim_frac=args.trim, fit=args.fit)
        _plot_clt_error(data, n_range)
        _plot_clt_per_n(data, n_range)
        print(f"Plots regenerated — {OUTPUT}")
    else:
        ERROR_BAR = args.error_bar
        TRIM_FRAC = args.trim
        FIT = args.fit
        N_RUNS_FAST = args.n_runs_fast
        N_RUNS_SLOW = args.n_runs_slow
        main()
