# genshin-wish

原神抽卡概率计算器 — 基于玩家总结的概率机制，**解析计算**角色池、武器池、常驻池的抽数概率分布。

> 图表展示：[genshin-wish-images](https://github.com/SleepCloudMX/genshin-wish-images)

## 安装

```bash
pip install -e .
```

依赖：Python ≥ 3.11，numpy，scipy，matplotlib，click。

## 快速开始

### CLI 计算

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

### CLI 单图绘制

图表默认输出到 `output/cli/`，可使用 `-o` 指定输出路径。

#### （1）角色池 (`plot char-*`)

```bash
# CDF 曲线
genshin-wish plot char-cdf --n-up 7 --loss 0

# PDF 曲线
genshin-wish plot char-pdf --n-up 7 --loss 0

# 幸运扇形图
genshin-wish plot char-fan --n-up 7 --interval 5
```

#### （2）常驻数分布 (`plot nstd-*`)

```bash
# 柱状图
genshin-wish plot nstd-bar --n-up 7 --loss 0

# 条件抽数 CDF
genshin-wish plot nstd-pdf --n-up 7 --n-std 2 --loss 0
```

#### （3）捕获明光次数分布 (`plot radiance-*`)

```bash
# 给定 win/loss 序列
genshin-wish plot radiance-seq --seq "1,2,2,1,2,2,1,1,1,2"

# 给定 n_up
genshin-wish plot radiance-bar --n-up 100 --loss 0
```

#### （4）联合 (`plot joint-*`)

```bash
# 角色 + 武器联合 CDF
genshin-wish plot joint-cdf --char-up 3 --weapon-count 1
```

#### （5）武器池 (`plot weapon-*`)

```bash
# 定轨 CDF
genshin-wish plot weapon-cdf --count-a 1 --ep 1 --pity 45
```

> 完整 CLI 选项、参数互斥规则、输出格式见 **[使用指南](docs/usage.md)**。

### Python API

```python
from genshin_wish import CharacterState, up_distribution

dist = up_distribution(CharacterState(), n_up=7)
print(f"期望: {dist.expected:.0f} 抽")
print(f"中位数: {dist.quantile(0.5)} 抽")
print(f"800 抽达成概率: {dist.probability(800) * 100:.1f}%")
```

> 武器池、常驻池、联合计算的 Python API 见 **[使用指南](docs/usage.md)**。

## 批量生成图表

```bash
python scripts/main_plot.py          # 全部图表
python scripts/main_plot.py -c       # 仅角色池
python scripts/main_plot.py -n       # 仅 n_std 分布
```

图表输出到 `output/`，同时作为独立仓库托管于 [genshin-wish-images](https://github.com/SleepCloudMX/genshin-wish-images)。分析脚本见 `scripts/main_analysis.py`。更自由的单图绘制见 [CLI 单图绘制](#cli-单图绘制)。

## 文档

- [使用指南](docs/usage.md) — CLI 完整选项 / Python API 所有方法
- [概率机制说明](docs/mechanism.md) — 模型假设与验证
- [图表说明](docs/plots.md) — 图表类型与自定义绘图
- [分析与验证](docs/analysis.md) — CLT 误差、Solver 对比
- [架构与设计决策](docs/architecture.md) — 模块分层与设计理由

## 许可

MIT
