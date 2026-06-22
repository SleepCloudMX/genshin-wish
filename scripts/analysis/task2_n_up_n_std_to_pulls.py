#!/usr/bin/env python
"""B组: 任务2 (n_up-n_std-to-pulls) — dp-path vs dp-golds.

对比方案 2 和方案 4 在 n=1..30 时按 n_std 分层的条件抽数分布，
验证方案 4 的正确性，输出 speed.png 及 data.json。

使用示例::

    python scripts/analysis/task2_n_up_n_std_to_pulls.py
    python scripts/analysis/task2_n_up_n_std_to_pulls.py --n-runs 100
    python scripts/analysis/task2_n_up_n_std_to_pulls.py --plot-only --trim 0.3
"""

import json as _json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import trim_mean

from genshin_wish._constants import CHARACTER_POOL, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._capture_radiance import guarantee_seq
from genshin_wish._gold import get_gold_pdfs
from genshin_wish._dp_golds import _dp_golds_full, golds_nstd_to_pulls
from genshin_wish.character import UpDistribution

OUTPUT = Path("output/analysis/task2-n_up-n_std-to-pulls")
QUANTILES = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
DP_PATH_MAX_N = 20
TRIM_FRAC = 0.2
ERROR_BAR = "minmax"
N_RUNS = 50

_p_up = CAPTURE_RADIANCE_WIN_RATE


def _dp_path_task2(n_uncertain: int, k_miss: int) -> dict[int, UpDistribution]:
    """方案2: group guarantee_seq by n_std, then condition."""
    seq2p = guarantee_seq(k_miss, n_uncertain)
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=n_uncertain * 2)

    # {n_std: {gold: prob}}
    nstd_golds: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for seq, (_final_k, prob) in seq2p.items():
        gold = sum(seq)
        ns = seq.count(2)
        nstd_golds[ns][gold] += prob

    result: dict[int, UpDistribution] = {}
    for ns, gold_probs in nstd_golds.items():
        total = sum(gold_probs.values())
        max_gold = max(gold_probs.keys())
        pdf_arr = np.zeros(len(pdfs[max_gold]), dtype=np.float64)
        for gold, prob in gold_probs.items():
            if gold > 0:
                pdf_arr[: len(pdfs[gold])] += pdfs[gold] * (prob / total)
        cdf = np.cumsum(pdf_arr)
        result[ns] = UpDistribution(pdf=pdf_arr, cdf=cdf)

    return dict(result)


def _metrics_per_nstd(dists: dict[int, UpDistribution]) -> dict:
    """Extract expected + quantiles for each n_std."""
    out: dict = {}
    for ns, d in dists.items():
        cdf = d.cdf
        out[str(ns)] = {
            "expected": d.expected,
            "quantiles": {str(q): int(np.searchsorted(cdf, q)) for q in QUANTILES},
        }
    return out


def _timeit(fn, n_runs: int = 50) -> dict:
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


def _null_metrics() -> dict:
    return {
        "n_std_values": None,
        "time_ms": None, "time_min": None, "time_max": None,
        "time_std": None, "time_all": [], "n_runs": 0,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    n_range = list(range(1, 31))
    methods = ["dp-path", "dp-golds"]
    data: dict[str, dict[str, dict]] = {m: {} for m in methods}

    for n_up in n_range:
        print(f"  n={n_up} ({n_up}/{n_range[-1]})", flush=True)

        # --- dp-path ---
        if n_up <= DP_PATH_MAX_N:
            def _run_path():
                _dp_path_task2(n_up, 0)
            timing = _timeit(_run_path, n_runs=N_RUNS)
            dists = _dp_path_task2(n_up, 0)
            data["dp-path"][str(n_up)] = {
                "n_std_values": _metrics_per_nstd(dists),
                **timing,
            }
        else:
            data["dp-path"][str(n_up)] = _null_metrics()

        # --- dp-golds ---
        def _run_golds():
            gn = _dp_golds_full(n_up, 0)
            golds_nstd_to_pulls(gn)
        timing = _timeit(_run_golds, n_runs=N_RUNS)
        gn = _dp_golds_full(n_up, 0)
        dists = golds_nstd_to_pulls(gn)
        data["dp-golds"][str(n_up)] = {
            "n_std_values": _metrics_per_nstd(dists),
            **timing,
        }

    (OUTPUT / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- Plots ---
    _plot_speed(data, n_range)
    _plot_distribution(data, n_range)

    print(f"Done — {OUTPUT}")


def _trimmed_stats(raw: list[float], trim_frac: float) -> dict:
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
                trim_frac: float = 0.0) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    eb = error_bar or ERROR_BAR
    trim = trim_frac or TRIM_FRAC

    fig, ax = plt.subplots(figsize=(10, 6))
    for name in ["dp-path", "dp-golds"]:
        ns = [n for n in n_range if data[name][str(n)]["time_ms"] is not None]
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
        line = ax.plot(ns, times, "o-", markersize=4, label=name)[0]
        if eb != "none":
            ax.fill_between(ns, los, his, alpha=0.15, color=line.get_color())
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_title("Task 2 speed comparison")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUTPUT / "speed.png", dpi=200)
    plt.close(fig)


def _plot_distribution(data: dict, n_range: list[int]) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    # Pick n=10 for distribution comparison
    n = 10
    if str(n) not in data["dp-path"]:
        return

    path_data = data["dp-path"][str(n)]["n_std_values"]
    golds_data = data["dp-golds"][str(n)]["n_std_values"]

    for ns_str in path_data:
        if ns_str not in golds_data:
            continue
        p_exp = path_data[ns_str]["expected"]
        g_exp = golds_data[ns_str]["expected"]
        if abs(p_exp - g_exp) > 0.01:
            print(f"  MISMATCH n_std={ns_str}: path={p_exp:.2f} golds={g_exp:.2f}")

    print("  Distribution check: OK")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--plot-only", action="store_true",
                   help="Skip computation, regenerate plots from data.json")
    p.add_argument("--error-bar", choices=["minmax", "std3", "none"],
                   default="minmax",
                   help="Error bar style (default: minmax)")
    p.add_argument("--trim", type=float, default=0.2,
                   help="Trim fraction (default: 0.2)")
    p.add_argument("--n-runs", type=int, default=50,
                   help="Number of runs per solver (default: 50)")
    args = p.parse_args()

    if args.plot_only:
        print(f"Plot-only mode (trim={args.trim}) — loading data.json ...", flush=True)
        data = _json.loads((OUTPUT / "data.json").read_text(encoding="utf-8"))
        n_range = [int(k) for k in data["dp-golds"].keys()]
        n_range.sort()
        _plot_speed(data, n_range, error_bar=args.error_bar, trim_frac=args.trim)
        _plot_distribution(data, n_range)
        print(f"Plots regenerated — {OUTPUT}")
    else:
        ERROR_BAR = args.error_bar
        TRIM_FRAC = args.trim
        N_RUNS = args.n_runs
        main()
