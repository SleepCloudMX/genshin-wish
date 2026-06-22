"""Shared utilities for analysis scripts: timing, benchmarking, plotting."""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib import pyplot as plt

from genshin_wish.viz._base import setup_style

setup_style()

OUTPUT = Path("output/analysis")


def timeit(fn: Callable[[], Any], n_runs: int = 3) -> float:
    """Median wall-clock time in milliseconds over *n_runs* calls."""
    times: list[float] = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return float(np.median(times)) * 1000


def benchmark(
    n_range: list[int],
    solvers: dict[str, Callable[[int], dict[str, Any]]],
) -> dict[str, dict[int, dict[str, Any]]]:
    """Run each solver on each n, collecting results.

    Args:
        n_range: list of n_up values to test.
        solvers: {name: fn} where fn(n) returns a dict with at least "time_ms".

    Returns:
        {solver_name: {n: result_dict}}
    """
    data: dict[str, dict[int, dict[str, Any]]] = {
        name: {} for name in solvers
    }
    for n in n_range:
        for name, fn in solvers.items():
            result = fn(n)
            data[name][n] = result
    return data


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


def plot_speed(
    data: dict[str, dict[int, dict[str, Any]]],
    save_path: str | Path,
    title: str = "Speed comparison",
    cutoff_s: float = 10.0,
) -> None:
    """Log-log speed plot.  Solvers exceeding *cutoff_s* are truncated."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for name in data:
        ns = sorted(data[name].keys())
        times = [min(data[name][n]["time_ms"], cutoff_s * 1000) for n in ns]
        ax.plot(ns, times, "o-", markersize=4, label=name)

    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("time (ms)")
    ax.set_title(title)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    _save(fig, save_path)


def plot_clt_error_abs(
    data: dict[str, dict[int, dict[str, Any]]],
    exact_key: str,
    clt_key: str,
    quantiles: list[float],
    save_path: str | Path,
    title: str = "CLT absolute error",
) -> None:
    """Absolute error (pulls/UP) of CLT vs exact at each quantile."""
    ns = sorted(data[exact_key].keys())
    colors = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    linestyles = [":", "--", "-", "-", "-", "--", ":"]

    fig, ax = plt.subplots(figsize=(12, 7))
    for qi, q in enumerate(quantiles):
        errors = []
        for n in ns:
            e = data[exact_key][n]["quantiles"][q] / n
            c = data[clt_key][n]["quantiles"][q] / n
            errors.append(abs(e - c))
        ax.plot(ns, errors, color=colors[qi % len(colors)],
                linestyle=linestyles[qi % len(linestyles)],
                linewidth=2, label=f"{int(q * 100)}%")
    ax.set_title(title, fontsize=14)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("error (pulls / UP)")
    ax.legend(loc="upper right", ncol=4, fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save(fig, save_path)


def plot_clt_error_rel(
    data: dict[str, dict[int, dict[str, Any]]],
    exact_key: str,
    clt_key: str,
    quantiles: list[float],
    save_path: str | Path,
    title: str = "CLT relative error",
) -> None:
    """Relative error (%) of CLT vs exact at each quantile."""
    ns = sorted(data[exact_key].keys())
    colors = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
    linestyles = [":", "--", "-", "-", "-", "--", ":"]

    fig, ax = plt.subplots(figsize=(12, 7))
    for qi, q in enumerate(quantiles):
        errors = []
        for n in ns:
            e = data[exact_key][n]["quantiles"][q] / n
            c = data[clt_key][n]["quantiles"][q] / n
            errors.append(abs(e - c) / max(e, 1.0) * 100)
        ax.plot(ns, errors, color=colors[qi % len(colors)],
                linestyle=linestyles[qi % len(linestyles)],
                linewidth=2, label=f"{int(q * 100)}%")
    ax.set_title(title, fontsize=14)
    ax.set_xlabel("$n_\\text{up}$")
    ax.set_ylabel("relative error (%)")
    ax.legend(loc="upper right", ncol=4, fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    _save(fig, save_path)


def plot_distribution_compare(
    ref: dict[int, float],
    test: dict[int, float],
    save_path: str | Path,
    label_ref: str = "dp-path",
    label_test: str = "dp-golds",
    title: str = "n_std distribution comparison",
) -> None:
    """Side-by-side bar chart comparing two n_std distributions."""
    all_keys = sorted(set(ref.keys()) | set(test.keys()))
    x = np.arange(len(all_keys))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, [ref.get(k, 0) for k in all_keys], width,
           label=label_ref, alpha=0.8)
    ax.bar(x + width / 2, [test.get(k, 0) for k in all_keys], width,
           label=label_test, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([str(k) for k in all_keys])
    ax.set_xlabel("$n_\\text{std}$")
    ax.set_ylabel("probability")
    ax.set_title(title)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _save(fig, save_path)


# ---------------------------------------------------------------------------
# internal
# ---------------------------------------------------------------------------


def _save(fig: plt.Figure, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200)
    plt.close(fig)
