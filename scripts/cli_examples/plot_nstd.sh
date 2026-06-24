#!/usr/bin/env bash
# n_std 分布单图绘制示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 柱状图 (满命) ==="
genshin-wish plot nstd-bar --n-up 7 --loss 0

echo "=== 柱状图 (大保底) ==="
genshin-wish plot nstd-bar --n-up 3 --guaranteed --loss 0

echo "=== 柱状图 (连歪 2) ==="
genshin-wish plot nstd-bar --n-up 7 --loss 2

echo "=== 条件抽数 CDF (歪 2 次) ==="
genshin-wish plot nstd-pdf --n-up 7 --n-std 2 --loss 0

echo "=== 条件抽数 CDF (大保底) ==="
genshin-wish plot nstd-pdf --n-up 3 --n-std 0 --guaranteed --loss 0

echo ""
echo "Done — output/cli/"
