#!/usr/bin/env python
"""Batch radiance distribution charts for character banner.

Output: ``output/character/radiance/``
"""

from pathlib import Path

from genshin_wish.character import CharacterState, radiance_distribution
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.nstd import plot_nstd_heatmap_per_up
from genshin_wish.viz.radiance import plot_radiance_bar

setup_style()

OUTPUT = Path("output/character/radiance")


def main(
    n_up: list[int] | None = None,
    k_miss: list[int] | None = None,
) -> None:
    n_ups = n_up or list(range(1, 8))
    k_misses = k_miss or [0, 1, 2, 3]

    all_dist: dict[int, dict[int, dict[int, float]]] = {}

    for k in k_misses:
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k)
        for n in n_ups:
            dist = radiance_distribution(state, n)
            all_dist.setdefault(n, {})[k] = dist

    for n in n_ups:
        nstd_by_k = {k: all_dist[n][k] for k in k_misses}
        out_dir = OUTPUT / f"n_up={n}"
        plot_nstd_heatmap_per_up(nstd_by_k, n, out_dir / "heatmap.png")
        for k in k_misses:
            plot_radiance_bar(all_dist[n][k], n, k,
                              out_dir / f"n{n}-k{k}.png")

    print(f"Done — {OUTPUT}")


if __name__ == "__main__":
    import argparse

    def _int_list(s):
        return [int(x.strip()) for x in s.split(",")]

    p = argparse.ArgumentParser()
    p.add_argument("--n-up", type=_int_list, default=None)
    p.add_argument("--k-miss", type=_int_list, default=None)
    args = p.parse_args()
    main(args.n_up, args.k_miss)
