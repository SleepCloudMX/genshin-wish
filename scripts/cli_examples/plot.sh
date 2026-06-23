#!/usr/bin/env bash
# 单图绘制示例 — 输出到 output/cli/
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 角色池 CDF (满命, 连歪 0) ==="
genshin-wish plot char-cdf --n-up 7 --loss 0

echo "=== 角色池 CDF (大保底 + 垫抽) ==="
genshin-wish plot char-cdf --n-up 2 --guaranteed --pity 32 --loss 1

echo "=== 角色池 PDF (满命, 连歪 0) ==="
genshin-wish plot char-pdf --n-up 7 --loss 0

echo "=== 角色池 PDF (大保底 + 垫抽) ==="
genshin-wish plot char-pdf --n-up 2 --guaranteed --pity 32 --loss 1

echo "=== 角色池幸运扇形图 (3 层区间) ==="
genshin-wish plot char-fan --n-up 7 --loss 0 --interval 3

echo "=== 角色池幸运扇形图 (5 层区间) ==="
genshin-wish plot char-fan --n-up 7 --loss 0 --interval 5

echo "=== n_std 分布柱状图 (满命) ==="
genshin-wish plot nstd-bar --n-up 7 --loss 0

echo "=== n_std 分布柱状图 (大保底) ==="
genshin-wish plot nstd-bar --n-up 3 --guaranteed --loss 0

echo "=== n_std 分布柱状图 (连歪 2) ==="
genshin-wish plot nstd-bar --n-up 7 --loss 2

echo "=== 条件抽数 CDF (歪 2 次) ==="
genshin-wish plot nstd-pdf --n-up 7 --n-std 2 --loss 0

echo "=== 条件抽数 CDF (大保底) ==="
genshin-wish plot nstd-pdf --n-up 3 --n-std 0 --guaranteed --loss 0

echo "=== 武器池 CDF (1 把定轨) ==="
genshin-wish plot weapon-cdf --count-a 1

echo "=== 武器池 CDF (定轨 + 垫抽 + 命定值) ==="
genshin-wish plot weapon-cdf --count-a 1 --ep 1 --pity 45

echo ""
echo "Done — output/cli/"
