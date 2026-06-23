#!/usr/bin/env python
"""Ten-pull multi-gold probability charts."""

from pathlib import Path

import numpy as np

from genshin_wish._constants import CHARACTER_POOL, WEAPON_POOL
from genshin_wish._gold import get_gold_pdfs
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.multi_gold import plot_multi_gold

setup_style()

OUTPUT = Path("output")


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


def main() -> None:
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


if __name__ == "__main__":
    main()
