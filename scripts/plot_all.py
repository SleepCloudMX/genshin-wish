#!/usr/bin/env python
"""Generate all standard plots for genshin-wish.

Run once after installing the package:
    python scripts/plot_all.py
"""

from pathlib import Path

import numpy as np

from genshin_wish._constants import STABLE_P, CHARACTER_POOL, WEAPON_POOL
from genshin_wish._gold import get_gold_pdfs
from genshin_wish.character import CharacterState, up_distribution, stable_up_distribution
from genshin_wish.weapon import WeaponState, WeaponTarget, weapon_up_distribution
from genshin_wish.viz._base import setup_style, MISS_LABELS, DEFAULT_ALPHAS, write_percentile_table
from genshin_wish.viz.cdf import plot_annotated_cdf, plot_up_cdf_lines
from genshin_wish.viz.heatmap import plot_percentile_heatmap
from genshin_wish.viz.column import plot_success_column_chart
from genshin_wish.viz.fan import plot_luck_fan
from genshin_wish.viz.stack import plot_stacked_up_probabilities
from genshin_wish.viz.staircase import plot_staircase_luck_fan
from genshin_wish.viz.multi_gold import plot_multi_gold
from genshin_wish.viz.pdf import plot_base_pdfs

setup_style()

OUTPUT = Path("output")
MAX_PULLS = 1000


def _stable_pdf_func(n_up: int) -> np.ndarray:
    """Return PDF for n_up UPs in steady state."""
    res: np.ndarray | None = None
    for m, w in enumerate(STABLE_P):
        pdf = up_distribution(CharacterState(pity=0, consecutive_loss=m), n_up).pdf
        if res is None:
            res = np.zeros(len(pdf))
        if len(res) < len(pdf):
            new_res = np.zeros(len(pdf))
            new_res[: len(res)] = res
            res = new_res
        res[: len(pdf)] += pdf * w
    return res


def _build_cdf_map(n_up: int) -> dict[str, np.ndarray]:
    """Build CDF map with miss=0..3 and stable keys for a given n_up."""
    cdf_map: dict[str, np.ndarray] = {}
    for miss in range(4):
        state = CharacterState(pity=0, consecutive_loss=miss)
        cdf_map[f"miss={miss}"] = up_distribution(state, n_up).cdf
    cdf_map["stable"] = np.cumsum(_stable_pdf_func(n_up))
    return cdf_map


def _build_cdfs_dict(k_miss: int | None, max_n: int, max_pulls: int) -> dict[int, np.ndarray]:
    """Build {n_up: padded_cdf} dict for stack/staircase plots."""
    cdfs: dict[int, np.ndarray] = {}
    for n in range(1, max_n + 1):
        if k_miss is None:
            cdf = np.cumsum(_stable_pdf_func(n))
        else:
            state = CharacterState(pity=0, consecutive_loss=k_miss)
            cdf = up_distribution(state, n).cdf
        padded = np.ones(max_pulls)
        length = min(len(cdf), max_pulls)
        padded[:length] = cdf[:length]
        cdfs[n] = padded
    return cdfs


# --- Character CDF ---

def plot_character_cdf() -> None:
    """CDF heatmap + table + per-miss annotated CDFs for n_up = 1..7."""
    for n_up in range(1, 8):
        root = OUTPUT / "character" / "cdf" / f"n={n_up}"
        root.mkdir(parents=True, exist_ok=True)

        cdf_map = _build_cdf_map(n_up)
        label = "满命" if n_up == 7 else f"{n_up - 1} 命"

        # Percentile table
        write_percentile_table(
            cdf_map,
            f"抽 {label} 分位点表",
            root / f"n={n_up}-table.md",
            alphas=[0.1, 0.3, 0.5, 0.7, 0.9, 0.99],
        )

        # Heatmap
        plot_percentile_heatmap(
            cdf_map,
            f"抽 {label} 所需抽数",
            root / f"n={n_up}-heatmap.png",
        )

        # Per-miss annotated CDF
        for miss in range(4):
            state = CharacterState(pity=0, consecutive_loss=miss)
            d = up_distribution(state, n_up)
            plot_annotated_cdf(
                d.cdf,
                f"抽 {label} CDF (已连歪 {miss} 次)",
                root / f"n={n_up},miss={miss}.png",
            )

        print(f"  Character CDF n={n_up} done")


# --- Character Fan ---

def plot_character_fan() -> None:
    """Fan charts for 3-interval and 5-interval."""
    for interval in [3, 5]:
        root = OUTPUT / "character" / f"fan-{interval}interval"
        root.mkdir(parents=True, exist_ok=True)

        for miss in range(4):
            def pdf_func(n: int, miss: int = miss) -> np.ndarray:
                return up_distribution(CharacterState(pity=0, consecutive_loss=miss), n).pdf

            plot_luck_fan(
                pdf_func,
                max_n_up=7,
                save_path=root / f"miss{miss}.png",
                interval_set=interval,
                title=f"已连续歪 {miss} 次",
            )

        plot_luck_fan(
            _stable_pdf_func,
            max_n_up=7,
            save_path=root / "stable.png",
            interval_set=interval,
            title="稳态",
        )

        print(f"  Character fan-{interval}interval done")


# --- Character Column ---

