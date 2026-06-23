#!/usr/bin/env python
"""Long-term luck fan charts: pre-5.0 vs post-5.0."""

from pathlib import Path

from genshin_wish.long_term import LongTermState, make_long_solver
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.long_term import plot_long_term_luck

setup_style()

OUTPUT = Path("output")


def main() -> None:
    base = OUTPUT / "character" / "long-term"
    scenarios = [
        ("N1=0,N2=500", LongTermState(n_pre_50=0, n_post_50=500), "捕获明光后"),
        ("N1=500,N2=0", LongTermState(n_pre_50=500, n_post_50=0), "纯 50/50"),
    ]
    for dirname, state, label in scenarios:
        out_dir = base / dirname
        out_dir.mkdir(parents=True, exist_ok=True)
        solver = make_long_solver(state)
        N = state.n_pre_50 + state.n_post_50

        plot_long_term_luck(
            solver, N=N,
            save_path=out_dir / "long-term.png",
            title=f"{label} 长期欧非演变 (N={N})",
        )

        for block_start in range(0, N, 100):
            block_n = min(100, N - block_start)
            block_end = block_start + block_n
            plot_long_term_luck(
                solver, N=block_n, n_start=block_start,
                save_path=out_dir / f"{block_end}.png",
                title=f"{label} 长期欧非演变 (N={block_start + 1}~{block_end})",
            )

        print(f"  Long-term {dirname} done")


if __name__ == "__main__":
    main()
