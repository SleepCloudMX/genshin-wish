"""Cumulative probability curve for ten-pull multi-gold events."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator
import matplotlib.patheffects as pe

from genshin_wish.viz._base import _ensure_dir


def plot_multi_gold(p: float, title: str, save_path: Path) -> None:
    """Plot cumulative probability of at least one multi-gold event
    vs number of ten-pulls, with percentile annotations.

    The curve is y = 1 - (1 - p)^x where x is the number of ten-pulls
    and p is the per-ten-pull probability.

    Parameters
    ----------
    p : float
        Probability of the multi-gold event per ten-pull.
    title : str
        Chart title.
    save_path : Path
        Output file path (parent directories created automatically).
    """
    save_path = _ensure_dir(save_path)

    # 动态设定横轴，2/p 覆盖了绝大多数情况
    n_max = int(2 / p)
    x = np.arange(1, n_max + 1)
    y = 1 - (1 - p) ** x

    # 设置样式
    plt.style.use('seaborn-v0_8-muted')
    fig, ax = plt.subplots(figsize=(10, 6), dpi=120)

    # 绘制主体曲线
    ax.plot(x, y, color='#d3a055', linewidth=2.5, label=f'{title} 概率: {p:.6%}')
    ax.fill_between(x, y, color='#d3a055', alpha=0.1)

    # 1. 标注均值 (Expectation N = 1/p)
    n_avg = 1 / p
    y_avg = 1 - (1 - p) ** n_avg
    avg_color = '#2c3e50'

    ax.axvline(x=n_avg, color=avg_color, linestyle='-', alpha=0.8, linewidth=1.5)
    ax.scatter(n_avg, y_avg, color=avg_color, s=60, zorder=6, marker='D')
    ax.annotate(f'期望: {n_avg:.2f} 次十连\n(概率: {y_avg:.1%})',
                xy=(n_avg, y_avg), xytext=(n_avg + n_max * 0.02, y_avg - 0.12),
                fontsize=10, color=avg_color, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=avg_color, lw=1))

    # 2. 标注关键百分位点
    targets = [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
    colors = [
        '#7ed355',  # 10% - 浅绿
        '#55d3a8',  # 30% - 青绿
        '#55a8d3',  # 50% - 蓝色
        '#8355d3',  # 70% - 紫色
        '#d355a8',  # 90% - 玫红
        '#d35555',  # 99% - 红色
    ]

    for target, color in zip(targets, colors):
        # 无论是否在 n_max 内，都精确计算
        n_val = np.log(1 - target) / np.log(1 - p)

        # 随线标注低分位点 (10% - 70%)
        if target <= 0.7:
            ax.axvline(x=n_val, color=color, linestyle='--', alpha=0.6)
            ax.axhline(y=target, color=color, linestyle='--', alpha=0.3)
            ax.scatter(n_val, target, color=color, s=40, zorder=5)
            ax.annotate(f'{int(target * 100)}% 需要 {int(n_val)} 次十连',
                        xy=(n_val, target), xytext=(n_val + n_max * 0.02, target - 0.04),
                        fontsize=9, color=color, fontweight='bold')
        # 右下角固定标注高分位点 (90%, 99%)
        else:
            # 设定固定的垂直偏移量，在 Legend 上方堆叠
            # 90% 在上，99% 在下
            y_fixed = 0.28 if target == 0.9 else 0.20

            # 直接使用相对于坐标系的文本标注，不再使用指向箭头的 annotate
            ax.text(n_max * 0.98, y_fixed,
                    f'{int(target * 100)}% 累计需要 {int(n_val)} 次十连',
                    fontsize=10, color=color, fontweight='bold',
                    ha='right', va='center',
                    bbox=dict(boxstyle='round,pad=0.3', fc='white', ec=color, alpha=0.8, lw=1.5))

    # 图表修饰
    ax.set_title(title, fontsize=14, pad=20, fontweight='bold')
    ax.set_xlabel('十连次数', fontsize=11)
    ax.set_ylabel('累积概率', fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, n_max)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(loc='lower right', frameon=True)

    # 移除顶部和右侧边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
