#!/usr/bin/env python
"""Joint distribution CDF charts (character + weapon).

Output: ``output/joint/``
"""

from pathlib import Path

import numpy as np

from genshin_wish.character import CharacterState
from genshin_wish.weapon import WeaponState, WeaponTarget
from genshin_wish.joint import joint_distribution
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.cdf import plot_annotated_cdf

setup_style()

OUTPUT = Path("output/joint")

# a+b = C_a + R_b → n_up = a+1, weapon_count = b
DEFAULTS: list[tuple[int, int]] = [(2, 1), (6, 1), (6, 5)]


def main() -> None:
    for a, b in DEFAULTS:
        n_up = a + 1
        out_dir = OUTPUT / f"{a}+{b}"
        out_dir.mkdir(parents=True, exist_ok=True)

        percentiles: dict[int, dict[float, int]] = {}
        for loss in range(4):
            state = CharacterState(guaranteed=False, pity=0,
                                   consecutive_loss=loss)
            weapon_state = WeaponState(pity=0, epitomized_points=0,
                                       prev_standard=False)
            target = WeaponTarget(count_a=b, count_b=0)
            dist = joint_distribution(state, n_up, weapon_state, target)

            path = out_dir / f"{a}+{b},miss={loss}.png"
            title = (
                f"joint CDF ({a}+{b}, miss={loss})  "
                f"E={dist.expected:.0f}"
            )
            plot_annotated_cdf(dist.cdf, title, path)

            percentiles[loss] = {}
            for alpha in [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]:
                percentiles[loss][alpha] = int(
                    np.searchsorted(dist.cdf, alpha)
                )

        # Heatmap table
        rows = []
        for loss in range(4):
            p = percentiles[loss]
            rows.append(
                f"| k_miss={loss} | {p[0.1]} | {p[0.3]} | {p[0.5]} | "
                f"{p[0.7]} | {p[0.9]} | {p[0.99]} |"
            )

        table = (
            f"### {a}+{b} (C{a} + R{b})\n\n"
            f"| k_miss | 10% | 30% | 50% | 70% | 90% | 99% |\n"
            f"|--------|-----|-----|-----|-----|-----|-----|\n"
            + "\n".join(rows) + "\n"
        )
        (out_dir / f"{a}+{b}-table.md").write_text(table, encoding="utf-8")

    print(f"Done — {OUTPUT}")


if __name__ == "__main__":
    main()
