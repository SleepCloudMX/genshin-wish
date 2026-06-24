"""Percentile heatmap for CDF data across miss/stable states."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from ._base import DEFAULT_ALPHAS, MISS_LABELS, _ensure_dir


def plot_percentile_heatmap(
    cdf_map: dict[str, np.ndarray],
    title: str,
    filename: str | Path,
    alphas: list[float] | None = None,
    note_text: str | None = None,
) -> None:
    """Draw a heatmap showing percentile values (pulls needed) across miss/stable states.

    cdf_map keys: 'miss=0', 'miss=1', 'miss=2', 'miss=3', 'stable'
    """
    if alphas is None:
        alphas = DEFAULT_ALPHAS

    alpha_headers = [f"{int(a * 100)}%" for a in alphas] + ["期望"]

    data = np.zeros((len(MISS_LABELS), len(alphas) + 1), dtype=float)
    for i, (_row_name, key) in enumerate(MISS_LABELS):
        cdf = cdf_map[key]
        for j, a in enumerate(alphas):
            data[i, j] = int(np.searchsorted(cdf, a))
        # Expected value
        pdf = np.diff(cdf, prepend=0.0)
        data[i, -1] = float(np.sum(np.arange(len(pdf)) * pdf))

    fig, ax = plt.subplots(figsize=(10, 5))
    cmap = plt.colormaps['Blues']

    cax = ax.imshow(data, cmap=cmap, aspect='auto')

    min_val, max_val = data.min(), data.max()
    for i in range(len(MISS_LABELS)):
        for j in range(len(alpha_headers)):
            val = data[i, j]
            norm_val = (val - min_val) / (max_val - min_val + 1e-9)
            text_color = 'white' if norm_val > 0.6 else '#2b2b2b'
            if j == len(alpha_headers) - 1:  # expected column
                text = f"{val:.0f}"
            else:
                text = str(int(val))
            ax.text(j, i, text, ha='center', va='center',
                    color=text_color, fontweight='bold', fontsize=12)

    ax.set_xticks(np.arange(len(alpha_headers)))
    ax.set_yticks(np.arange(len(MISS_LABELS)))
    ax.set_xticklabels(alpha_headers, fontsize=11)
    ax.set_yticklabels([r[0] for r in MISS_LABELS], fontsize=11)

    ax.set_title(title, fontsize=15, pad=10, fontweight='bold')

    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
    ax.set_xticks(np.arange(data.shape[1] + 1) - .5, minor=True)
    ax.set_yticks(np.arange(data.shape[0] + 1) - .5, minor=True)
    ax.grid(which="minor", color="white", linestyle='-', linewidth=2.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    for spine in ax.spines.values():
        spine.set_visible(False)

    cbar = fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("所需总抽数", rotation=270, labelpad=20, fontsize=12)

    if note_text is None:
        note_text = (
            "注：官方未公开概率，基于玩家经验数据建模（前 73 抽 0.6%，之后每抽递增 6%；连续歪 0/1/2/3 次捕获明光概率 0.018%/9.6%/18.3%/100%），\n"
            "与官方公布的综合概率相比，期望抽数约低估 0.3 抽/UP（观测误差）；结果为解析计算（非蒙特卡洛），无模型误差与截断误差，舍入误差可忽略。"
        )
    fig.text(0.45, 0.025, note_text, ha='center', va='bottom', fontsize=8,
             color='#666666', linespacing=1.35, ma='left')

    _ensure_dir(filename)
    plt.savefig(filename, dpi=200)
    plt.close()
