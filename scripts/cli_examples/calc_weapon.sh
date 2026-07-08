#!/usr/bin/env bash
# 武器池概率查询示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 1 把定轨武器 ==="
genshin-wish weapon --count-a 1 --pulls 200

echo ""
echo "=== 定轨 + 垫抽 + 命定值 ==="
genshin-wish weapon --count-a 1 --ep 1 --pity 45 --pulls 100

echo ""
echo "=== 上一金是常驻 ==="
genshin-wish weapon --count-a 1 --prev-std --pulls 200

echo ""
echo "=== 指定百分比格式 (四位小数) ==="
genshin-wish weapon --count-a 2 --pulls 200 --pct-fmt .4f

echo ""
echo "Done"
