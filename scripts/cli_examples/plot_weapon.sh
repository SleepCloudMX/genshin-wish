#!/usr/bin/env bash
# 武器池单图绘制示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== 定轨 CDF (1 把) ==="
genshin-wish plot weapon-cdf --count-a 1

echo "=== 定轨 CDF (垫抽 + 命定值) ==="
genshin-wish plot weapon-cdf --count-a 1 --ep 1 --pity 45

echo ""
echo "Done — output/cli/"
