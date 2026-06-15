# genshin-wish

原神抽卡概率计算器 — 精确计算角色池、武器池的抽数概率分布。

## 安装

```bash
pip install -e .
```

依赖：Python ≥ 3.11，numpy，scipy，matplotlib，click。

## 快速开始

### CLI

```bash
# 查询满命期望抽数
genshin-wish char --n-up 7 --pulls 800

# 查询分位点
genshin-wish char --n-up 7 --quantile 0.5

# 带抽卡状态
genshin-wish char --n-up 2 --guaranteed --pity 32 --loss 0 --pulls 200

# 武器池
genshin-wish weapon --count-a 1 --pulls 200

# 常驻池
genshin-wish std --n-gold 5 --pulls 371

# 联合计算
genshin-wish joint --char-up 2 --weapon-count 1 --pulls 500
```

### Python API

```python
from genshin_wish import CharacterState, up_distribution

# 0 垫抽、小保底、未连歪，抽满命
dist = up_distribution(CharacterState(), n_up=7)
print(f"期望: {dist.expected:.0f} 抽")
print(f"中位数: {dist.quantile(0.5)} 抽")
print(f"800 抽达成概率: {dist.probability(800) * 100:.1f}%")
```

## 生成图表

```bash
python scripts/plot_all.py
```

图表输出到 `output/`。

## 文档

- [概率机制说明](docs/mechanism.md)
- [使用指南](docs/usage.md)
- [图表说明](docs/plots.md)
- [架构与设计决策](docs/architecture.md)

## 许可

MIT
