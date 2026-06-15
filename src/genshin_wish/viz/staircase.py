"""Staircase / fan chart of UP count vs pulls with percentile bands."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator
import matplotlib.patheffects as pe

from genshin_wish.viz._base import _ensure_dir


def plot_staircase_luck_fan(
    dists: dict[int, np.ndarray],
    max_pulls: int,
    save_path: Path,
    *,
    title: str = "",
    calc_n_limit: int = 15,
    user_data: list | None = None,
) -> None:
    """Plot a staircase fan chart showing UP count evolution against pull count.

    Draws symmetric percentile bands (inner to outer), an expectation curve,
    a median step line, and optional user data markers.

    Parameters
    ----------
    dists : dict[int, np.ndarray]
        Maps n_up -> CDF array.  Must cover n = 0 .. calc_n_limit.
        dists[n][i] = P(>= n UP | i pulls).
    max_pulls : int
        Maximum pull count on the x-axis.
    save_path : Path
        Output file path (parent directories created automatically).
    title : str
        Chart title (default "").
    calc_n_limit : int
        Upper n_up limit for expectation computation (default 15).
    user_data : list | None
        Optional list of (pulls, up_count) tuples for user markers.
    """
    save_path = _ensure_dir(save_path)
    cdfs_dict = dict(dists)
    # CDF for 0 UP is always 1
    if 0 not in cdfs_dict:
        cdfs_dict[0] = np.ones(max_pulls)
    pulls = np.arange(max_pulls)

    # 1. 计算分位点与期望
    alphas = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]
    bounds: dict[float, np.ndarray] = {a: np.zeros(max_pulls) for a in alphas}
    expectation = np.zeros(max_pulls)

    for i in range(max_pulls):
        # 修正：计算分位和期望时，视野必须涵盖到 calc_n_limit 金
        current_cdf_all = np.array([cdfs_dict[n][i] for n in range(calc_n_limit + 1)])

        # 期望线：无截断计算
        expectation[i] = np.sum(current_cdf_all[1:])

        for a in alphas:
            # 找到概率分位对应的实际金数
            idx = np.where(current_cdf_all >= (1 - a))[0]
            if len(idx) > 0:
                # 拿分位点对应的金数，但绘图区域限制在 calc_n_limit
                val = idx[-1]
                bounds[a][i] = min(val, calc_n_limit)
            else:
                bounds[a][i] = 0

    fig, ax = plt.subplots(figsize=(15, 10))

    # 2. 绘制渐变扇形区域 (由内向外对称填充)
    color_map = plt.get_cmap('Blues')

    # 按照区间对进行循环，确保每一对 low/high 都能生成 label
    pairs = [
        (0.4, 0.5, 0.5, 0.6),  # 40%-60%
        (0.3, 0.4, 0.6, 0.7),  # 30%-70%
        (0.2, 0.3, 0.7, 0.8),  # 20%-80%
        (0.1, 0.2, 0.8, 0.9),  # 10%-90%
        (0.01, 0.1, 0.9, 0.99),  # 1%-99%
    ]

    for i, (l_low, l_high, r_low, r_high) in enumerate(pairs):
        # 核心区深，边缘区浅
        color_val = 0.8 - (i * 0.12)
        c = color_map(color_val)
        alpha_val = 0.7 - i * 0.12

        # 绘制下方条带 (不加 label，避免重复)
        ax.fill_between(pulls, bounds[r_low], bounds[r_high],
                        color=c, alpha=alpha_val, linewidth=0.0, zorder=2)
        # 绘制上方条带 (添加要求的 label)
        # 使用你要求的格式: low*100% - high*100%
        label_str = f'{int(l_low * 100)}% - {int(r_high * 100)}% 区间'
        ax.fill_between(pulls, bounds[l_low], bounds[l_high],
                        color=c, alpha=alpha_val, linewidth=0.0, zorder=2,
                        label=label_str)

    # 3. 期望线与中位线
    ax.plot(pulls, expectation, color='black', linewidth=3, label='期望 UP 数', zorder=10)
    ax.step(pulls, bounds[0.5], where='post', color='black', linewidth=1.2,
            linestyle='--', alpha=0.5, label='中位数 (50%)', zorder=11)

    # 4. 动态切面 (期望整数点)
    accent_color = '#005f5f'
    for n in range(1, int(np.max(expectation)) + 1):
        idx = np.searchsorted(expectation, n)
        if idx < max_pulls:
            ax.vlines(idx, 0, n, colors=accent_color, linestyles='--', alpha=0.3, linewidth=1, zorder=12)
            ax.text(idx, 0.1, f'{idx}抽', ha='center', va='bottom', fontsize=10,
                    color=accent_color, fontweight='bold', alpha=0.9,
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
            ax.scatter(idx, n, color=accent_color, s=25, zorder=13, edgecolors='white')

    # 5. 用户数据点
    if user_data:
        for px, py in user_data:
            y_buff = -0.3
            ax.scatter(px, py + y_buff, color='white', edgecolors='black', s=120, zorder=25, linewidths=1.5)
            ax.scatter(px, py + y_buff, color='darkred', s=50, marker='X', zorder=26, linewidths=2,
                       label='实际记录' if px == user_data[0][0] else "")
            txt = ax.text(px + max_pulls * 0.015, py + y_buff, f'({px}抽, {py}UP)',
                          fontsize=12, fontweight='black', color='black', va='center', zorder=27)
            txt.set_path_effects([pe.withStroke(linewidth=3, foreground="white")])

    # 6. 格线
    ax.xaxis.set_major_locator(MultipleLocator(100))
    ax.xaxis.set_minor_locator(MultipleLocator(20))
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.grid(which='major', linestyle='-', alpha=0.3, color='black')
    ax.grid(which='minor', linestyle=':', alpha=0.3, color='black')

    # 7. 标题与标签
    ax.set_title(title, fontsize=22, pad=35)
    ax.set_xlabel("累计消耗抽数 (Pulls)", fontsize=14)
    ax.set_ylabel("获得 UP 角色总数 (n)", fontsize=14)
    ax.set_xlim(0, max_pulls)
    ax.set_ylim(0, calc_n_limit + 0.8)

    # 8. 图例优化
    # 我们按 zorder 反向获取，确保期望线在最前
    handles, labels = ax.get_legend_handles_labels()
    # 手动排序让图例更有逻辑：期望、中位、区间从内到外
    # 期望线(idx -3), 中位线(idx -2), 实际记录(idx -1), 其余是区间
    # 这种排序更符合直觉
    ax.legend(handles, labels, loc='upper left', frameon=True, shadow=True, ncol=2, fontsize=10)

    ax.text(1.0, -0.08, f'* 期望值基于前 {calc_n_limit} 个 UP 命座概率累加计算',
            transform=ax.transAxes,
            ha='right', va='top',       # ha='right' 对齐右边界，va='top' 向上对齐（即文本在点下方）
            fontsize=9, color='gray',
            alpha=0.8, fontstyle='italic')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
