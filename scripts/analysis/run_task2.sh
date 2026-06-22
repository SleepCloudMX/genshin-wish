#!/bin/bash
# Run task2 benchmark (n_up-n_std-to-pulls)
cd "$(dirname "$0")/../.."
python scripts/analysis/task2_n_up_n_std_to_pulls.py "$@"
