# genshin-wish

原神抽卡概率计算器 — 基于玩家总结的概率机制，**解析计算**角色池、武器池、常驻池的抽数概率分布。

## 安装

```bash
pip install -e .
```

依赖：Python ≥ 3.11，numpy，scipy，matplotlib，click。

## 快速开始

### CLI

#### （1）角色池

```bash
# 满命 (n_up=7)：期望抽数与 800 抽达成概率
genshin-wish char --n-up 7 --pulls 800

# 2 限定，已垫 32 抽，连歪 0 次：期望抽数与 200 抽达成概率
genshin-wish char --n-up 2 --guaranteed --pity 32 --loss 0 --pulls 200

# 满命：中位数
genshin-wish char --n-up 7 --quantile 0.5

# 稳态 (不指定具体 loss 状态时的平均情况)
genshin-wish char --stable --n-up 7 --pulls 800
```

#### （2）武器池

```bash
# 1 把定轨武器：期望抽数与 200 抽达成概率
genshin-wish weapon --count-a 1 --pulls 200

# 已垫 45 抽、命定值 1：期望抽数与 100 抽达成概率
genshin-wish weapon --count-a 1 --ep 1 --pity 45 --pulls 100
```

#### （3）常驻池

```bash
# 5 个五星：期望抽数与 371 抽达成概率
genshin-wish std --n-gold 5 --pulls 371
```

#### （4）联合计算

```bash
# C1 + R1：期望抽数与 500 抽达成概率
genshin-wish joint --char-up 2 --weapon-count 1 --pulls 500
```

> 完整 CLI 选项、参数互斥规则、JSON 输出格式见 **[使用指南](docs/usage.md)**。

### Python API

```python
from genshin_wish import CharacterState, up_distribution

dist = up_distribution(CharacterState(), n_up=7)
print(f"期望: {dist.expected:.0f} 抽")
print(f"中位数: {dist.quantile(0.5)} 抽")
print(f"800 抽达成概率: {dist.probability(800) * 100:.1f}%")
```

> 武器池、常驻池、联合计算的 Python API 见 **[使用指南](docs/usage.md)**。

## 生成图表

```bash
python scripts/plot_all.py
```

图表输出到 `output/`。`scripts/` 下还有其他分析工具，详见 [分析与验证](docs/analysis.md)。

## 文档

- [使用指南](docs/usage.md) — CLI 完整选项 / Python API 所有方法
- [概率机制说明](docs/mechanism.md) — 模型假设与验证
- [图表说明](docs/plots.md) — 图表类型与自定义绘图
- [分析与验证](docs/analysis.md) — CLT 误差、Solver 对比
- [架构与设计决策](docs/architecture.md) — 模块分层与设计理由

## 许可

MIT
