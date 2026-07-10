#!/usr/bin/env bash
# 玩家抽卡百分位对照图示例
# 使用前: conda activate ai (或你的环境)
set -euo pipefail

# --- 短序列 (≤20 UP) ---

echo "=== 短序列 默认 auto (全标注) ==="
genshin-wish plot player-luck \
  --pulls-seq "68,79+11,77+80,77,76+74,80+66,74,78,78,32+79,31+75"

echo "=== 短序列 稳态 ==="
genshin-wish plot player-luck \
  --pulls-seq "68,79+11,77+80,77,76+74,80+66,74,78,78,32+79,31+75" \
  --stable

echo "=== 短序列 大保底 + 垫 32 抽 ==="
genshin-wish plot player-luck \
  --pulls-seq "68,79+11,77+80,77,76+74,80+66,74,78,78,32+79,31+75" \
  --guaranteed --pity 32 --loss 1

# --- 中序列 (21–50 UP) ---

PULLS_MID="78,19,55+11,74,76,80,72,43+79,67,75,50+47,50,76+33,77,81,75+74,81,79+74,80,60,74,77,79+80"

echo "=== 中序列 默认 auto (全标注 + 自适应扩图) ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_MID"

echo "=== 中序列 仅关闭分位数标注 ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_MID" \
  --plot-config "q: off" \
  -o output/cli/player-luck-n23-loss0-pity0-no-q.png

echo "=== 中序列 仅关闭节点标注 ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_MID" \
  --plot-config "node: false" \
  -o output/cli/player-luck-n23-loss0-pity0-no-node.png

echo "=== 中序列 极简 (全关) ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_MID" \
  --plot-config "single-up: false; q: off; node: false" \
  -o output/cli/player-luck-n23-loss0-pity0-minimal.png

echo "=== 中序列 固定宽度 16 英寸 ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_MID" \
  --plot-config "width: fixed" \
  -o output/cli/player-luck-n23-loss0-pity0-fixed.png

# --- 长序列 (>50 UP) ---

PULLS_LONG="78,75,82+11,77,68,70+76,80,74,73,76+8,75,81,70,79,74+78,72,76,80,74,77+82,69,75,78,81,70+80,73,79,76,74,72+78,77,80,69,75,81+7,76,73,78,74,79+76,72,77,80,68,75,81+6,73,79,76,70,78,74+80,72,76,80"

echo "=== 长序列 默认 auto (极简: 无 single-up/node, q 稀疏标注, 40 英寸封顶) ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_LONG"

echo "=== 长序列 强制全标注 + 扩图 ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_LONG" \
  --plot-config "single-up: true; q: all; node: true; width: auto" \
  -o output/cli/player-luck-n55-loss0-pity0-full.png

echo "=== 长序列 关闭分位数标注 ==="
genshin-wish plot player-luck --pulls-seq "$PULLS_LONG" \
  --plot-config "width: fixed" \
  -o output/cli/player-luck-n55-loss0-pity0-fixed.png

echo ""
echo "Done — output/cli/"
