#!/bin/bash
# Run all three analysis benchmarks (task1 + task2 + task3)
# Usage: bash run_all.sh [--n-runs-fast 50] [--n-runs-slow 11]

cd "$(dirname "$0")/../.."

echo "=== Task 1: n_up-to-pulls ==="
python scripts/analysis/task1_n_up_to_pulls.py "$@"
echo

echo "=== Task 2: n_up-n_std-to-pulls ==="
python scripts/analysis/task2_n_up_n_std_to_pulls.py "$@"
echo

echo "=== Task 3: n_up-to-n_std ==="
python scripts/analysis/task3_n_up_to_n_std.py "$@"
echo

echo "All done."
