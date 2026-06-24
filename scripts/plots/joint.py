#!/usr/bin/env python
"""Joint distribution CDF charts (character + weapon).

Output: ``output/joint/``
"""

from pathlib import Path

import numpy as np

from genshin_wish.character import CharacterState
from genshin_wish.weapon import WeaponState, WeaponTarget
from genshin_wish.joint import joint_distribution
from genshin_wish._constants import STABLE_P
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.cdf import plot_annotated_cdf
from genshin_wish.viz.heatmap import plot_percentile_heatmap

setup_style()

OUTPUT = Path("output/joint")

# a+b = C_a + W_b → n_up = a+1, weapon_count = b
DEFAULTS: list[tuple[int, int]] = [(2, 1), (6, 1), (6, 5)]


def _make_weapon_state() -> WeaponState:
    return WeaponState(pity=0, epitomized_points=0, prev_standard=False)


def _make_target(b: int) -> WeaponTarget:
    return WeaponTarget(count_a=b, count_b=0)


def main(pairs: list[tuple[int, int]] | None = None) -> None:
    for a, b in (pairs or DEFAULTS):
        n_up = a + 1
        out_dir = OUTPUT / f"{a}+{b}"
        out_dir.mkdir(parents=True, exist_ok=True)

        cdf_map: dict[str, np.ndarray] = {}
        percentiles: dict[int, dict[float, int]] = {}
        for loss in range(4):
            state = CharacterState(guaranteed=False, pity=0,
                                   consecutive_loss=loss)
            dist = joint_distribution(state, n_up, _make_weapon_state(),
                                      _make_target(b))

            cdf_map[f"miss={loss}"] = dist.cdf

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

        # Steady-state CDF (weighted average over k_miss)
        max_len = max(len(c) for c in cdf_map.values())
        stable_cdf = np.zeros(max_len, dtype=np.float64)
        for loss, pi in enumerate(STABLE_P):
            cdf = cdf_map[f"miss={loss}"]
            padded = np.zeros(max_len, dtype=np.float64)
            padded[: len(cdf)] = cdf
            stable_cdf += padded * pi
        cdf_map["stable"] = stable_cdf

        plot_percentile_heatmap(
            cdf_map,
            f"{a}+{b} 所需抽数",
            out_dir / f"{a}+{b}-heatmap.png",
            note_text=(
                f"{' ' * 20}注：角色池（前 73 抽 0.6%，之后每抽递增 6%；连续歪 0/1/2/3 次捕获明光概率 0.018%/9.6%/18.3%/100%）；\n"
                f"{' ' * 20}武器池（前 62 抽 0.7%，之后每抽递增 7%；定轨路径）；结果为解析计算（非蒙特卡洛），无模型误差与截断误差，舍入误差可忽略。"
            ),
        )

        # Markdown table
        rows = []
        for loss in range(4):
            p = percentiles[loss]
            rows.append(
                f"| k_miss={loss} | {p[0.1]} | {p[0.3]} | {p[0.5]} | "
                f"{p[0.7]} | {p[0.9]} | {p[0.99]} |"
            )

        table = (
            f"### {a}+{b} (C{a} + W{b})\n\n"
            f"| k_miss | 10% | 30% | 50% | 70% | 90% | 99% |\n"
            f"|--------|-----|-----|-----|-----|-----|-----|\n"
            + "\n".join(rows) + "\n"
        )
        (out_dir / f"{a}+{b}-table.md").write_text(table, encoding="utf-8")

    print(f"Done — {OUTPUT}")


if __name__ == "__main__":
    import argparse

    def _parse_pair(s: str) -> tuple[int, int]:
        a, b = s.split("+")
        return int(a.strip()), int(b.strip())

    p = argparse.ArgumentParser()
    p.add_argument("pairs", nargs="*", type=_parse_pair,
                   help="a+b pairs (default: 2+1 6+1 6+5)")
    args = p.parse_args()
    main(args.pairs if args.pairs else None)
