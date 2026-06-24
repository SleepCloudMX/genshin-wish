#!/usr/bin/env bash
# 联合计算单图绘制示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== C2 + W1 (连歪 0) ==="
genshin-wish plot joint-cdf --char-up 3 --weapon-count 1 --char-loss 0

echo "=== C6 + W1 (连歪 0) ==="
genshin-wish plot joint-cdf --char-up 7 --weapon-count 1 --char-loss 0

echo "=== C6 + W5 (连歪 0) ==="
genshin-wish plot joint-cdf --char-up 7 --weapon-count 5 --char-loss 0

echo ""
echo "Done — output/cli/"
