"""Long-term luck-distribution fan chart over many UP acquisitions."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from genshin_wish.viz._base import INTERVAL_COLORS_3, INTERVAL_COLORS_5


def _build_configs(interval_set: int) -> list[dict]:
    raw = INTERVAL_COLORS_5 if interval_set == 5 else INTERVAL_COLORS_3
    return [
        {'a': e['a'], 'color': e['color'],
         'label': f"{int(e['a']*100)}%-{int((1-e['a'])*100)}%"}
        for e in raw
    ]


# ---------------------------------------------------------------------------
# 3-interval rendering  (ref: plot_long_term_luck)
# ---------------------------------------------------------------------------
def _render_long_term_3(
    solver_func, N: int, n_start: int, save_path: Path, title: str
) -> None:
    alpha_configs = _build_configs(3)
    target_alphas = [0.01, 0.1, 0.3, 0.7, 0.9, 0.99]
    solver_alphas = [0.3, 0.1, 0.01]

    total = n_start + N
    raw_data = solver_func(total, solver_alphas)
    up_axis = np.arange(n_start + 1, total + 1)

    # --- data transform: cumulative → per-UP average ---
    all_bounds_avg: dict[float, list[float]] = {a: [] for a in target_alphas}
    for i, n in enumerate(up_axis):
        for a_base in solver_alphas:
            low, high = raw_data[a_base][n_start + i]
            all_bounds_avg[a_base].append(low / n)
            all_bounds_avg[round(1 - a_base, 2)].append(high / n)

    mid_a = 0.3
    lo_last, hi_last = raw_data[mid_a][-1]
    mu_single = float((lo_last + hi_last) / 2 / total)
    expectations_avg = np.full(N, mu_single)

    plt.figure(figsize=(18, 11))

    # --- shadow bands ---
    plt.fill_between(up_axis, all_bounds_avg[0.3], all_bounds_avg[0.7],
                     color='#1f77b4', alpha=0.3, label='30%-70% 区间', zorder=2)
    plt.fill_between(up_axis, all_bounds_avg[0.1], all_bounds_avg[0.3],
                     color='#ff7f0e', alpha=0.2, zorder=1)
    plt.fill_between(up_axis, all_bounds_avg[0.7], all_bounds_avg[0.9],
                     color='#ff7f0e', alpha=0.2, label='10%-90% 区间', zorder=1)
    plt.fill_between(up_axis, all_bounds_avg[0.01], all_bounds_avg[0.1],
                     color='#d62728', alpha=0.15, zorder=0)
    plt.fill_between(up_axis, all_bounds_avg[0.9], all_bounds_avg[0.99],
                     color='#d62728', alpha=0.15, label='1%-99% 区间', zorder=0)

    # --- expectation reference ---
    plt.axhline(mu_single, color='black', linewidth=1.5, linestyle='--',
                label=f'理论均值 ({mu_single:.1f})', zorder=10)

    # --- sampled annotations (every 10th, from 10) ---
    label_indices = [i for i in range(len(up_axis))
                     if (n_start + i + 1) >= 10 and (n_start + i + 1) % 10 == 0]
    if (N - 1) not in label_indices:
        label_indices.append(N - 1)

    for i in label_indices:
        n = up_axis[i]

        # Vertical guide from y=0 to outermost bound
        top_y = all_bounds_avg[0.99][i]
        plt.vlines(n, ymin=0, ymax=top_y, colors='gray', linestyles=':',
                   alpha=0.4, zorder=1)

        curr_vals = [
            (all_bounds_avg[0.99][i], '99%', '#d62728'),
            (all_bounds_avg[0.9][i],  '90%', '#ff7f0e'),
            (all_bounds_avg[0.7][i],  '70%', '#1f77b4'),
            (mu_single,               'Avg', 'black'),
            (all_bounds_avg[0.3][i],  '30%', '#1f77b4'),
            (all_bounds_avg[0.1][i],  '10%', '#ff7f0e'),
            (all_bounds_avg[0.01][i], '1%',  '#d62728'),
        ]
        curr_vals.sort(key=lambda x: x[0], reverse=True)

        last_y = 9999.0
        for _idx, (val, label, col) in enumerate(curr_vals):
            if label == 'Avg':
                x_off, ha, y_pos = 0.002 * N, 'left', val + 1.2
                weight = 'extra bold'
            else:
                x_off = 0.002 * N
                ha = 'left'
                y_pos, weight = val, 'bold'

            if last_y - y_pos < 1.0:
                y_pos = last_y - 1.0

            plt.text(n + x_off, y_pos, f"{val:.1f}", color=col, ha=ha,
                     va='center', fontsize=7, fontweight=weight, zorder=15)
            last_y = y_pos

    # --- styling ---
    plt.title(title, fontsize=20, pad=30)
    plt.xlabel("获取 UP 角色总数 (n)", fontsize=14)
    plt.ylabel("单位平均消耗 (总抽数/n)", fontsize=14)

    plt.yticks(np.arange(0, 201, 10))
    plt.ylim(mu_single - 40, mu_single + 50)
    plt.xlim(n_start, total + (0.05 * N))

    plt.grid(axis='y', linestyle=':', alpha=0.5)
    plt.legend(loc='upper right', frameon=True, fontsize=11, ncol=2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


# ---------------------------------------------------------------------------
# 5-interval rendering  (ref: plot_long_term_luck_5)
# ---------------------------------------------------------------------------
def _render_long_term_5(
    solver_func, N: int, n_start: int, save_path: Path, title: str
) -> None:
    alpha_configs = _build_configs(5)
    target_alphas = [0.01, 0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 0.99]

    total = n_start + N
    raw_data = solver_func(total, target_alphas)
    up_axis = np.arange(n_start + 1, total + 1)

    # --- data transform: cumulative → per-UP average ---
    all_bounds_avg: dict[float, list[float]] = {a: [] for a in target_alphas}
    expectations_avg: list[float] = []

    mid_a = 0.4
    lo_last, hi_last = raw_data[mid_a][-1]
    mu_single = float((lo_last + hi_last) / 2 / total)

    for i, n in enumerate(up_axis):
        idx = n_start + i
        for a in target_alphas:
            if a < 0.5:
                val = raw_data[a][idx][0] / n
            else:
                val = raw_data[round(1 - a, 2)][idx][1] / n
            all_bounds_avg[a].append(val)
        expectations_avg.append(mu_single)

    plt.figure(figsize=(16, 11))

    # --- shadow bands ---
    sorted_alphas = [0.4, 0.3, 0.2, 0.1, 0.01]
    for i, a in enumerate(sorted_alphas):
        low = np.array(all_bounds_avg[a])
        high = np.array(all_bounds_avg[round(1 - a, 2)])

        if i == 0:
            plt.fill_between(up_axis, low, high, color=alpha_configs[i]['color'],
                             alpha=0.4, label=alpha_configs[i]['label'], zorder=5 - i)
        else:
            prev_low = np.array(all_bounds_avg[sorted_alphas[i - 1]])
            prev_high = np.array(all_bounds_avg[round(1 - sorted_alphas[i - 1], 2)])
            plt.fill_between(up_axis, low, prev_low, color=alpha_configs[i]['color'],
                             alpha=0.25, zorder=5 - i)
            plt.fill_between(up_axis, prev_high, high, color=alpha_configs[i]['color'],
                             alpha=0.25, label=alpha_configs[i]['label'], zorder=5 - i)

    # --- expectation line ---
    plt.plot(up_axis, expectations_avg, color='black', linewidth=1.5,
             linestyle='--', label='单位理论期望', zorder=10)

    # --- sampled annotations ---
    if N <= 10:
        label_indices = list(range(len(up_axis)))
    else:
        sample_pts = [1, 5, 10, 20, 50, 100, 200, 500, total]
        label_indices = [i - 1 - n_start for i in sample_pts if n_start < i <= total]
        if (N - 1) not in label_indices:
            label_indices.append(N - 1)

    for i in label_indices:
        n = up_axis[i]
        vals = [(all_bounds_avg[a][i], f"{int(a * 100)}%", a)
                for a in target_alphas]
        vals.append((expectations_avg[i], 'Avg', 0.5))
        vals.sort(key=lambda x: x[0], reverse=True)

        last_y = 9999.0
        for idx, (val, label, alpha_val) in enumerate(vals):
            if label == 'Avg':
                color, font_weight, z_order = '#000000', 'extra bold', 15
                x_offset, ha, y_pos = 0.01 * N, 'left', val + 1.2
            else:
                color = 'black'
                for cfg in alpha_configs:
                    if (abs(alpha_val - cfg['a']) < 0.001
                            or abs((1 - alpha_val) - cfg['a']) < 0.001):
                        color = cfg['color']
                font_weight, z_order = 'bold', 12
                x_offset = (0.005 * N) if idx % 2 == 0 else (-0.005 * N)
                ha = 'left' if idx % 2 == 0 else 'right'
                y_pos = val

            if last_y - y_pos < 3.5:
                y_pos = last_y - 3.5

            plt.text(n + x_offset, y_pos, f"{val:.1f}",
                     color=color, ha=ha, va='center',
                     fontsize=8 if N < 50 else 7,
                     fontweight=font_weight, zorder=z_order)
            last_y = y_pos

    # --- styling ---
    if N <= 20:
        plt.xticks(up_axis)

    plt.title(title, fontsize=18, pad=30)
    plt.xlabel("获取 UP 角色总数 (n)", fontsize=12)
    plt.ylabel("平均每个UP消耗抽数 (总数/n)", fontsize=12)

    plt.yticks(np.arange(0, 201, 20))
    plt.ylim(max(0, mu_single - 60), min(200, mu_single + 80))
    plt.xlim(n_start, total + (0.05 * N))

    plt.legend(loc='upper right', frameon=True, fontsize=9, ncol=2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def plot_long_term_luck(
    solver_func,
    N: int,
    save_path: str | Path,
    *,
    interval_set: int = 3,
    title: str | None = None,
    n_start: int = 0,
) -> None:
    """Plot a long-term luck-distribution fan chart.

    Parameters
    ----------
    solver_func : callable
        ``solver_func(N, alphas) -> {alpha: [(low, high) for n = 1 … N]}``
    N : int
        Number of UPs to show in this chart.
    save_path : str or Path
        Output image path (PNG).
    interval_set : int
        Number of probability bands: 3 (default) or 5.
    title : str, optional
        Chart title.
    n_start : int
        Starting UP index (0-based).  Shows UPs n_start+1 … n_start+N.
    """
    sp = Path(save_path)
    if title is None:
        total = n_start + N
        title = "长期欧非演变"

    if interval_set == 3:
        _render_long_term_3(solver_func, N, n_start, sp, title)
    else:
        _render_long_term_5(solver_func, N, n_start, sp, title)
