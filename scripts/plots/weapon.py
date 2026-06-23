#!/usr/bin/env python
"""Weapon banner plots: PDF, CDF, target."""

from pathlib import Path

import numpy as np

from genshin_wish._constants import WEAPON_POOL
from genshin_wish._gold import get_gold_pdfs
from genshin_wish.weapon import WeaponState, WeaponTarget, weapon_up_distribution
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.cdf import plot_annotated_cdf
from genshin_wish.viz.pdf import plot_base_pdfs

setup_style()

OUTPUT = Path("output")


def main() -> None:
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


if __name__ == "__main__":
    main()
