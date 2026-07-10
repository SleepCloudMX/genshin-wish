#!/usr/bin/env bash
# 5.0 前机制 (无捕获明光) 绘图示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

PULLS="68,79+11,77+80,77,76+74,80+66,74,78,78,32+79,31+75"
PULLS_LONG="78,19,55+11,74,76,80,72,43+79,67,75,50+47,50,76+33,77,81,75+74,81,79+74,80,60,74,77,79+80"

# --- char-fan ---

echo "=== 扇形图 Pre-5.0 ==="
genshin-wish plot char-fan --n-up 7 --pre-5.0 --interval 5

echo "=== 扇形图 Post-5.0 (对比) ==="
genshin-wish plot char-fan --n-up 7 --interval 5

echo "=== 扇形图 Pre-5.0 叠加玩家记录 ==="
genshin-wish plot char-fan --interval 5 --pre-5.0 --pulls-seq "$PULLS"

# --- player-luck ---

echo "=== player-luck 全 Pre-5.0 ==="
genshin-wish plot player-luck --pulls-seq "$PULLS" --pre-5.0 \
  -o output/cli/player-luck-n11-pre50-all.png

echo "=== player-luck 两阶段 (前 5 次为 Pre-5.0) ==="
genshin-wish plot player-luck --pulls-seq "$PULLS" \
  --pre-5.0-seq "68,79+11,77+80,77" \
  -o output/cli/player-luck-n11-pre50up5.png

echo "=== player-luck 全 Post-5.0 (对比) ==="
genshin-wish plot player-luck --pulls-seq "$PULLS" \
  -o output/cli/player-luck-n11-loss0-pity0.png

echo "=== player-luck 长序列 两阶段 (前 10 次为 Pre-5.0) ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_LONG" \
  --pre-5.0-seq "78,19,55+11,74,76,80,72,43+79,67" \
  -o output/cli/player-luck-n23-pre50up10.png

echo ""
echo "Done — output/cli/"
