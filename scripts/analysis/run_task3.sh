#!/bin/bash
# Run task3 benchmark (n_up-to-n_std)
cd "$(dirname "$0")/../.."
python scripts/analysis/task3_n_up_to_n_std.py "$@"
