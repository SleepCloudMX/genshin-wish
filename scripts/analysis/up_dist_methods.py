#!/usr/bin/env python
"""Benchmark three exact UP-distribution methods: DP-full, DP-prune, Enum, Convolution.

Usage:
    python scripts/analysis/up_dist_methods.py --dp-vs-enum
    python scripts/analysis/up_dist_methods.py --enum-vs-conv
    python scripts/analysis/up_dist_methods.py               # both
"""

import argparse
import json as _json
import time
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from genshin_wish._constants import CHARACTER_POOL, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._gold import get_gold_pdfs
from genshin_wish.character import CharacterState, up_distribution
from genshin_wish.long_term import _solve_exact
from genshin_wish.viz._base import setup_style

setup_style()

OUTPUT = Path("output/analysis/method-compare")
QUANTILES = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
EPSILONS = [1e-12, 1e-15, 1e-18]

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _pad(a: np.ndarray, length: int) -> np.ndarray:
    c = np.zeros(length, dtype=np.float64)
    c[: len(a)] = a
    return c


def _manual_convolve(a: np.ndarray, b: np.ndarray, eps: float = 0.0) -> tuple[np.ndarray, int, int]:
    """Manual convolution (no FFT), returns (result, total_ops, skipped_ops).

    *eps* > 0 enables pruning: entries in *a* with |val| < eps are skipped.
    """
    n = len(a) + len(b) - 1
    result = np.zeros(n, dtype=np.float64)
    total = 0
    skipped = 0
    for i in range(len(a)):
        total += 1
        ai = a[i]
        if eps > 0 and abs(ai) < eps:
            skipped += 1
            continue
        if ai != 0.0:
            result[i : i + len(b)] += ai * b
    return result, total, skipped


def _extract_metrics(pdf: np.ndarray) -> dict:
    cdf = np.cumsum(pdf)
    expected = float(np.sum(np.arange(len(pdf)) * pdf))
    qs = {f"{q:.2f}": int(np.searchsorted(cdf, q)) for q in QUANTILES}
    return {"expected": expected, "quantiles": qs}


def _timeit(fn, n_runs: int = 3) -> float:
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return float(np.median(times))


# ---------------------------------------------------------------------------
# solvers
# ---------------------------------------------------------------------------


def solve_dp_full(
    n_up: int, p_up: list[float], p_gold: np.ndarray, p_gold2: np.ndarray
) -> dict[int, np.ndarray]:
    """Iterative convolution using manual conv — simulates 3D-DP per-element cost."""
    n_states = len(p_up)
    pdf_state: list[np.ndarray | None] = [None] * n_states
    pdf_state[0] = np.array([1.0], dtype=np.float64)
    result: dict[int, np.ndarray] = {}

    for n in range(1, n_up + 1):
        new = [np.zeros(1, dtype=np.float64) for _ in range(n_states)]
        for s in range(n_states):
            ps = pdf_state[s]
            if ps is None:
                continue
            # win → state 0
            wc, _, _ = _manual_convolve(ps, p_gold)
            wc *= p_up[s]
            new[0] = _pad(new[0], max(len(new[0]), len(wc)))
            new[0][: len(wc)] += wc
            # loss → state s+1
            if s < n_states - 1:
                lc, _, _ = _manual_convolve(ps, p_gold2)
                lc *= 1 - p_up[s]
                new[s + 1] = _pad(new[s + 1], max(len(new[s + 1]), len(lc)))
                new[s + 1][: len(lc)] += lc

        pdf_state = new
        non_none = [p for p in pdf_state if p is not None]
        mlen = max(len(p) for p in non_none)
        total = np.zeros(mlen, dtype=np.float64)
        for p in non_none:
            total[: len(p)] += p
        result[n] = total

    return result


def solve_dp_prune(
    n_up: int, p_up: list[float], p_gold: np.ndarray, p_gold2: np.ndarray, eps: float
) -> tuple[dict[int, np.ndarray], dict[str, float]]:
    """Same as DP-full but skip low-prob entries in manual convolution."""
    n_states = len(p_up)
    pdf_state: list[np.ndarray | None] = [None] * n_states
    pdf_state[0] = np.array([1.0], dtype=np.float64)
    result: dict[int, np.ndarray] = {}
    total_ops = 0
    skipped_ops = 0

    for n in range(1, n_up + 1):
        new = [np.zeros(1, dtype=np.float64) for _ in range(n_states)]
        for s in range(n_states):
            ps = pdf_state[s]
            if ps is None:
                continue
            wc, tot, sk = _manual_convolve(ps, p_gold, eps)
            total_ops += tot
            skipped_ops += sk
            wc *= p_up[s]
            new[0] = _pad(new[0], max(len(new[0]), len(wc)))
            new[0][: len(wc)] += wc
            if s < n_states - 1:
                lc, tot, sk = _manual_convolve(ps, p_gold2, eps)
                total_ops += tot
                skipped_ops += sk
                lc *= 1 - p_up[s]
                new[s + 1] = _pad(new[s + 1], max(len(new[s + 1]), len(lc)))
                new[s + 1][: len(lc)] += lc

        pdf_state = new
        non_none = [p for p in pdf_state if p is not None]
        mlen = max(len(p) for p in non_none)
        total = np.zeros(mlen, dtype=np.float64)
        for p in non_none:
            total[: len(p)] += p
        result[n] = total

    stats = {"total_ops": total_ops, "skipped_ops": skipped_ops}
    return result, stats


