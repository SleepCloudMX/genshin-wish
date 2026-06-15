"""CDF plotting: annotated single-CDF and multi-line UP-CDF charts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator

from genshin_wish.viz._base import ALPHA_COLORS_6, _ensure_dir, setup_style

if __name__ != "__main__":
    setup_style()


def plot_annotated_cdf(
    cdf: np.ndarray,
    title: str,
    filename: str | Path,
    alphas: list[float] | None = None,
    colors: list[str] | None = None,
) -> None:
    """Draw a CDF curve with percentile annotation lines.

    Parameters
    ----------
    cdf : np.ndarray
        1-D cumulative distribution function array.
    title : str
        Chart title.
    filename : str or Path
        Output file path (parent directories created automatically).
    alphas : list[float] or None
        Percentile thresholds to annotate.  Defaults to [0.1, 0.3, 0.5, 0.7, 0.9, 0.99].
    colors : list[str] or None
        Hex colours for each alpha annotation.  Defaults to ALPHA_COLORS_6.
    """
    if alphas is None:
        alphas = [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
    if colors is None:
        colors = ALPHA_COLORS_6

    plt.figure(figsize=(12, 7))
    x_axis = np.arange(len(cdf))
    plt.plot(x_axis[1:], cdf[1:], color="#333333", linewidth=2.5, zorder=2)

    for alpha, color in zip(alphas, colors):
        idx = int(np.searchsorted(cdf, alpha))
        plt.vlines(x=idx, ymin=0, ymax=alpha, colors=color, linestyles="--", linewidth=1.5, alpha=0.8, zorder=3)
        plt.hlines(y=alpha, xmin=0, xmax=idx, colors=color, linestyles=":", linewidth=1, alpha=0.4, zorder=1)
        plt.text(float(idx + 1.5), alpha - 0.01, f"α={alpha}\n x={idx}",
                 fontsize=10, color=color, fontweight="bold",
                 verticalalignment="top",
                 bbox=dict(facecolor="white", alpha=0.8, edgecolor=color, boxstyle="round,pad=0.3"))
        plt.scatter(idx, 0, color=color, s=20, zorder=4)

    plt.title(title, fontsize=14, pad=15)
    plt.xlabel("抽数", fontsize=12)
    plt.ylabel("概率", fontsize=12)
    plt.xlim(0, len(cdf) * 1.05)
    plt.ylim(0, 1.05)
    plt.grid(True, which="major", linestyle="-", alpha=0.2)
    plt.tight_layout()
    _ensure_dir(filename)
    plt.savefig(filename)
    plt.close()


def plot_up_cdf_lines(
    dists: dict[int, np.ndarray],
    max_pulls: int,
    save_path: str | Path,
    title: str,
) -> None:
    """Plot multiple CDF lines for different UP counts.

    Parameters
    ----------
    dists : dict[int, np.ndarray]
        Mapping from n_up (int) to CDF array (already computed, padded to
        at least *max_pulls*).  Key 0 is ignored if present (always 1.0).
    max_pulls : int
        Right limit of the x-axis (total pulls).
    save_path : str or Path
        Output file path (parent directories created automatically).
    title : str
        Full chart title.
    """
    max_n_up = max(k for k in dists if k > 0)
    pulls = np.arange(max_pulls)

    fig, ax = plt.subplots(figsize=(14, 8))
    colors = plt.get_cmap("viridis")(np.linspace(0, 0.85, max_n_up + 1))

    for n in range(1, max_n_up + 1):
        cdf_n = dists.get(n)
        if cdf_n is None:
            continue
        ax.plot(pulls, cdf_n[:max_pulls], label=f"至少 {n} UP (含 {n-1} 命)", color=colors[n], linewidth=2.5)

        p50_idx = int(np.searchsorted(cdf_n[:max_pulls], 0.5))
        if p50_idx < max_pulls:
            ax.vlines(p50_idx, 0, 0.5, colors=colors[n], linestyles="--", alpha=0.4)
            ax.text(p50_idx, 0.52, f"{p50_idx}", color=colors[n], ha="center", fontsize=9, fontweight="bold")

    ax.xaxis.set_major_locator(MultipleLocator(100))
    ax.xaxis.set_minor_locator(MultipleLocator(20))
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_minor_locator(MultipleLocator(0.02))
    ax.grid(which="major", linestyle="-", alpha=0.3, color="black")
    ax.grid(which="minor", linestyle=":", alpha=0.3, color="gray")
    ax.set_title(title, fontsize=16, pad=20)
    ax.set_xlabel("消耗总抽数", fontsize=12)
    ax.set_ylabel("累积概率", fontsize=12)
    ax.axhline(0.9, color="red", linestyle="-.", alpha=0.2)
    ax.text(max_pulls * 0.01, 0.91, "90% 概率覆盖区 (大非线)", color="red", alpha=0.5, fontsize=10)
    ax.set_xlim(0, max_pulls)
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right", frameon=True, shadow=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
