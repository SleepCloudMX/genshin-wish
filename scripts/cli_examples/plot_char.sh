#!/usr/bin/env bash
# 角色池单图绘制示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== CDF (满命, 连歪 0) ==="
genshin-wish plot char-cdf --n-up 7 --loss 0

echo "=== CDF (大保底 + 垫抽) ==="
genshin-wish plot char-cdf --n-up 2 --guaranteed --pity 32 --loss 1

echo "=== PDF (满命, 连歪 0) ==="
genshin-wish plot char-pdf --n-up 7 --loss 0

echo "=== PDF (大保底 + 垫抽) ==="
genshin-wish plot char-pdf --n-up 2 --guaranteed --pity 32 --loss 1

echo "=== 幸运扇形图 (3 层区间) ==="
genshin-wish plot char-fan --n-up 7 --loss 0 --interval 3

echo "=== 幸运扇形图 (5 层区间) ==="
genshin-wish plot char-fan --n-up 7 --loss 0 --interval 5

echo "=== 扇形图 + 个人抽卡记录 (n_up 自动推断) ==="
genshin-wish plot char-fan --interval 5 \
  --pulls-seq "68,79+11,77+80,77,76+74,80+66,74,78,78,32+79,31+75"

echo ""
echo "Done — output/cli/"
