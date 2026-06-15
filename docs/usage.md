# genshin-wish 使用指南

## 安装

```bash
conda activate ai   # 或你的 Python 环境
pip install -e .
```

依赖：Python >= 3.11, numpy, scipy, matplotlib, click

核心原理：从当前状态出发，枚举 UP/歪序列计算精确概率分布，n_up > 7 时自动切换 CLT 近似。角色池支持捕获明光机制，武器池支持定轨路径，联合计算将二者分布做卷积。

---

## CLI 命令

### `genshin-wish char` — 角色池

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--n-up` | INT | 必填 | 目标 UP 数（含角色本体，0 命 = 1） |
| `--guaranteed` / `--no-guaranteed` | flag | `--no-guaranteed` | 下一个金是否大保底 |
| `--pity` | INT | 0 | 已垫抽数，范围 0~89 |
| `--loss` | INT | 0 | 连续歪次数，范围 0~3，驱动捕获明光概率 |
| `--stable` / `--no-stable` | flag | `--no-stable` | 使用稳态分布（按稳态概率加权所有 `loss` 状态） |
| `--pulls` | INT | — | 查询给定抽数内的达成概率 |
| `--quantile` | FLOAT | — | 查询给定概率的分位点，如 `0.5` = 中位数 |
| `--quantiles` | STR | — | 多个分位点，逗号分隔，如 `"0.1,0.5,0.9"` |
| `--format` | `text`\|`json` | `text` | 输出格式 |

**示例：**

```bash
# 查期望和中位数
genshin-wish char --n-up 7 --quantile 0.5
# → 角色池:
#     期望抽数: 637.2
#     分位点 0.5: 639 抽

# 查特定状态下的达成概率
genshin-wish char --n-up 2 --guaranteed --pity 32 --loss 1 --pulls 200

# 稳态查询
genshin-wish char --stable --n-up 7 --pulls 800

# 多个分位点
genshin-wish char --n-up 7 --quantiles "0.1,0.5,0.9"

# JSON 输出
genshin-wish char --n-up 7 --pulls 800 --format json
```

### `genshin-wish weapon` — 武器池

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--count-a` | INT | 1 | 目标武器 A 的数量（定轨不取消） |
| `--pity` | INT | 0 | 已垫抽数，范围 0~79 |
| `--ep` | INT | 0 | 命定值，范围 0~2 |
| `--prev-std` / `--no-prev-std` | flag | `--no-prev-std` | 上一金是否为常驻（触发标准大保底） |
| `--pulls` | INT | — | 查询给定抽数内的达成概率 |
| `--quantile` | FLOAT | — | 查询给定概率的分位点 |
| `--format` | `text`\|`json` | `text` | 输出格式 |

**示例：**

```bash
# 从零开始抽 1 把定轨武器
genshin-wish weapon

# 已有命定值和垫抽
genshin-wish weapon --count-a 1 --ep 1 --pity 45 --pulls 100

# JSON 输出含 gold_weights
genshin-wish weapon --format json
```

### `genshin-wish joint` — 联合计算

角色池和武器池同时开抽的总消耗分布（两个池子独立，做卷积）。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--char-up` | INT | 必填 | 角色目标 UP 数 |
| `--weapon-count` | INT | 1 | 武器目标数量 |
| `--char-guaranteed` / `--no-char-guaranteed` | flag | `--no-char-guaranteed` | 角色池是否大保底 |
| `--char-pity` | INT | 0 | 角色池已垫抽数，0~89 |
| `--char-loss` | INT | 0 | 角色池连续歪次数，0~3 |
| `--weapon-pity` | INT | 0 | 武器池已垫抽数，0~79 |
| `--weapon-ep` | INT | 0 | 武器池命定值，0~2 |
| `--pulls` | INT | — | 查询给定抽数内的达成概率 |
| `--format` | `text`\|`json` | `text` | 输出格式 |

**示例：**

```bash
# 满命 + 1 把专武
genshin-wish joint --char-up 7 --weapon-count 1

