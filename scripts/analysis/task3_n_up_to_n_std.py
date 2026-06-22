#!/usr/bin/env python
"""C组: 任务3 (n_up-to-n_std) 方案对比 — 方案2/4."""

import json as _json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import trim_mean

from genshin_wish._capture_radiance import guarantee_seq
from genshin_wish._dp_golds import _dp_golds_full, golds_nstd_to_nstd_dist

OUTPUT = Path("output/analysis/task3-n_up-to-n_std")
DP_PATH_MAX_N = 20
TRIM_FRAC = 0.2
ERROR_BAR = "minmax"
N_RUNS = 50


def _dp_path_task3(n_uncertain: int, k_miss: int) -> dict[int, float]:
    """方案2: group guarantee_seq by n_std, sum probabilities."""
    seq2p = guarantee_seq(k_miss, n_uncertain)
    result: dict[int, float] = defaultdict(float)
    for seq, (_final_k, prob) in seq2p.items():
        result[seq.count(2)] += prob
    return dict(result)


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
        "n_std_dist": None, "expected_n_std": None,
        "time_ms": None, "time_min": None, "time_max": None,
        "time_std": None, "time_all": [], "n_runs": 0,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    n_range = list(range(1, 101))
    methods = ["dp-path", "dp-golds"]
    data: dict[str, dict[str, dict]] = {m: {} for m in methods}

    for n_up in n_range:
        print(f"  n={n_up} ({n_up}/{n_range[-1]})", flush=True)

        # --- dp-path ---
        if n_up <= DP_PATH_MAX_N:
            def _run_path():
                _dp_path_task3(n_up, 0)
            timing = _timeit(_run_path, n_runs=N_RUNS)
            nstd_dist = _dp_path_task3(n_up, 0)
            data["dp-path"][str(n_up)] = {
                "n_std_dist": {str(k): v for k, v in nstd_dist.items()},
                "expected_n_std": float(sum(k * v for k, v in nstd_dist.items())),
                **timing,
            }
        else:
            data["dp-path"][str(n_up)] = _null_metrics()

        # --- dp-golds ---
        def _run_golds():
            gn = _dp_golds_full(n_up, 0)
            golds_nstd_to_nstd_dist(gn)
        timing = _timeit(_run_golds, n_runs=N_RUNS)
        gn = _dp_golds_full(n_up, 0)
        nstd_dist = golds_nstd_to_nstd_dist(gn)
        data["dp-golds"][str(n_up)] = {
            "n_std_dist": {str(k): v for k, v in nstd_dist.items()},
            "expected_n_std": float(sum(k * v for k, v in nstd_dist.items())),
            **timing,
        }

    (OUTPUT / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- Plots ---
    _plot_speed(data, n_range)
    _plot_distribution(data)

    print(f"Done — {OUTPUT}")


def _trim_time(entry: dict, trim_frac: float) -> float | None:
    raw = entry.get("time_all")
    if raw and len(raw) > 0:
        return float(trim_mean(np.array(raw), trim_frac))
    return entry.get("time_ms")


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
        times = [_trim_time(data[name][str(n)], trim) for n in ns]
        line = ax.plot(ns, times, "o-", markersize=4, label=name)[0]
        if eb != "none":
            if eb == "std3":
                t_std = [data[name][str(n)].get("time_std", 0) for n in ns]
                lo = [max(0, t - 3 * s) for t, s in zip(times, t_std)]
                hi = [t + 3 * s for t, s in zip(times, t_std)]
            else:
                lo = [data[name][str(n)].get("time_min", t) for n, t in zip(ns, times)]
                hi = [data[name][str(n)].get("time_max", t) for n, t in zip(ns, times)]
            ax.fill_between(ns, lo, hi, alpha=0.15, color=line.get_color())
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_title("Task 3 speed comparison")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUTPUT / "speed.png", dpi=200)
    plt.close(fig)


def _plot_distribution(data: dict) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    for n in [10, 20]:
        sn = str(n)
        if sn not in data["dp-path"] or data["dp-path"][sn]["n_std_dist"] is None:
            continue

        path_dist = data["dp-path"][sn]["n_std_dist"]
        golds_dist = data["dp-golds"][sn]["n_std_dist"]

        all_keys = sorted(set(path_dist.keys()) | set(golds_dist.keys()),
                          key=int)
        x = np.arange(len(all_keys))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(x - width / 2, [path_dist.get(k, 0) for k in all_keys],
               width, label="dp-path", alpha=0.8)
        ax.bar(x + width / 2, [golds_dist.get(k, 0) for k in all_keys],
               width, label="dp-golds", alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(all_keys)
        ax.set_xlabel("$n_\\text{std}$")
        ax.set_ylabel("probability")
        ax.set_title(f"Task 3: $P(n_{{\\text{{std}}}})$ for $n_{{\\text{{up}}}}={n}$")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(OUTPUT / f"distribution-n{n}.png", dpi=200)
        plt.close(fig)

    # Verify consistency
    for n in [10, 20]:
        sn = str(n)
        if sn not in data["dp-path"] or data["dp-path"][sn]["n_std_dist"] is None:
            continue
        pd_ = data["dp-path"][sn]["n_std_dist"]
        gd_ = data["dp-golds"][sn]["n_std_dist"]
        max_diff = max(
            abs(pd_.get(k, 0) - gd_.get(k, 0))
            for k in set(pd_.keys()) | set(gd_.keys())
        )
        print(f"  n={n}: max diff = {max_diff:.2e}")


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
        _plot_distribution(data)
        print(f"Plots regenerated — {OUTPUT}")
    else:
        ERROR_BAR = args.error_bar
        TRIM_FRAC = args.trim
        N_RUNS = args.n_runs
        main()
