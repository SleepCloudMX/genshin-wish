#!/usr/bin/env python
"""Generate all standard plots.

Usage:
    python scripts/main_plot.py                 # all plots
    python scripts/main_plot.py -c              # character only
    python scripts/main_plot.py -w              # weapon only
    python scripts/main_plot.py -m              # multi-gold only
    python scripts/main_plot.py -l              # long-term only
    python scripts/main_plot.py -n              # n_std only
    python scripts/main_plot.py -c -w           # combinations
"""

import argparse


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-c", "--character", action="store_true", help="Character banner charts")
    p.add_argument("-w", "--weapon", action="store_true", help="Weapon banner charts")
    p.add_argument("-m", "--multi-gold", action="store_true", help="Ten-pull multi-gold charts")
    p.add_argument("-l", "--long-term", action="store_true", help="Long-term luck fan charts")
    p.add_argument("-n", "--nstd", action="store_true", help="n_std distribution charts")
    args = p.parse_args()

    run_all = not (args.character or args.weapon or args.multi_gold or args.long_term or args.nstd)

    if run_all:
        print("Generating all plots...")
    else:
        labels = []
        if args.character: labels.append("character")
        if args.weapon: labels.append("weapon")
        if args.multi_gold: labels.append("multi-gold")
        if args.long_term: labels.append("long-term")
        if args.nstd: labels.append("nstd")
        print(f"Generating: {', '.join(labels)}")

    if run_all or args.character:
        from plots.character import main as c
        c()
    if run_all or args.weapon:
        from plots.weapon import main as w
        w()
    if run_all or args.multi_gold:
        from plots.multi_gold import main as m
        m()
    if run_all or args.long_term:
        from plots.long_term import main as l
        l()
    if run_all or args.nstd:
        from plots.nstd import main as n
        n()

    print("\nDone")


if __name__ == "__main__":
    main()
