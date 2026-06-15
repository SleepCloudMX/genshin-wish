"""Stacked area chart of UP character acquisition probabilities."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator

from genshin_wish.viz._base import _ensure_dir


def plot_stacked_up_probabilities(
    dists: dict[int, np.ndarray],
    max_pulls: int,
    save_path: Path,
    title: str,
) -> None:
    """Plot a stacked area chart showing the proportion of players
    holding exactly n UP characters at each pull count.

    Parameters
    ----------
    dists : dict[int, np.ndarray]
        Maps n_up -> CDF array.  dists[0] should be all-ones.
        dists[n][i] = P(>= n UP | i pulls).
    max_pulls : int
        Maximum pull count on the x-axis.
    save_path : Path
        Output file path (parent directories created automatically).
    title : str
        Chart title.
    """
    save_path = _ensure_dir(save_path)
    max_n_up = max(dists.keys())

    # Convert CDFs to independent probabilities:
    #   dist_matrix[n] = P(exactly n UP) = CDF(n) - CDF(n+1)   for n < max_n_up
    #   dist_matrix[max_n_up] = P(>= max_n_up UP) = CDF(max_n_up)
    dist_matrix = np.zeros((max_n_up + 1, max_pulls))
    for n in range(max_n_up):
        dist_matrix[n] = dists[n][:max_pulls] - dists[n + 1][:max_pulls]
    dist_matrix[max_n_up] = dists[max_n_up][:max_pulls]

    pulls = np.arange(max_pulls)

    fig, ax = plt.subplots(figsize=(14, 8))
    colors = plt.get_cmap('Spectral_r')(np.linspace(0, 1, max_n_up + 1))

    labels = [f"持有 {i} UP" for i in range(max_n_up + 1)]
    ax.stackplot(pulls, dist_matrix, labels=labels, colors=colors, alpha=0.7, edgecolor='white', linewidth=0.2)

    # --- 刻度细化 ---
    ax.xaxis.set_major_locator(MultipleLocator(100))  # 主刻度 100
    ax.xaxis.set_minor_locator(MultipleLocator(20))   # 次刻度 20
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_minor_locator(MultipleLocator(0.02))

    # 网格线设置：主线明显，次线淡
    ax.grid(which='major', linestyle='-', alpha=0.4, color='gray')
    ax.grid(which='minor', linestyle=':', alpha=0.3, color='gray')

    ax.set_title(title, fontsize=16, pad=20)
    ax.set_xlabel("消耗总抽数", fontsize=12)
    ax.set_ylabel("概率百分比", fontsize=12)
    ax.set_xlim(0, max_pulls)
    ax.set_ylim(0, 1)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), frameon=True)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
