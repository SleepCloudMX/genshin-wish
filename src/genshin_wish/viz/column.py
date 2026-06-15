"""Column chart for success-percentile PDF distributions."""

from pathlib import Path
from typing import Callable

import numpy as np
from matplotlib import pyplot as plt

from ._base import _ensure_dir


def plot_success_column_chart(
    pdf_func: Callable[[int], np.ndarray],
    max_n_up: int,
    save_path: Path,
    title: str,
) -> None:
    """Draw a column chart showing PDF distributions and percentile annotations per constellation.

    pdf_func(n_up) returns the PDF array for n_up UPs.
    title is a pre-computed string like "已连续歪 0 次".
    """
    alpha_configs = [
        {'a': 0.1,  'color': '#2ca02c'},
        {'a': 0.3,  'color': '#1f77b4'},
        {'a': 0.5,  'color': '#ff7f0e'},
        {'a': 0.7,  'color': '#9467bd'},
        {'a': 0.9,  'color': '#d62728'},
        {'a': 0.99, 'color': '#4b0082'},
    ]

    n_axis = np.arange(1, max_n_up + 1)
    fig, ax = plt.subplots(figsize=(14, 9))
    cmap = plt.colormaps['YlGnBu']

    for j, n in enumerate(n_axis):
        pdf = pdf_func(n)
        cdf = np.cumsum(pdf)
        avg_pulls = sum(i * p for i, p in enumerate(pdf))

        h_limit = np.searchsorted(cdf, 0.995)

        # 1. Draw gradient column segments
        y_steps = np.arange(0, h_limit + 1, 2)
        for i in range(len(y_steps) - 1):
            y_curr = int(y_steps[i])
            y_next = int(y_steps[i + 1])
            prob = cdf[y_curr] if y_curr < len(cdf) else 1.0
            ax.add_patch(plt.Rectangle(
                (j - 0.3, y_curr), 0.6, y_next - y_curr,
                facecolor=cmap(prob), edgecolor='none', zorder=1,
            ))

        # Column border
        ax.add_patch(plt.Rectangle(
            (j - 0.3, 0), 0.6, float(h_limit),
            fill=False, edgecolor='#333333', linewidth=1, zorder=2,
        ))

        # 2. Average pull count above column top
        ax.text(j, h_limit + 10, f"期望: {avg_pulls:.2f}", ha='center', va='bottom',
                fontsize=10, fontweight='bold', color='#333333')

        # 3. Percentile lines with anti-overlap labels
        last_y = -100
        for config in alpha_configs:
            alpha = config['a']
            y_val = np.searchsorted(cdf, alpha)

            if y_val <= h_limit:
                ax.hlines(y=y_val, xmin=j - 0.35, xmax=j + 0.35,
                          colors=config['color'], linestyles='--', linewidth=1.2, zorder=3)

                v_offset = -2
                if abs(y_val - last_y) < (h_limit * 0.025):
                    v_offset = 2
                    va = 'bottom'
                else:
                    va = 'top'

                label_text = f"{int(alpha * 100)}% {y_val}"
                ax.text(j, y_val + v_offset, label_text, color=config['color'],
                        ha='center', va=va, fontsize=8, fontweight='bold',
                        bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=0.5))

                last_y = y_val if va == 'top' else y_val

    # 4. Visual polish
    ax.set_xticks(range(len(n_axis)))
    ax.set_xticklabels([f"{i - 1}命" for i in n_axis], fontsize=12)

    final_pdf = pdf_func(max_n_up)
    global_max_y = np.searchsorted(np.cumsum(final_pdf), 0.995)
    ax.set_ylim(0, global_max_y * 1.15)

    tick_step = 50 if global_max_y < 1200 else 100
    ax.set_yticks(np.arange(0, global_max_y + tick_step, tick_step))

    ax.set_title(f"【{title}】各命座抽数分位点分布图", fontsize=16, pad=30)
    ax.set_ylabel("投入总抽数", fontsize=13)
    ax.grid(axis='y', linestyle=':', alpha=0.4, zorder=0)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
    cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label('达成概率 (CDF)')

    _ensure_dir(save_path)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
