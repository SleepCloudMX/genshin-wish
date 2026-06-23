#!/usr/bin/env python
"""Run task analysis benchmarks.

Usage:
    python scripts/main_analysis.py --plot-only              # all tasks, plot-only
    python scripts/main_analysis.py --plot-only --tasks 1    # task1 only
    python scripts/main_analysis.py --plot-only --tasks 1 --fit
    python scripts/main_analysis.py --plot-only --tasks 2,3
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPTS_DIR / "analysis"

TASKS = {
    "1": ANALYSIS_DIR / "task1_n_up_to_pulls.py",
    "2": ANALYSIS_DIR / "task2_n_up_n_std_to_pulls.py",
    "3": ANALYSIS_DIR / "task3_n_up_to_n_std.py",
}


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tasks", default="1,2,3",
                   help="Comma-separated task ids (default: 1,2,3)")
    p.add_argument("--plot-only", action="store_true",
                   help="Skip computation, regenerate plots from data.json")
    p.add_argument("--error-bar", choices=["minmax", "std3", "none"],
                   default="minmax", help="Error bar style (default: minmax)")
    p.add_argument("--trim", type=float, default=0.2,
                   help="Trim fraction for trimmed mean (default: 0.2)")
    p.add_argument("--fit", action="store_true",
                   help="Fit & annotate slope lines on speed.png (task1 only)")
    args = p.parse_args()

    task_ids = [t.strip() for t in args.tasks.split(",")]
    for tid in task_ids:
        if tid not in TASKS:
            print(f"Unknown task: {tid} (valid: {sorted(TASKS.keys())})")
            sys.exit(1)

    for tid in task_ids:
        script = TASKS[tid]
        cmd = [sys.executable, str(script)]
        if args.plot_only:
            cmd.append("--plot-only")
        cmd.extend(["--error-bar", args.error_bar])
        cmd.extend(["--trim", str(args.trim)])
        if tid == "1" and args.fit:
            cmd.append("--fit")

        print(f"\n=== Task {tid}: {script.name} ===", flush=True)
        subprocess.run(cmd, cwd=SCRIPTS_DIR.parent, check=True)

    print("\nAll tasks done.")


if __name__ == "__main__":
    main()
