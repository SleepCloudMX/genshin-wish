# genshin-wish

原神抽卡概率计算器 — 基于玩家总结的概率机制，**解析计算**角色池、武器池、常驻池的抽数概率分布。

## 安装

```bash
pip install -e .
```

依赖：Python ≥ 3.11，numpy，scipy，matplotlib，click。

## 快速开始

### CLI

#### （1）角色池 `genshin-wish char`

查询获得指定数量 UP 角色的抽数分布。支持大小保底、捕获明光机制。

| 选项 | 说明 |
|------|------|
| `--n-up N` | 目标 UP 数（含本体，0 命 = 1） |
| `--guaranteed` | 下一个金是否大保底 |
| `--pity N` | 已垫抽数 (0~89) |
| `--loss N` | 连续歪次数 (0~3)，驱动捕获明光 |
| `--stable` | 使用稳态分布 |
| `--pulls N` | 查询 N 抽内的达成概率 |
| `--quantile Q` | 查询分位点对应抽数 |
| `--format json` | JSON 输出 |

```bash
# 满命 (--n-up 7)：期望抽数与 800 抽达成概率
genshin-wish char --n-up 7 --pulls 800

# 2 限定，已垫 32 抽，连歪 0 次：期望抽数与 200 抽达成概率
genshin-wish char --n-up 2 --guaranteed --pity 32 --loss 0 --pulls 200

# 满命中位数
genshin-wish char --n-up 7 --quantile 0.5
```

#### （2）武器池 `genshin-wish weapon`

定轨不取消，抽到指定数量目标武器。

| 选项 | 说明 |
|------|------|
| `--count-a N` | 目标数量（默认 1） |
| `--pity N` | 已垫抽数 (0~79) |
| `--ep N` | 命定值 (0~2) |
| `--prev-std` | 上一金是否为常驻 |
| `--pulls N` / `--quantile Q` | 同上 |

```bash
# 1 把定轨武器：期望与 200 抽概率
genshin-wish weapon --count-a 1 --pulls 200

# 已垫 45 抽、命定值 1：100 抽概率
genshin-wish weapon --count-a 1 --ep 1 --pity 45 --pulls 100
```

#### （3）常驻池 `genshin-wish std`

纯出金，无 UP 机制。n_gold ≤ 7 精确卷积，> 7 用 CLT 近似。

| 选项 | 说明 |
|------|------|
| `--n-gold N` | 目标五星数 |
| `--pity N` | 已垫抽数 (0~89) |
| `--pulls N` / `--quantile Q` | 同上 |

```bash
# 5 个五星，371 抽概率
genshin-wish std --n-gold 5 --pulls 371
```

#### （4）联合计算 `genshin-wish joint`

同时抽角色和武器，总抽数分布 = 二者独立卷积。

| 选项 | 说明 |
|------|------|
| `--char-up N` | 角色目标 UP 数 |
| `--weapon-count N` | 武器目标数量 |
| `--char-pity N` / `--char-loss N` / `--char-guaranteed` | 角色状态 |
| `--weapon-pity N` / `--weapon-ep N` | 武器状态 |
| `--pulls N` | 查询总抽数内达成概率 |

```bash
# C1 + R1：期望与 500 抽概率
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
