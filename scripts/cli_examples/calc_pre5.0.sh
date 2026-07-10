#!/usr/bin/env bash
# 5.0 前机制 (无捕获明光) 概率查询示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== Pre-5.0 单 UP 期望 (≈93.4) ==="
genshin-wish char --n-up 1 --pre-5.0

echo ""
echo "=== Post-5.0 单 UP 期望 (≈93.4, km=0 时相同) ==="
genshin-wish char --n-up 1

echo ""
echo "=== Pre-5.0 满命期望 (≈654) ==="
genshin-wish char --n-up 7 --pre-5.0

echo ""
echo "=== Post-5.0 满命期望 (≈637, CR 累积优势) ==="
genshin-wish char --n-up 7

echo ""
echo "=== Pre-5.0 分位点 ==="
genshin-wish char --n-up 7 --pre-5.0 --quantiles "0.1,0.5,0.9"

echo ""
echo "=== Pre-5.0 大保底 ==="
genshin-wish char --n-up 2 --pre-5.0 --guaranteed --pity 32

echo ""
echo "=== Pre-5.0 稳态 ==="
genshin-wish char --stable --pre-5.0 --n-up 7

echo ""
echo "=== Pre-5.0 n_std 分布 ==="
genshin-wish plot nstd-bar --n-up 7 --pre-5.0

echo ""
echo "=== Post-5.0 n_std 分布 (对比) ==="
genshin-wish plot nstd-bar --n-up 7

echo ""
echo "=== 互斥: --pre-5.0 --loss 1 应报错 ==="
genshin-wish char --n-up 1 --pre-5.0 --loss 1 2>&1 || true

echo ""
echo "Done"
