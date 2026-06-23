"""Fan chart visualization for luck distribution over constellation / UP counts."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from genshin_wish._constants import STABLE_P
from genshin_wish.viz._base import INTERVAL_COLORS_3, INTERVAL_COLORS_5


def _build_configs(interval_set: int) -> list[dict]:
    """Build alpha config dicts with human-readable labels."""
    raw = INTERVAL_COLORS_5 if interval_set == 5 else INTERVAL_COLORS_3
    return [
        {'a': e['a'], 'color': e['color'],
         'label': f"{int(e['a']*100)}%-{int((1-e['a'])*100)}%"}
        for e in raw
    ]


# ---------------------------------------------------------------------------
# 3-interval rendering
# ---------------------------------------------------------------------------
def _render_fan_3(pdf_func, max_n_up: int, save_path: Path, title: str) -> None:
    from genshin_wish.viz._base import setup_style
    setup_style()
    alpha_configs = _build_configs(3)

    up_axis = np.arange(1, max_n_up + 1)
    expectations_avg: list[float] = []

    all_bounds: dict[float, list[float]] = {
        0.01: [], 0.10: [], 0.30: [], 0.70: [], 0.90: [], 0.99: [],
    }

    for n in up_axis:
        pdf = pdf_func(n)
        cdf = np.cumsum(pdf)
        expectations_avg.append(float(np.sum(np.arange(len(pdf)) * pdf)) / n)

        for a in [0.01, 0.10, 0.30, 0.70, 0.90, 0.99]:
            val = float(np.searchsorted(cdf, a)) / n
            all_bounds[a].append(val)

    plt.figure(figsize=(16, 10))

    low30, high30 = np.array(all_bounds[0.30]), np.array(all_bounds[0.70])
    low10, high10 = np.array(all_bounds[0.10]), np.array(all_bounds[0.90])
    low01, high01 = np.array(all_bounds[0.01]), np.array(all_bounds[0.99])

    plt.fill_between(up_axis, low30, high30, color='#1f77b4', alpha=0.3,
                     label='30%-70% 区间', zorder=2)
    plt.fill_between(up_axis, low10, low30, color='#ff7f0e', alpha=0.2, zorder=1)
    plt.fill_between(up_axis, high30, high10, color='#ff7f0e', alpha=0.2,
                     label='10%-90% 区间', zorder=1)
    plt.fill_between(up_axis, low01, low10, color='#d62728', alpha=0.15, zorder=0)
    plt.fill_between(up_axis, high10, high01, color='#d62728', alpha=0.15,
                     label='1%-99% 区间', zorder=0)

    line_style = dict(linestyle='--', linewidth=0.8, alpha=0.4)
    for a, color in [(0.01, '#d62728'), (0.10, '#ff7f0e'), (0.30, '#1f77b4'),
                     (0.70, '#1f77b4'), (0.90, '#ff7f0e'), (0.99, '#d62728')]:
        plt.plot(up_axis, all_bounds[a], color=color, **line_style)

    plt.plot(up_axis, expectations_avg, color='black', linewidth=2, marker='o',
             markersize=6, label='期望', zorder=10)

    for i, n in enumerate(up_axis):
        vals_to_plot = [
            (all_bounds[0.99][i], '99%', '#d62728'),
            (all_bounds[0.90][i], '90%', '#ff7f0e'),
            (all_bounds[0.70][i], '70%', '#1f77b4'),
            (expectations_avg[i], 'Avg', 'black'),
            (all_bounds[0.30][i], '30%', '#1f77b4'),
            (all_bounds[0.10][i], '10%', '#ff7f0e'),
            (all_bounds[0.01][i], '1%',  '#d62728'),
        ]
        last_y = 999.0
        for val, _label, col in vals_to_plot:
            y_pos = val
            if last_y - val < 5:
                y_pos = val - 3
            plt.text(n + 0.05, y_pos, f"{val:.1f}", color=col, ha='left',
                     va='center', fontsize=8, fontweight='bold', alpha=0.9)
            last_y = y_pos

    plt.title(title, fontsize=16, pad=25)
    plt.xlabel("目标命座", fontsize=12)
    plt.ylabel("平均每UP消耗抽数 (总数/UP数)", fontsize=12)
    plt.xticks(up_axis, [f"{i-1}命" for i in up_axis])
    plt.yticks(np.arange(0, 181, 20))
    plt.ylim(0, 185)
    plt.grid(axis='y', linestyle=':', alpha=0.5)
    plt.legend(loc='upper right', frameon=True, fontsize=10)
    plt.axhline(160, color='red', linestyle=':', alpha=0.3)
    plt.text(0.6, 162, "极限大保底参考 (160抽/UP)", color='red', fontsize=9, alpha=0.6)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


# ---------------------------------------------------------------------------
# 5-interval rendering
# ---------------------------------------------------------------------------
def _render_fan_5(pdf_func, max_n_up: int, save_path: Path, title: str) -> None:
    from genshin_wish.viz._base import setup_style
    setup_style()
    alpha_configs = _build_configs(5)  # sorted inner→outer: 0.40,0.30,0.20,0.10,0.01

    up_axis = np.arange(1, max_n_up + 1)
    expectations_avg: list[float] = []

    target_alphas = [0.01, 0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 0.99]
    all_bounds: dict[float, list[float]] = {a: [] for a in target_alphas}

    for n in up_axis:
        pdf = pdf_func(n)
        cdf = np.cumsum(pdf)
        expectations_avg.append(float(np.sum(np.arange(len(pdf)) * pdf)) / n)

        for a in target_alphas:
            val = float(np.searchsorted(cdf, a)) / n
            all_bounds[a].append(val)

    plt.figure(figsize=(16, 11))

    sorted_alphas = [0.4, 0.3, 0.2, 0.1, 0.01]
    for i, a in enumerate(sorted_alphas):
        low = np.array(all_bounds[a])
        high = np.array(all_bounds[round(1 - a, 2)])

        if i == 0:
            plt.fill_between(up_axis, low, high, color=alpha_configs[i]['color'],
                             alpha=0.4, label=alpha_configs[i]['label'], zorder=5 - i)
        else:
            prev_low = np.array(all_bounds[sorted_alphas[i - 1]])
            prev_high = np.array(all_bounds[round(1 - sorted_alphas[i - 1], 2)])
            plt.fill_between(up_axis, low, prev_low, color=alpha_configs[i]['color'],
                             alpha=0.25, zorder=5 - i)
            plt.fill_between(up_axis, prev_high, high, color=alpha_configs[i]['color'],
                             alpha=0.25, label=alpha_configs[i]['label'], zorder=5 - i)

    plt.plot(up_axis, expectations_avg, color='black', linewidth=2.5, marker='s',
             markersize=5, label='期望', zorder=10)

    for i, n in enumerate(up_axis):
        vals = [(all_bounds[a][i], f"{int(a * 100)}%", a) for a in target_alphas]
        vals.append((expectations_avg[i], 'Avg', 0.5))
        vals.sort(key=lambda x: x[0], reverse=True)

        last_y = 999.0
        for idx, (val, label, alpha_val) in enumerate(vals):
            if label == 'Avg':
                color = '#000000'
                font_weight = 'extra bold'
                z_order = 15
                x_offset = 0.15
                ha = 'left'
                y_pos = val + 1.5
            else:
                color = 'black'
                for cfg in alpha_configs:
                    if (abs(alpha_val - cfg['a']) < 0.001
                            or abs((1 - alpha_val) - cfg['a']) < 0.001):
                        color = cfg['color']
                font_weight = 'bold'
                z_order = 12
                x_offset = 0.07 if idx % 2 == 0 else -0.07
                ha = 'left' if idx % 2 == 0 else 'right'
                y_pos = val

            if last_y - y_pos < 3.8:
                y_pos = last_y - 3.8

            plt.text(n + x_offset, y_pos, f"{val:.1f}",
                     color=color, ha=ha, va='center',
                     fontsize=8, fontweight=font_weight, zorder=z_order)
            last_y = y_pos

    plt.title(title, fontsize=18, pad=30)
    plt.xlabel("目标命座 (包含角色本体)", fontsize=12)
    plt.ylabel("平均每个UP消耗抽数 (总数/UP数)", fontsize=12)
    plt.xticks(up_axis, [f"{i-1}命" for i in up_axis])
    plt.yticks(np.arange(0, 181, 20))
    plt.ylim(0, 185)
    plt.grid(linestyle=':', alpha=0.5)
    plt.legend(loc='upper right', bbox_to_anchor=(1, 1), frameon=True,
               fontsize=9, ncol=2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def plot_luck_fan(
    pdf_func,
    max_n_up: int,
    save_path: str | Path,
    *,
    interval_set: int = 5,
    title: str | None = None,
) -> None:
    """Plot a fan chart showing luck-distribution evolution per UP.

    Parameters
    ----------
    pdf_func : callable
        ``pdf_func(n_up: int) -> np.ndarray``
        Returns the 1-D PDF (probability mass function) for exactly *n_up*
        UPs.  The array index is the total pull count.
    max_n_up : int
        Maximum number of UPs on the x-axis (1 … max_n_up).
    save_path : str or Path
        Output image path (PNG).
    interval_set : int
        Number of probability bands: 3 or 5 (default 5).
    title : str, optional
        Chart title.  Falls back to a sensible default when *None*.
    """
    sp = Path(save_path)
    if title is None:
        title = ("欧非分布演变图 (单位平均成本视角)"
                 if interval_set == 3 else "欧非分布")

    if interval_set == 3:
        _render_fan_3(pdf_func, max_n_up, sp, title)
    else:
        _render_fan_5(pdf_func, max_n_up, sp, title)
