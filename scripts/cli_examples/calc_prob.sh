#!/usr/bin/env bash
# 概率查询示例 — 输出到终端
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 角色池: 满命期望 + 800 抽达成概率 ==="
genshin-wish char --n-up 7 --pulls 800

echo ""
echo "=== 角色池: 满命中位数 ==="
genshin-wish char --n-up 7 --quantile 0.5

echo ""
echo "=== 角色池: 多个分位点 ==="
genshin-wish char --n-up 7 --quantiles "0.1,0.5,0.9"

echo ""
echo "=== 角色池: 大保底 + 垫抽 ==="
genshin-wish char --n-up 2 --guaranteed --pity 32 --loss 1 --pulls 200

echo ""
echo "=== 角色池: 稳态查询 ==="
genshin-wish char --stable --n-up 7 --pulls 800

echo ""
echo "=== 角色池: JSON 输出 ==="
genshin-wish char --n-up 7 --pulls 800 --format json

echo ""
echo "=== 角色池: 指定方法 ==="
genshin-wish char --n-up 100 --method dp-golds --quantile 0.5

echo ""
echo "=== 武器池: 1 把定轨武器 ==="
genshin-wish weapon --count-a 1 --pulls 200

echo ""
echo "=== 武器池: 定轨 + 垫抽 + 命定值 ==="
genshin-wish weapon --count-a 1 --ep 1 --pity 45 --pulls 100

echo ""
echo "=== 武器池: 上一金是常驻 ==="
genshin-wish weapon --count-a 1 --prev-std --pulls 200

echo ""
echo "=== 常驻池: 5 个五星 ==="
genshin-wish std --n-gold 5 --pulls 371

echo ""
echo "=== 常驻池: 带垫抽 + 中位数 ==="
genshin-wish std --n-gold 30 --pity 10 --quantile 0.5

echo ""
echo "=== 常驻池: JSON 输出 ==="
genshin-wish std --n-gold 5 --format json

echo ""
echo "=== 联合计算: C1 + R1 ==="
genshin-wish joint --char-up 2 --weapon-count 1 --pulls 500

echo ""
echo "=== 联合计算: 带垫抽状态 ==="
genshin-wish joint \
  --char-up 2 --weapon-count 1 \
  --char-guaranteed --char-pity 32 --char-loss 1 \
  --weapon-ep 1 --weapon-pity 45 \
  --pulls 500

echo ""
echo "Done"