def plot_character_column() -> None:
    """Column charts."""
    root = OUTPUT / "character" / "column"
    root.mkdir(parents=True, exist_ok=True)

    for miss in range(4):
        def pdf_func(n: int, miss: int = miss) -> np.ndarray:
            return up_distribution(CharacterState(pity=0, consecutive_loss=miss), n).pdf

        plot_success_column_chart(pdf_func, max_n_up=7, save_path=root / f"miss{miss}.png",
                                  title=f"已连续歪 {miss} 次")

    plot_success_column_chart(_stable_pdf_func, max_n_up=7, save_path=root / "stable.png",
                              title="稳态")
    print("  Character column done")


# --- Character Rolls2Gold (multi-cdf, stack, staircase) ---

def plot_character_rolls2gold() -> None:
    """Multi-CDF line chart, stacked area, and staircase fan."""
    base = OUTPUT / "character" / "rolls2gold"

    # -- multi-cdf --
    root = base / "multi-cdf"
    root.mkdir(parents=True, exist_ok=True)
    for miss in range(4):
        cdfs = _build_cdfs_dict(miss, 7, MAX_PULLS)
        plot_up_cdf_lines(
            cdfs, MAX_PULLS, root / f"miss{miss}.png",
            title=f"【已连续歪 {miss} 次】获得各数量 UP 角色的累积概率 (CDF)",
        )
    stable_cdfs = _build_cdfs_dict(None, 7, MAX_PULLS)
    plot_up_cdf_lines(
        stable_cdfs, MAX_PULLS, root / "stable.png",
        title="【稳态】获得各数量 UP 角色的累积概率 (CDF)",
    )
    print("  Character rolls2gold/multi-cdf done")

    # -- stack --
    root = base / "stack"
    root.mkdir(parents=True, exist_ok=True)
    for miss in range(4):
        cdfs = _build_cdfs_dict(miss, 7, MAX_PULLS)
        plot_stacked_up_probabilities(cdfs, MAX_PULLS, root / f"miss{miss}.png",
                                      title=f"【已连续歪 {miss} 次】不同抽数下持有 UP 角色数量占比")
    plot_stacked_up_probabilities(stable_cdfs, MAX_PULLS, root / "stable.png",
                                  title="【稳态】不同抽数下持有 UP 角色数量占比")
    print("  Character rolls2gold/stack done")

    # -- staircase --
    root = base / "staircase"
    root.mkdir(parents=True, exist_ok=True)
    for miss in range(4):
        cdfs = _build_cdfs_dict(miss, 7, MAX_PULLS)
        plot_staircase_luck_fan(cdfs, MAX_PULLS, root / f"miss{miss}.png",
                                title=f"【已连续歪 {miss} 次】抽数-命座概率演化图")
    # Stable needs extended n_up range for accurate expectation
    stable_ext = _build_cdfs_dict(None, 15, MAX_PULLS)
    plot_staircase_luck_fan(stable_ext, MAX_PULLS, root / "stable.png",
                            title="【稳态】抽数-命座概率演化图", calc_n_limit=15)
    print("  Character rolls2gold/staircase done")


# --- Weapon ---

def plot_weapon() -> None:
    """Weapon banner plots."""
    root = OUTPUT / "weapon"
    root.mkdir(parents=True, exist_ok=True)

    pdfs = get_gold_pdfs(WEAPON_POOL)
    plot_base_pdfs(pdfs, root / "pdf.png")

    cdfs = [np.cumsum(p) for p in pdfs]
    for gold in range(1, 5):
        plot_annotated_cdf(
            cdfs[gold],
            f"出 {gold} 金所需抽数的累积分布函数",
            root / f"cdf-gold{gold}.png",
        )

    state = WeaponState(pity=0)
    d1 = weapon_up_distribution(state, WeaponTarget(count_a=1))
    plot_annotated_cdf(d1.cdf, "武器池：出一个 Up 所需抽数的累积分布函数",
                       root / "target-one-up.png")

    print("  Weapon done")


# --- Multi-Gold ---

def _pull10_prob(pdf1: np.ndarray, gold: int) -> float:
    """Estimate steady-state 10-pull multi-gold probability."""
    cdfs = [np.cumsum(p) for p in [np.array([1.0]), pdf1]]
    survival = 1.0 - cdfs[1][:-1]
    weights = survival / survival.sum()

    total = 0.0
    for d, w in enumerate(weights):
        shifted = np.insert(pdf1[d + 1:] / pdf1[d + 1:].sum(), 0, 0)[:11]
        result = shifted.copy()
        for _ in range(gold - 1):
            result = np.convolve(result, pdf1)[:11]
        total += result.sum() * w
    return total


def plot_multi_gold_viz() -> None:
    """Ten-pull multi-gold probability curves."""
    root = OUTPUT / "multi-gold"
    root.mkdir(parents=True, exist_ok=True)

    for name, pool in [("character", CHARACTER_POOL), ("weapon", WEAPON_POOL)]:
        pdfs_list = get_gold_pdfs(pool)
        p_gold = pdfs_list[1]

        for gold in range(2, 7):
            p = _pull10_prob(p_gold, gold)
            if p > 1e-7:
                label = "角色" if name == "character" else "武器"
                plot_multi_gold(
                    p,
                    f"稳态下{label}池十连 {gold} 金",
                    root / f"{name}-{gold}gold.png",
                )
    print("  Multi-gold done")


# --- Main ---

def main() -> None:
    print("Generating all plots...")

    plot_character_cdf()
    plot_character_fan()
    plot_character_column()
    plot_character_rolls2gold()
    plot_weapon()
    plot_multi_gold_viz()

    print("\nAll plots generated in output/")


if __name__ == "__main__":
    main()
