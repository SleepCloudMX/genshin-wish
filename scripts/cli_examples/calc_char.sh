#!/usr/bin/env bash
# 角色池概率查询示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 满命期望 + 800 抽达成概率 ==="
genshin-wish char --n-up 7 --pulls 800

echo ""
echo "=== 满命中位数 ==="
genshin-wish char --n-up 7 --quantile 0.5

echo ""
echo "=== 多个分位点 ==="
genshin-wish char --n-up 7 --quantiles "0.1,0.5,0.9"

echo ""
echo "=== 大保底 + 垫抽 ==="
genshin-wish char --n-up 2 --guaranteed --pity 32 --loss 1 --pulls 200

echo ""
echo "=== 稳态查询 ==="
genshin-wish char --stable --n-up 7 --pulls 800

echo ""
echo "=== JSON 输出 ==="
genshin-wish char --n-up 7 --pulls 800 --format json

echo ""
echo "=== 小概率自动显示四位小数 ==="
genshin-wish char --n-up 7 --pulls 200

echo ""
echo "=== 科学记数法 (--pct-fmt .2e) ==="
genshin-wish char --n-up 7 --pulls 200 --pct-fmt .2e

echo ""
echo "=== 极小概率 (auto 自动切换科学记数) ==="
genshin-wish char --n-up 7 --pulls 100

echo ""
echo "=== 指定方法 ==="
genshin-wish char --n-up 100 --method dp-golds --quantile 0.5

echo ""
echo "Done"
