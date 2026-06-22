#!/usr/bin/env python
"""B组: 任务2 (n_up-n_std-to-pulls) 方案对比 — 方案2/4."""

import json as _json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from genshin_wish._constants import CHARACTER_POOL, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._capture_radiance import guarantee_seq
from genshin_wish._gold import get_gold_pdfs
from genshin_wish._dp_golds import _dp_golds_full, golds_nstd_to_pulls
from genshin_wish.character import UpDistribution

OUTPUT = Path("output/analysis/task2-n_up-n_std-to-pulls")
QUANTILES = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
DP_PATH_MAX_N = 20

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


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    n_range = list(range(1, 31))
    methods = ["dp-path", "dp-golds"]
    data: dict[str, dict[str, dict]] = {m: {} for m in methods}

    for n_up in n_range:
        print(f"  n={n_up} ({n_up}/{n_range[-1]})", flush=True)

        # --- dp-path ---
        if n_up <= DP_PATH_MAX_N:
            t0 = time.perf_counter()
            dists = _dp_path_task2(n_up, 0)
            t = (time.perf_counter() - t0) * 1000
            data["dp-path"][str(n_up)] = {
                "n_std_values": _metrics_per_nstd(dists),
                "time_ms": t,
            }
        else:
            data["dp-path"][str(n_up)] = {
                "n_std_values": None,
                "time_ms": None,
            }

        # --- dp-golds ---
        t0 = time.perf_counter()
        gold_nstd = _dp_golds_full(n_up, 0)
        dists = golds_nstd_to_pulls(gold_nstd)
        t = (time.perf_counter() - t0) * 1000
        data["dp-golds"][str(n_up)] = {
            "n_std_values": _metrics_per_nstd(dists),
            "time_ms": t,
        }

    (OUTPUT / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- Plots ---
    _plot_speed(data, n_range)
    _plot_distribution(data, n_range)

    print(f"Done — {OUTPUT}")


def _plot_speed(data: dict, n_range: list[int]) -> None:
    from matplotlib import pyplot as plt
    from genshin_wish.viz._base import setup_style
    setup_style()

    fig, ax = plt.subplots(figsize=(10, 6))
    for name in ["dp-path", "dp-golds"]:
        ns = [n for n in n_range if data[name][str(n)]["time_ms"] is not None]
        times = [data[name][str(n)]["time_ms"] for n in ns]
        ax.plot(ns, times, "o-", markersize=4, label=name)
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
    main()
