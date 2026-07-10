#!/usr/bin/env bash
# 5.0 前机制 (无捕获明光) 绘图示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

PRE="68,79+11,77+80,77,76+74"
POST="80+66,74,78,78,32+79,31+75"
ALL="$PRE,$POST"
PRE_LONG="78,19,55+11,74,76,80,72,43+79,67"
POST_LONG="75,50+47,50,76+33,77,81,75+74,81,79+74,80,60,74,77,79+80"
ALL_LONG="$PRE_LONG,$POST_LONG"

# --- char-fan ---

echo "=== 扇形图 Pre-5.0 ==="
genshin-wish plot char-fan --n-up 7 --pre-5.0 --interval 5

echo "=== 扇形图 Post-5.0 (对比) ==="
genshin-wish plot char-fan --n-up 7 --interval 5

echo "=== 扇形图 Pre-5.0 叠加玩家记录 ==="
genshin-wish plot char-fan --interval 5 --pre-5.0 --pulls-seq "$ALL"

# --- player-luck ---

echo "=== player-luck 全 Pre-5.0 ==="
genshin-wish plot player-luck --pre-5.0-seq "$ALL" \
  -o output/cli/player-luck-n11-pre50-all.png

echo "=== player-luck 两阶段 ==="
genshin-wish plot player-luck --pre-5.0-seq "$PRE" --pulls-seq "$POST" \
  -o output/cli/player-luck-n11-twophase.png

echo "=== player-luck 全 Post-5.0 (对比) ==="
genshin-wish plot player-luck --pulls-seq "$ALL" \
  -o output/cli/player-luck-n11-loss0-pity0.png

echo "=== player-luck 长序列 两阶段 ==="
genshin-wish plot player-luck --pre-5.0-seq "$PRE_LONG" --pulls-seq "$POST_LONG" \
  -o output/cli/player-luck-n23-twophase.png

echo ""
echo "Done — output/cli/"
