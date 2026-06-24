#!/usr/bin/env bash
# 联合计算概率查询示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

echo "=== C1 + R1 ==="
genshin-wish joint --char-up 2 --weapon-count 1 --pulls 500

echo ""
echo "=== 带垫抽状态 ==="
genshin-wish joint \
  --char-up 2 --weapon-count 1 \
  --char-guaranteed --char-pity 32 --char-loss 1 \
  --weapon-ep 1 --weapon-pity 45 \
  --pulls 500

echo ""
echo "Done"
