"""Player luck percentile chart — compares personal pull history to theoretical distribution."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt


# Symmetric percentile pairs with colors from fan chart interval colors
_PERCENTILE_PAIRS: list[tuple[float, str]] = [
    (0.01, '#cb181d'),
    (0.10, '#f16913'),
    (0.20, '#4292c6'),
    (0.30, '#2171b5'),
    (0.40, '#084594'),
]

_PLAYER_COLOR = '#27ae60'


def plot_player_luck(
    pdf_func,
    player_cum: list[int],
    max_n_up: int,
    save_path: str | Path,
    *,
    title: str | None = None,
) -> None:
    """Plot a percentile chart comparing a player's pull history to the distribution.

    Parameters
    ----------
    pdf_func : callable
        ``pdf_func(n_up: int) -> np.ndarray``
    player_cum : list[int]
        Cumulative total pulls after each UP.
    max_n_up : int
        Maximum number of UPs on the x-axis.
    save_path : str or Path
        Output image path (PNG).
    title : str, optional
    """
    from genshin_wish.viz._base import setup_style
    setup_style()

    up_axis = np.arange(1, max_n_up + 1)
    target_alphas = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]

    # --- compute percentile reference data ---
    ref_pulls: dict[float, list[float]] = {a: [] for a in target_alphas}
    for n in up_axis:
        pdf = pdf_func(n)
        cdf = np.cumsum(pdf)
        for a in target_alphas:
            ref_pulls[a].append(float(np.searchsorted(cdf, a)))

    # --- compute player percentiles ---
    player_pct: list[float] = []
    for i, n in enumerate(up_axis):
        if i < len(player_cum):
            pdf = pdf_func(n)
            cdf = np.cumsum(pdf)
            total = player_cum[i]
            pct = float(cdf[min(total, len(cdf) - 1)]) * 100
            player_pct.append(pct)
        else:
            player_pct.append(float('nan'))

    plt.figure(figsize=(16, 10))

    # --- horizontal reference lines ---
    for a, color in _PERCENTILE_PAIRS:
        lo_pct = a * 100
        hi_pct = (1 - a) * 100
        plt.axhline(y=lo_pct, color=color, linestyle='--', linewidth=0.8, alpha=0.35)
        plt.axhline(y=hi_pct, color=color, linestyle='--', linewidth=0.8, alpha=0.35)

    plt.axhline(y=50, color='#555555', linestyle='--', linewidth=0.8, alpha=0.35)

    # --- annotations on horizontal lines ---
    step = 1 if max_n_up <= 10 else max(1, max_n_up // 7)
    annot_alphas = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]
    for a in annot_alphas:
        pct = a * 100
        for i in range(0, max_n_up, step):
            n = up_axis[i]
            val = ref_pulls[a][i]
            color = '#555555' if abs(a - 0.5) < 0.001 else 'black'
            for lo, c in _PERCENTILE_PAIRS:
                if abs(a - lo) < 0.001 or abs(a - (1 - lo)) < 0.001:
                    color = c
                    break

            plt.text(n + 0.05, pct + 1.5, f"{val:.0f}",
                     color=color, ha='left', va='bottom',
                     fontsize=7, fontweight='bold', alpha=0.9)

    # --- player curve ---
    n_player = sum(1 for p in player_pct if not np.isnan(p))
    if n_player > 0:
        plt.plot(up_axis[:n_player], player_pct[:n_player],
                 color=_PLAYER_COLOR, linewidth=2.5, marker='o',
                 markersize=7, label='你的百分位', zorder=20)

        for i in range(n_player):
            plt.text(up_axis[i] + 0.05, player_pct[i] + 0.8,
                     f"{player_pct[i]:.1f}%",
                     color=_PLAYER_COLOR, ha='left', va='bottom',
                     fontsize=9, fontweight='bold', zorder=21)

    # --- styling ---
    plt.title(title or "抽卡百分位对照图", fontsize=18, pad=25)
    plt.xlabel("已获得限定数", fontsize=12)
    plt.ylabel("超过百分之多少的玩家 (%)", fontsize=12)
    plt.xticks(up_axis, [f"{i-1}命" if i > 1 else "本体" for i in up_axis])
    plt.ylim(0, 100)
    plt.yticks(np.arange(0, 101, 10))
    plt.grid(axis='y', linestyle=':', alpha=0.5)
    if n_player > 0:
        plt.legend(loc='lower right', frameon=True, fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