# 带垫抽状态
genshin-wish joint --char-up 2 --weapon-count 1 \
  --char-guaranteed --char-pity 32 --char-loss 1 \
  --weapon-ep 1 --weapon-pity 45 \
  --pulls 500
```

---

## Python API

### 角色池

```python
from genshin_wish import CharacterState, up_distribution, stable_up_distribution

# 创建状态
state = CharacterState(
    guaranteed=False,    # 是否大保底
    pity=0,              # 已垫抽数，0~89
    consecutive_loss=0,  # 连续歪次数，0~3
)

# 计算精确分布（n_up <= 7 走 exact，> 7 自动切换 CLT）
dist = up_distribution(state, n_up=7)

# 查询
dist.expected           # float, 期望抽数
dist.quantile(0.5)      # int, 中位数抽数
dist.probability(800)   # float, 800 抽内达成概率
dist.luck(800)          # float, 等价于 probability，返回百分位
dist.pdf                # np.ndarray, 概率质量函数
dist.cdf                # np.ndarray, 累积分布函数
dist.method             # str, "exact" 或 "clt"
```

**稳态分布：** 按 `consecutive_loss` 的稳态概率 `[0.55, 0.27, 0.12, 0.05]` 加权平均各状态的分布，适用于不知道当前状态时的预估。

```python
dist_stable = stable_up_distribution(7)
```

**CLT 近似：** 当 n_up 较大时可直接调用，更快且精度足够。

```python
from genshin_wish.character import up_distribution_clt

dist_approx = up_distribution_clt(n_up=20)            # 稳态 CLT
dist_approx = up_distribution_clt(state, n_up=20)     # 指定状态 CLT
```

### 武器池

```python
from genshin_wish import WeaponState, WeaponTarget, weapon_up_distribution

state = WeaponState(
    pity=0,                # 已垫抽数，0~79
    epitomized_points=0,   # 命定值，0~2
    prev_standard=False,   # 上一金是否为常驻
)

# 只支持单把武器 (count_a >= 1, count_b 固定为 0)
target = WeaponTarget(count_a=1)

dist = weapon_up_distribution(state, target)

dist.expected        # 期望抽数
dist.quantile(0.5)   # 中位数
dist.probability(200)
dist.gold_weights    # dict, 各出金数分支的概率权重
```

### 联合计算

```python
from genshin_wish import CharacterState, WeaponState, WeaponTarget, joint_distribution

jd = joint_distribution(
    CharacterState(guaranteed=False, pity=0, consecutive_loss=0),
    char_n_up=2,
    WeaponState(pity=0, epitomized_points=0, prev_standard=False),
    WeaponTarget(count_a=1),
)

jd.expected          # float, 总期望抽数
jd.char.expected     # float, 角色部分期望
jd.weapon.expected   # float, 武器部分期望
jd.probability(500)  # float, 500 抽内达成概率
jd.quantile(0.5)     # int, 中位数
```

### 生成图表

```python
from genshin_wish.character import up_distribution, CharacterState
from genshin_wish.viz.cdf import plot_annotated_cdf

dist = up_distribution(CharacterState(), 7)
plot_annotated_cdf(dist.cdf, title="满命角色 CDF", filename="cdf.png")
```

`plot_annotated_cdf` 会自动标注 10%, 30%, 50%, 70%, 90%, 99% 分位线。还可用 `plot_up_cdf_lines` 绘制多条 CDF 对比图。

---

## 输出格式

默认 `text`，适合人读。`--format json` 输出机器可解析的 JSON。

```bash
genshin-wish char --n-up 7 --pulls 800 --format json
# {"expected": 637.2, "probability": 0.943, ...}
```

JSON 输出中的字段因命令而异：

- `char`: `expected`, `probability`, `quantile` / `quantiles`（如有指定）
- `weapon`: `expected`, `probability`, `gold_weights`
- `joint`: `expected`, `probability`, `char_expected`, `weapon_expected`