def solve_enum(n_up: int, k_miss: int = 0) -> np.ndarray:
    """Wrapper: guarantee_seq enumeration (ground truth)."""
    state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k_miss)
    return up_distribution(state, n_up).pdf


def solve_conv(n_up: int, p_up: list[float], p_gold: np.ndarray, p_gold2: np.ndarray) -> dict[int, np.ndarray]:
    """Wrapper: iterative convolution with numpy FFT (方案三)."""
    return _solve_exact(n_up, p_up, p_gold, p_gold2)


# ---------------------------------------------------------------------------
# A组: DP vs Enum  (n_up = 1..10)
# ---------------------------------------------------------------------------


def _plot_dp_accuracy(data: dict, save_dir: Path) -> None:
    """Error of DP-prune vs Enum, by epsilon and n_up."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    eps_labels = [f"{e:.0e}" for e in EPSILONS]
    colors = ["#1f77b4", "#ff7f0e", "#d62728"]
    n_ups = data["n_ups"]

    # Expected value relative error
    ax = axes[0, 0]
    for ei, eps in enumerate(EPSILONS):
        errs = []
        for n in n_ups:
            key = f"dp-prune-{eps:.0e}"
            ref = data["enum"][str(n)]["expected"]
            if ref == 0:
                errs.append(0)
            else:
                errs.append(abs(data[key][str(n)]["expected"] - ref) / ref)
        ax.plot(n_ups, errs, "o-", color=colors[ei], label=eps_labels[ei], markersize=4)
    ax.set_title("Expected value relative error")
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("|err| / enum")
    ax.legend()
    ax.grid(alpha=0.3)

    # Quantile absolute error (median across quantiles)
    ax = axes[0, 1]
    for ei, eps in enumerate(EPSILONS):
        errs = []
        for n in n_ups:
            key = f"dp-prune-{eps:.0e}"
            q_ref = data["enum"][str(n)]["quantiles"]
            q_pr = data[key][str(n)]["quantiles"]
            avg_err = np.mean([abs(q_pr[qk] - q_ref[qk]) for qk in q_ref])
            errs.append(avg_err)
        ax.plot(n_ups, errs, "s-", color=colors[ei], label=eps_labels[ei], markersize=4)
    ax.set_title("Mean absolute quantile error (pulls)")
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("error (pulls)")
    ax.legend()
    ax.grid(alpha=0.3)

    # Prune ratio
    ax = axes[1, 0]
    for ei, eps in enumerate(EPSILONS):
        ratios = []
        for n in n_ups:
            key = f"dp-prune-{eps:.0e}"
            s = data[key][str(n)]["skip_ratio"]
            ratios.append(s)
        ax.plot(n_ups, ratios, "d-", color=colors[ei], label=eps_labels[ei], markersize=4)
    ax.set_title("Skip ratio (skipped / total ops)")
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("ratio")
    ax.legend()
    ax.grid(alpha=0.3)

    # Speed comparison: DP-full, 3× DP-prune, Enum
    ax = axes[1, 1]
    ax.plot(n_ups, [data["dp-full"][str(n)]["time_ms"] for n in n_ups],
            "o-", color="black", label="DP-full", markersize=4)
    for ei, eps in enumerate(EPSILONS):
        ax.plot(n_ups, [data[f"dp-prune-{eps:.0e}"][str(n)]["time_ms"] for n in n_ups],
                "^-", color=colors[ei], label=f"DP-prune {eps_labels[ei]}", markersize=4)
    ax.plot(n_ups, [data["enum"][str(n)]["time_ms"] for n in n_ups],
            "s-", color="green", label="Enum", markersize=4)
    ax.set_title("Wall time")
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(save_dir / "accuracy.png", dpi=200)
    plt.close(fig)


def bench_dp_vs_enum() -> None:
    print("=== A组: DP vs Enum (n_up = 1..10) ===")
    save_dir = OUTPUT / "dp-vs-enum"
    save_dir.mkdir(parents=True, exist_ok=True)

    p_up = list(CAPTURE_RADIANCE_WIN_RATE)
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=20)
    p_gold, p_gold2 = pdfs[1], np.convolve(pdfs[1], pdfs[1])

    data: dict = {"n_ups": list(range(1, 11)), "epsilons": [f"{e:.0e}" for e in EPSILONS]}

    for n_up in range(1, 11):
        print(f"  n_up={n_up} ...")

        # DP-full
        t = _timeit(lambda: solve_dp_full(n_up, p_up, p_gold, p_gold2))
        dp_pdfs = solve_dp_full(n_up, p_up, p_gold, p_gold2)
        m = _extract_metrics(dp_pdfs[n_up])
        m["time_ms"] = t * 1000
        data.setdefault("dp-full", {})[str(n_up)] = m

        # DP-prune with 3 thresholds
        for eps in EPSILONS:
            t = _timeit(lambda: solve_dp_prune(n_up, p_up, p_gold, p_gold2, eps))
            dp_pdfs, stats = solve_dp_prune(n_up, p_up, p_gold, p_gold2, eps)
            m = _extract_metrics(dp_pdfs[n_up])
            m["time_ms"] = t * 1000
            m["skip_ratio"] = stats["skipped_ops"] / max(stats["total_ops"], 1)
            data.setdefault(f"dp-prune-{eps:.0e}", {})[str(n_up)] = m

        # Enum (ground truth)
        t = _timeit(lambda: solve_enum(n_up))
        pdf_enum = solve_enum(n_up)
        m = _extract_metrics(pdf_enum)
        m["time_ms"] = t * 1000
        data.setdefault("enum", {})[str(n_up)] = m

    (save_dir / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    _plot_dp_accuracy(data, save_dir)
    print("  Saved dp-vs-enum/")


# ---------------------------------------------------------------------------
# B组: Enum vs Conv  (n_up = 1..20)
# ---------------------------------------------------------------------------


def _plot_enum_conv_speed(data: dict, save_dir: Path) -> None:
    n_ups = data["n_ups"]
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(n_ups, [data["enum"][str(n)]["time_ms"] for n in n_ups],
            "s-", color="#d62728", label="Enum (方案二)", markersize=5)
    ax.plot(n_ups, [data["conv"][str(n)]["time_ms"] for n in n_ups],
            "o-", color="#1f77b4", label="Conv (方案三)", markersize=5)

    # Find crossover
    for n in n_ups:
        if data["enum"][str(n)]["time_ms"] > data["conv"][str(n)]["time_ms"]:
            ax.axvline(n - 0.5, color="gray", linestyle=":", alpha=0.5)
            ax.text(n, ax.get_ylim()[1] * 0.5 if ax.get_ylim()[1] > 0 else 10,
                    f" crossover at n_up={n}", fontsize=9, color="gray")
            break

    ax.set_title("Enum vs Convolution speed")
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_dir / "speed.png", dpi=200)
    plt.close(fig)


def bench_enum_vs_conv() -> None:
    print("=== B组: Enum vs Conv (n_up = 1..20) ===")
    save_dir = OUTPUT / "enum-vs-conv"
    save_dir.mkdir(parents=True, exist_ok=True)

    p_up = list(CAPTURE_RADIANCE_WIN_RATE)
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=40)
    p_gold, p_gold2 = pdfs[1], np.convolve(pdfs[1], pdfs[1])

    data: dict = {"n_ups": list(range(1, 21))}

    for n_up in range(1, 21):
        print(f"  n_up={n_up} ...")

        # Enum
        t = _timeit(lambda: solve_enum(n_up))
        pdf_enum = solve_enum(n_up)
        m = _extract_metrics(pdf_enum)
        m["time_ms"] = t * 1000
        data.setdefault("enum", {})[str(n_up)] = m

        # Conv
        t = _timeit(lambda: solve_conv(n_up, p_up, p_gold, p_gold2))
        conv_pdfs = solve_conv(n_up, p_up, p_gold, p_gold2)
        m = _extract_metrics(conv_pdfs[n_up])
        m["time_ms"] = t * 1000
        data.setdefault("conv", {})[str(n_up)] = m

    (save_dir / "data.json").write_text(
        _json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    _plot_enum_conv_speed(data, save_dir)
    print("  Saved enum-vs-conv/")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dp-vs-enum", action="store_true", help="Benchmark DP-full / DP-prune vs Enum")
    p.add_argument("--enum-vs-conv", action="store_true", help="Benchmark Enum vs Convolution")
    args = p.parse_args()

    run_all = not (args.dp_vs_enum or args.enum_vs_conv)

    if run_all or args.dp_vs_enum:
        bench_dp_vs_enum()
    if run_all or args.enum_vs_conv:
        bench_enum_vs_conv()

    print("\nDone")


if __name__ == "__main__":
    main()
