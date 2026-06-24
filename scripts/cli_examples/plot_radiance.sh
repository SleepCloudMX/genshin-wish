#!/usr/bin/env bash
# 捕获明光分布单图绘制示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 给定序列 ==="
genshin-wish plot radiance-seq --seq "1,2,2,1,2,2,1,1,1,2"

echo "=== 给定 n_up ==="
genshin-wish plot radiance-bar --n-up 100 --loss 0

echo ""
echo "Done — output/cli/"
