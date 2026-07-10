"""Player luck percentile chart — compares personal pull history to theoretical distribution."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from genshin_wish._player_pulls import PlayerPulls

# Symmetric percentile pairs with colors from fan chart interval colors
_PERCENTILE_PAIRS: list[tuple[float, str]] = [
    (0.01, '#cb181d'),
    (0.10, '#f16913'),
    (0.20, '#4292c6'),
    (0.30, '#2171b5'),
    (0.40, '#084594'),
]

_PLAYER_COLOR = '#27ae60'
_MARGINAL_COLOR = '#1e8449'


def _resolve_single_up(val: str, n_up: int) -> bool:
    if val == "auto":
        return n_up <= 50
    return val == "true"


def _resolve_q(val: str, n_up: int) -> tuple[str, int | None]:
    """Return (mode, step). mode: "all" | "stepped" | "off"."""
    if val == "off":
        return ("off", None)
    if val == "all":
        return ("all", 1)
    # auto
    if n_up <= 20:
        return ("all", 1)
    elif n_up <= 50:
        return ("stepped", max(1, n_up // 7))
    else:
        return ("off", None)


def _resolve_width(val: str, n_up: int, has_annotations: bool) -> int:
    if val == "fixed" or not has_annotations or n_up <= 20:
        return 16
    if n_up <= 50:
        return min(16 + int((n_up - 20) * 0.8), 40)
    return 40


def _reconstruct_states(
    pp: PlayerPulls, initial_loss: int, initial_guaranteed: bool
) -> list[tuple[int, bool]]:
    """Reconstruct (k_miss, guaranteed) state before each UP."""
    km = initial_loss
    gtd = initial_guaranteed
    states: list[tuple[int, bool]] = []
    for is_win in pp.is_direct_win:
        states.append((km, gtd))
        if is_win:
            km = 0
            gtd = False
        else:
            km = min(km + 1, 3)
            km = 0
            gtd = False
    return states


def plot_player_luck(
    pdf_func,
    player_cum: list[int],
    max_n_up: int,
    save_path: str | Path,
    *,
    title: str | None = None,
    player_pulls: PlayerPulls | None = None,
    initial_loss: int = 0,
    initial_guaranteed: bool = False,
    single_up: str = "auto",
    quantile_annot: str = "auto",
    width_mode: str = "auto",
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
    player_pulls : PlayerPulls, optional
        Required for per-segment marginal annotations.
    initial_loss : int
        Starting k_miss (0..3) for state reconstruction.
    initial_guaranteed : bool
        Starting guaranteed flag for state reconstruction.
    single_up : str
        ``"auto"``, ``"true"``, or ``"false"`` — per-segment marginal annotations.
    quantile_annot : str
        ``"auto"``, ``"all"``, or ``"off"`` — quantile reference line number labels.
    width_mode : str
        ``"auto"`` or ``"fixed"`` — adaptive figure width vs always 16".
    """
    from genshin_wish.character import CharacterState, up_distribution
    from genshin_wish.viz._base import setup_style
    setup_style()

    # --- resolve auto config ---
    up_axis = np.arange(1, max_n_up + 1)
    show_single_up = _resolve_single_up(single_up, max_n_up)
    q_mode, q_step = _resolve_q(quantile_annot, max_n_up)
    has_annotations = show_single_up or (q_mode != "off")
    fig_w = _resolve_width(width_mode, max_n_up, has_annotations)

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

    # --- compute marginal percentiles ---
    marginal_pct: list[float] = []
    if show_single_up and player_pulls is not None and player_pulls.is_direct_win:
        states = _reconstruct_states(player_pulls, initial_loss, initial_guaranteed)
        from genshin_wish.character import CharacterState, up_distribution
        for i, pulls in enumerate(player_pulls.per_up):
            km, gtd = states[i]
            state = CharacterState(guaranteed=gtd, pity=0, consecutive_loss=km)
            dist = up_distribution(state, n_up=1)
            idx = min(pulls, len(dist.cdf) - 1)
            marginal_pct.append(float(dist.cdf[idx]) * 100)
    else:
        marginal_pct = [float('nan')] * len(player_cum)

    plt.figure(figsize=(fig_w, 10))

    # --- horizontal reference lines ---
    for a, color in _PERCENTILE_PAIRS:
        lo_pct = a * 100
        hi_pct = (1 - a) * 100
        plt.axhline(y=lo_pct, color=color, linestyle='--', linewidth=0.8, alpha=0.35)
        plt.axhline(y=hi_pct, color=color, linestyle='--', linewidth=0.8, alpha=0.35)

    plt.axhline(y=50, color='#555555', linestyle='--', linewidth=0.8, alpha=0.35)

    # --- annotations on horizontal lines ---
    if q_mode != "off":
        step = q_step if q_step is not None else 1
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

                if abs(a - 0.99) < 0.001:
                    y_pos = pct - 0
                    va = 'top'
                else:
                    y_pos = pct + 0
                    va = 'bottom'

                plt.text(n + 0.05, y_pos, f"{val:.0f}",
                         color=color, ha='left', va=va,
                         fontsize=7, fontweight='bold', alpha=0.9)

    # --- player curve ---
    n_player = sum(1 for p in player_pct if not np.isnan(p))
    if n_player > 0:
        plt.plot(up_axis[:n_player], player_pct[:n_player],
                 color=_PLAYER_COLOR, linewidth=2.5, marker='o',
                 markersize=7, label='玩家记录', zorder=20)

        for i in range(n_player):
            plt.text(up_axis[i] + 0.05, player_pct[i] - 1.5,
                     f"{player_pct[i]:.1f}%",
                     color='black', ha='left', va='top',
                     fontsize=9, fontweight='bold', zorder=21)

        # --- marginal annotations on segments ---
        if show_single_up and n_player >= 2:
            ax = plt.gca()
            # Compute display scale from figure/axes geometry (works before draw)
            fig = ax.figure
            bbox = ax.get_position()
            fig_w, fig_h = fig.get_size_inches()
            ax_w = bbox.width * fig_w * fig.dpi
            ax_h = bbox.height * fig_h * fig.dpi
            x_range = ax.get_xlim()[1] - ax.get_xlim()[0]
            y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
            sx = ax_w / x_range  # pixels per data unit (x)
            sy = ax_h / y_range  # pixels per data unit (y)

            for i in range(1, n_player):
                mp = marginal_pct[i]
                if np.isnan(mp):
                    continue
                x1, x2 = float(up_axis[i - 1]), float(up_axis[i])
                y1, y2 = player_pct[i - 1], player_pct[i]
                # Segment vector in display pixels
                dx = (x2 - x1) * sx
                dy = (y2 - y1) * sy
                angle = np.degrees(np.arctan2(dy, dx))
                # Perpendicular offset ("above" the segment), rotated 90° CCW
                perp_dx, perp_dy = -dy, dx
                nrm = np.hypot(perp_dx, perp_dy)
                if nrm < 1e-9:
                    continue
                perp_dx /= nrm
                perp_dy /= nrm
                # Midpoint in display coords
                disp_x_mid = (x1 + x2) / 2 * sx
                disp_y_mid = (y1 + y2) / 2 * sy
                offset = 10  # pixels
                x_pos = (disp_x_mid + perp_dx * offset) / sx
                y_pos = (disp_y_mid + perp_dy * offset) / sy

                ax.text(x_pos, y_pos, f"非于{mp:.0f}%",
                        color=_MARGINAL_COLOR, ha='center', va='center',
                        fontsize=8, fontweight='normal', rotation=angle, alpha=0.7,
                        zorder=19)

    # --- styling ---
    plt.title(title or "整体欧非趋势", fontsize=18, pad=25)
    plt.xlabel("限定五星数量", fontsize=12)
    plt.ylabel("比百分之多少的玩家非 (%)", fontsize=12)

    # xtick labels
    if max_n_up <= 7:
        tick_labels = [f"{i-1}命" if i > 1 else "本体" for i in up_axis]
        tick_positions = up_axis
    elif max_n_up <= 40:
        tick_labels = [str(i) for i in up_axis]
        tick_positions = up_axis
    else:
        step = 5
        tick_positions = up_axis[::step]
        tick_labels = [str(i) for i in tick_positions]
    plt.xticks(tick_positions, tick_labels,
               fontsize=8 if max_n_up > 40 else None)

    plt.ylim(0, 100)
    plt.yticks(np.arange(0, 101, 10))
    plt.grid(axis='y', linestyle=':', alpha=0.5)
    plt.grid(axis='x', linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
