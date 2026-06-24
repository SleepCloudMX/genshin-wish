#!/usr/bin/env bash
# 常驻池概率查询示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 5 个五星 ==="
genshin-wish std --n-gold 5 --pulls 371

echo ""
echo "=== 带垫抽 + 中位数 ==="
genshin-wish std --n-gold 30 --pity 10 --quantile 0.5

echo ""
echo "=== JSON 输出 ==="
genshin-wish std --n-gold 5 --format json

echo ""
echo "Done"
