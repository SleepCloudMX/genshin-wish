#!/bin/bash
# Run task1 benchmark (n_up-to-pulls)
# Usage: bash run_task1.sh [--n-runs-fast 50] [--n-runs-slow 11] [--trim 0.2] [--error-bar minmax]

cd "$(dirname "$0")/../.."
python scripts/analysis/task1_n_up_to_pulls.py "$@"
