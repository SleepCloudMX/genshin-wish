#!/usr/bin/env python
"""Generate n_std distribution and conditional pulls charts for character banner.

Output: ``output/character/std/``

Usage::

    python scripts/plot_nstd.py                    # default: k_miss=0, n_up=1..7
    python scripts/plot_nstd.py --k-miss 0,1,2,3   # all k_miss
    python scripts/plot_nstd.py --n-up 7 --type pulls-dist
"""

import argparse
from pathlib import Path

from genshin_wish.character import (
    CharacterState,
    n_std_distribution,
    n_std_conditional_pulls,
)
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.nstd import (
    plot_nstd_bar,
    plot_nstd_cdf,
    plot_nstd_heatmap,
    plot_nstd_heatmap_per_up,
    plot_nstd_pdf,
)

setup_style()

OUTPUT = Path("output/character/std")
STD_DIST = OUTPUT / "std-dist"
PULLS_DIST = OUTPUT / "pulls-dist"


def main():
    args = _parse_args()
    n_ups = args.n_up or list(range(1, 8))
    k_misses = args.k_miss or [0]
    chart_type = args.type

    # --- collect all data ---
    # {n_up: {k_miss: {n_std: prob}}}
    all_nstd: dict[int, dict[int, dict[int, float]]] = {}
    # {n_up: {k_miss: {n_std: UpDistribution}}}
    all_pulls: dict[int, dict[int, dict[int, object]]] = {}

    for k in k_misses:
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k)
        for n in n_ups:
            if chart_type in ("all", "std-dist"):
                dist = n_std_distribution(state, n)
                all_nstd.setdefault(n, {})[k] = dist
            if chart_type in ("all", "pulls-dist"):
                dists = n_std_conditional_pulls(state, n)
                all_pulls.setdefault(n, {})[k] = dists

    # --- generate charts ---
    if chart_type in ("all", "std-dist"):
        _gen_std_dist(all_nstd, n_ups, k_misses)
    if chart_type in ("all", "pulls-dist"):
        _gen_pulls_dist(all_pulls, n_ups, k_misses)

    print(f"Done — {OUTPUT}")


def _gen_std_dist(
    all_nstd: dict[int, dict[int, dict[int, float]]],
    n_ups: list[int],
    k_misses: list[int],
) -> None:
    """Generate std-dist/ charts."""
    # Global heatmaps (one per k_miss)
    for k in k_misses:
        nstd_by_up = {n: all_nstd[n][k] for n in n_ups}
        plot_nstd_heatmap(nstd_by_up, k, STD_DIST / "heatmap" / f"heatmap-k{k}.png")

    # Per-n_up charts
    for n in n_ups:
        nstd_by_k = {k: all_nstd[n][k] for k in k_misses}
        out_dir = STD_DIST / f"n_up={n}"
        # Per-n_up heatmap (k_miss × n_std)
        plot_nstd_heatmap_per_up(nstd_by_k, n, out_dir / "heatmap.png")
        # Bar charts
        for k in k_misses:
            plot_nstd_bar(nstd_by_k[k], n, k, out_dir / f"n{n}-k{k}.png")


def _gen_pulls_dist(
    all_pulls: dict[int, dict[int, dict[int, object]]],
    n_ups: list[int],
    k_misses: list[int],
) -> None:
    """Generate pulls-dist/ charts."""
    for n in n_ups:
        for k in k_misses:
            dists = all_pulls[n][k]

            # Multi-curve PDF
            plot_nstd_pdf(dists, n, k,
                          PULLS_DIST / "pdf" / f"n{n}" / f"k{k}.png")

            # Annotated CDF — only for n=3 and n=7
            if n not in (3, 7):
                continue
            ranked = sorted(dists.items(),
                            key=lambda kv: kv[1].pdf.sum(), reverse=True)
            for ns, dist in ranked[:2]:
                plot_nstd_cdf(dist, n, ns, k,
                              PULLS_DIST / "cdf" / f"n{n}" / f"s{ns}-k{k}.png")


def _parse_args():
    def _int_list(s):
        return [int(x.strip()) for x in s.split(",")]

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-up", type=_int_list, default=None,
                   help="n_up values, comma-separated (default: 1,2,3,4,5,6,7)")
    p.add_argument("--k-miss", type=_int_list, default=None,
                   help="k_miss values, comma-separated (default: 0)")
    p.add_argument("--type", choices=["all", "std-dist", "pulls-dist"],
                   default="all",
                   help="Chart types to generate (default: all)")
    return p.parse_args()


if __name__ == "__main__":
    main()
