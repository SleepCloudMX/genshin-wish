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


def _stable_pdf_func(n_up):
    """Return PDF for n_up UPs in steady state."""
    res = None
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


def plot_character_cdf() -> None:
    """CDF + heatmap for n_up = 1..7."""
    for n_up in range(1, 8):
        root = OUTPUT / "character" / "cdf"
        root.mkdir(parents=True, exist_ok=True)

        cdf_map = {}
        for miss in range(4):
            state = CharacterState(pity=0, consecutive_loss=miss)
            d = up_distribution(state, n_up)
            cdf_map[f"miss={miss}"] = d.cdf
        cdf_map["stable"] = np.cumsum(_stable_pdf_func(n_up))

        # Percentile table
        write_percentile_table(
            cdf_map,
            f"抽 {'满命' if n_up == 7 else f'{n_up - 1} 命'} 分位点表",
            root / f"n{n_up}-table.md",
            alphas=[0.1, 0.3, 0.5, 0.7, 0.9, 0.99],
        )

        # Heatmap
        plot_percentile_heatmap(
            cdf_map,
            f"抽 {'满命' if n_up == 7 else f'{n_up - 1} 命'} 所需抽数",
            root / f"n{n_up}-heatmap.png",
        )

        if n_up == 7:
            print(f"  Character CDF n={n_up} done")


def plot_character_fan() -> None:
    """Fan charts for 3-interval and 5-interval."""
    for interval in [3, 5]:
        root = OUTPUT / "character" / f"fan-{interval}interval"
        root.mkdir(parents=True, exist_ok=True)

        for miss in range(4):
            def pdf_func(n, miss=miss):
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


def plot_character_column() -> None:
    """Column charts."""
    root = OUTPUT / "character" / "column"
    root.mkdir(parents=True, exist_ok=True)

    for miss in range(4):
        def pdf_func(n, miss=miss):
            return up_distribution(CharacterState(pity=0, consecutive_loss=miss), n).pdf

        plot_success_column_chart(pdf_func, max_n_up=7, save_path=root / f"miss{miss}.png",
                                  title=f"已连续歪 {miss} 次")

    plot_success_column_chart(_stable_pdf_func, max_n_up=7, save_path=root / "stable.png",
                              title="稳态")
    print("  Character column done")


def plot_character_stack() -> None:
    """Stacked area and staircase charts."""
    for kind, func in [("stack", plot_stacked_up_probabilities),
                        ("staircase", plot_staircase_luck_fan)]:
        root = OUTPUT / "character" / kind
        root.mkdir(parents=True, exist_ok=True)

        max_pulls = 1000
        for miss in range(4):
            cdfs = {}
            for n in range(1, 8):
                d = up_distribution(CharacterState(pity=0, consecutive_loss=miss), n)
                padded = np.ones(max_pulls)
                length = min(len(d.cdf), max_pulls)
                padded[:length] = d.cdf[:length]
                cdfs[n] = padded

            if kind == "stack":
                func(cdfs, max_pulls, root / f"miss{miss}.png",
                     title=f"已连续歪 {miss} 次")
            else:
                func(cdfs, max_pulls, root / f"miss{miss}.png",
                     title=f"已连续歪 {miss} 次")

        # Stable
        stable_cdfs = {}
        for n in range(1, 16):  # extend to n=15 for staircase
            stable_pdf = _stable_pdf_func(n)
            stable_cdf = np.cumsum(stable_pdf)
            padded = np.ones(max_pulls)
            length = min(len(stable_cdf), max_pulls)
            padded[:length] = stable_cdf[:length]
            stable_cdfs[n] = padded
        if kind == "stack":
            func(stable_cdfs, max_pulls, root / "stable.png", title="稳态")
        else:
            func(stable_cdfs, max_pulls, root / "stable.png", title="稳态",
                 calc_n_limit=15)
        print(f"  Character {kind} done")


def plot_weapon() -> None:
    """Weapon banner plots."""
    root = OUTPUT / "weapon"
    root.mkdir(parents=True, exist_ok=True)

    pdfs = get_gold_pdfs(WEAPON_POOL)
    plot_base_pdfs(pdfs, root / "pdf.png")

    # CDF for 1-4 golds
    cdfs = [np.cumsum(p) for p in pdfs]
    for gold in range(1, 5):
        plot_annotated_cdf(
            cdfs[gold],
            f"出 {gold} 金所需抽数的累积分布函数",
            root / f"cdf-gold{gold}.png",
        )

    # Target: one copy of A
    state = WeaponState(pity=0)
    d1 = weapon_up_distribution(state, WeaponTarget(count_a=1))
    plot_annotated_cdf(d1.cdf, "武器池：出一个 Up 所需抽数的累积分布函数",
                       root / "target-one-up.png")

    print("  Weapon done")


def plot_multi_gold_viz() -> None:
    """Ten-pull multi-gold probability curves."""
    from genshin_wish._gold import get_gold_cdfs
    root = OUTPUT / "multi-gold"
    root.mkdir(parents=True, exist_ok=True)

    for name, pool in [("character", CHARACTER_POOL), ("weapon", WEAPON_POOL)]:
        pdfs_list = get_gold_pdfs(pool)
        p_gold = pdfs_list[1]
        base_p = pool.base_rate

        for gold in range(2, 7):
            # Simple multi-gold per 10-pull probability
            p = _pull10_prob(p_gold, gold)
            if p > 1e-7:
                label = "角色" if name == "character" else "武器"
                plot_multi_gold(
                    p,
                    f"稳态下{label}池十连 {gold} 金",
                    root / f"{name}-{gold}gold.png",
                )
    print("  Multi-gold done")


def _pull10_prob(pdf1, gold):
    """Estimate 10-pull multi-gold probability at steady state."""
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


def main() -> None:
    print("Generating all plots...")

    plot_character_cdf()
    plot_character_fan()
    plot_character_column()
    plot_character_stack()
    plot_weapon()
    plot_multi_gold_viz()

    print("\nAll plots generated in output/")


if __name__ == "__main__":
    main()
