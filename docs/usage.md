<h1>genshin-wish 使用指南</h1>

[TOC]

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
| `--stable` / `--no-stable` | flag | `--no-stable` | 使用稳态分布。**与 `--loss`、`--guaranteed`、`--pity` 互斥**——指定 `--stable` 后这些参数被忽略 |
| `--method` | `auto`\|`dp-golds`\|`dp-path`\|`dp-state`\|`clt` | `auto` | 计算方法。`auto` 自动选择（≤500 dp-golds，>500 clt+warning）。`dp-path` 限 n_up ≤ 20 |
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

### `genshin-wish std` — 常驻池

纯出金，无 UP 机制。计算获得指定数量五星的总抽数分布。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--n-gold` | INT | 必填 | 目标五星数 |
| `--pity` | INT | 0 | 已垫抽数，范围 0~89 |
| `--pulls` | INT | — | 查询给定抽数内的达成概率 |
| `--quantile` | FLOAT | — | 查询给定概率的分位点 |
| `--format` | `text`\|`json` | `text` | 输出格式 |

n_gold ≤ 7 精确卷积，> 7 则首金精确处理 pity 后对剩余金数用 CLT 近似。

**示例：**

```bash
# 5 个五星，371 抽
genshin-wish std --n-gold 5 --pulls 371

# 30 个五星，带垫抽，查中位数
genshin-wish std --n-gold 30 --pity 10 --quantile 0.5
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

### `genshin-wish plot` — 单图绘制

输出到 `output/cli/`，文件名由参数自动生成。与 `scripts/main_plot.py`（批量、固定参数）互补。

所有子命令支持 `-o` / `--output` 自定义输出路径：

- 路径含 `.` → 当作文件路径直接使用
- 否则 → 当作目录，文件名自动生成放入该目录
- 不指定 → 默认 `output/cli/<name>.png`

#### `plot char-cdf` — 角色池标注 CDF

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--n-up` | INT | 必填 | 目标 UP 数 |
| `--guaranteed` / `--no-guaranteed` | flag | `--no-guaranteed` | 是否大保底 |
| `--pity` | INT | 0 | 已垫抽数 |
| `--loss` | INT | 0 | 连续歪次数 0~3 |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

#### `plot char-pdf` — 角色池 PDF

选项同 `char-cdf`。

#### `plot char-fan` — 角色池幸运扇形图

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--n-up` | INT | 7 | 最大 UP 数 |
| `--guaranteed` / `--no-guaranteed` | flag | `--no-guaranteed` | |
| `--pity` | INT | 0 | |
| `--loss` | INT | 0 | |
| `--stable` / `--no-stable` | flag | `--no-stable` | 稳态分布 (按 STABLE_P 加权) |
| `--interval` | `3`\|`5` | `3` | 区间层数 |
| `--pulls-seq` | TEXT | — | 个人抽卡序列, e.g. `"68,79+11,77+80,..."`（叠加绿色玩家曲线） |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

`A+B` 表示歪常驻 (A 抽) 后出限定 (B 抽)；单个数字表示直接赢得限定。

#### `plot player-luck` — 个人抽卡百分位对照图

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--pulls-seq` | TEXT | **必填** | 抽卡序列, e.g. `"68,79+11,77+80,..."` |
| `--n-up` | INT | 序列长度 | 最大 UP 数 |
| `--guaranteed` / `--no-guaranteed` | flag | `--no-guaranteed` | |
| `--pity` | INT | 0 | |
| `--loss` | INT | 0 | |
| `--stable` / `--no-stable` | flag | `--no-stable` | 稳态分布 |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 |

Y 轴 = 百分位 (0–100%)，X 轴 = 已获得限定数。10 条水平参考线 (1%/10%/…/99%) 标注各 UP 所需抽数。 |

#### `plot nstd-bar` — n_std 分布柱状图

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--n-up` | INT | 必填 | 目标 UP 数 |
| `--guaranteed` / `--no-guaranteed` | flag | `--no-guaranteed` | 是否大保底 |
| `--loss` | INT | 0 | 连续歪次数 0~3 |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

仅支持 `pity=0`。

#### `plot nstd-pdf` — 条件抽数 CDF

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--n-up` | INT | 必填 | 目标 UP 数 |
| `--n-std` | INT | 必填 | 常驻数量 |
| `--guaranteed` / `--no-guaranteed` | flag | `--no-guaranteed` | 是否大保底 |
| `--loss` | INT | 0 | 连续歪次数 0~3 |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

仅支持 `pity=0`。

#### `plot radiance-seq` — 捕获明光次数分布 (给定序列)

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--seq` | STR | 必填 | win/loss 序列，逗号分隔 (1=win, 2=loss) |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

#### `plot radiance-bar` — 捕获明光次数分布 (给定 n_up)

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--n-up` | INT | 必填 | 目标 UP 数 |
| `--guaranteed` / `--no-guaranteed` | flag | `--no-guaranteed` | 是否大保底 |
| `--loss` | INT | 0 | 连续歪次数 0~3 |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

仅支持 `pity=0`。

#### `plot weapon-cdf` — 武器池标注 CDF

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--count-a` | INT | 1 | 目标武器 A 数量 |
| `--ep` | INT | 0 | 命定值 0~2 |
| `--pity` | INT | 0 | 已垫抽数 |
| `--prev-std` / `--no-prev-std` | flag | `--no-prev-std` | 上一金是否为常驻 |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

#### `plot joint-cdf` — 联合计算 CDF

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--char-up` | INT | 必填 | 角色目标 UP 数 (含本体) |
| `--weapon-count` | INT | 1 | 武器目标数量 |
| `--char-guaranteed` / `--no-char-guaranteed` | flag | `--no-guaranteed` | 角色池是否大保底 |
| `--char-pity` | INT | 0 | 角色池已垫抽数 |
| `--char-loss` | INT | 0 | 角色池连续歪次数 0~3 |
| `--weapon-ep` | INT | 0 | 武器池命定值 0~2 |
| `--weapon-pity` | INT | 0 | 武器池已垫抽数 |
| `-o` / `--output` | PATH | `output/cli/` | 输出路径 (含 `.` = 文件, 否则 = 目录) |

**示例：**

```bash
# 角色池满命 CDF
genshin-wish plot char-cdf --n-up 7 --loss 0

# 带垫抽和大保底的角色 PDF
genshin-wish plot char-pdf --n-up 2 --guaranteed --pity 32 --loss 1

# 幸运扇形图（5 层区间）
genshin-wish plot char-fan --n-up 7 --interval 5

# 扇形图 + 稳态
genshin-wish plot char-fan --n-up 7 --interval 5 --stable

# 扇形图叠加个人抽卡记录
genshin-wish plot char-fan --n-up 7 --interval 5 \
  --pulls-seq "68,79+11,77+80,77,76+74,80+66,74,78,78,32+79"

# 个人抽卡百分位对照图
genshin-wish plot player-luck \
  --pulls-seq "68,79+11,77+80,77,76+74,80+66,74,78,78,32+79"

# n_std 分布
genshin-wish plot nstd-bar --n-up 7 --loss 2

# 条件抽数（歪 2 次时的抽数分布）
genshin-wish plot nstd-pdf --n-up 7 --n-std 2 --loss 0

# 武器池定轨
genshin-wish plot weapon-cdf --count-a 1 --ep 1 --pity 45

# 指定输出目录
genshin-wish plot char-cdf --n-up 7 -o output/my-charts/

# 指定完整文件路径
genshin-wish plot nstd-bar --n-up 7 -o output/special.png

# 捕获明光次数 (给定序列)
genshin-wish plot radiance-seq --seq "1,2,2,1,2,2,1,1,1,2"

# 捕获明光次数 (给定 n_up)
genshin-wish plot radiance-bar --n-up 100 --loss 0

# 联合计算 CDF (C2 + R1)
genshin-wish plot joint-cdf --char-up 3 --weapon-count 1 --char-loss 0
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

# 计算分布（默认 auto：≤500 dp-golds，>500 clt+warning）
dist = up_distribution(state, n_up=7)

# 指定方法
dist = up_distribution(state, n_up=100, method="dp-golds")  # 金数 DP + 加权 PDF
dist = up_distribution(state, n_up=600, method="clt")       # 强制 CLT 近似
# method: "auto"（默认）/ "dp-golds"（金数 DP）/ "dp-path"（枚举，限 ≤20）
#         / "dp-state"（迭代卷积）/ "clt"

# 查询
dist.expected           # float, 期望抽数
dist.quantile(0.5)      # int, 中位数抽数
dist.probability(800)   # float, 800 抽内达成概率
dist.luck(800)          # float, 等价于 probability，返回百分位
dist.pdf                # np.ndarray, 概率质量函数
dist.cdf                # np.ndarray, 累积分布函数
dist.method             # str, "exact" 或 "clt"
dist.method             # str, "exact" 或 "clt"
```

**稳态分布：** 按 `consecutive_loss` 的稳态概率 `[0.55, 0.27, 0.12, 0.05]` 加权平均各状态的分布，适用于不知道当前状态时的预估。透传 `method` 参数。

```python
dist_stable = stable_up_distribution(7)                # auto
dist_stable = stable_up_distribution(500, method="dp-golds")
```

**捕获明光次数分布：** 计算获得 *n_up* 个 UP 过程中触发捕获明光的次数分布。仅支持 `pity=0`。

```python
from genshin_wish import CharacterState, radiance_distribution

state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
dist = radiance_distribution(state, n_up=7)
# dist = {0: 0.35, 1: 0.42, 2: 0.18, 3: 0.05, ...}
```

**常驻角色数分布：** 获得 *n_up* 个 UP 过程中歪出常驻数量的概率分布。仅支持 `pity=0`。

```python
from genshin_wish import CharacterState, n_std_distribution

state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
dist = n_std_distribution(state, n_up=7)
# dist = {0: 0.15, 1: 0.30, 2: 0.30, 3: 0.17, ...}
```

**常驻数条件下抽数分布：** 给定常驻数量的情况下的抽数分布。仅支持 `pity=0`。

```python
from genshin_wish import CharacterState, n_std_conditional_pulls

state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
dists = n_std_conditional_pulls(state, n_up=7)
# dists = {0: UpDistribution(...), 1: UpDistribution(...), ...}
dist = dists[2]  # 歪 2 次的抽数分布
dist.expected    # 期望抽数
dist.quantile(0.5)
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

### 常驻池

```python
from genshin_wish import StandardState, standard_distribution

state = StandardState(pity=0)   # 已垫抽数，0~89

dist = standard_distribution(state, n_gold=5)

dist.expected        # 期望抽数
dist.quantile(0.5)   # 中位数
dist.probability(371)
dist.method          # "exact" (n_gold <= 7) 或 "clt"
```

n_gold ≤ 7 精确卷积，> 7 首金精确处理 pity + 剩余金数 CLT 近似。

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

### 长期 UP 分布

计算 pre/post-5.0 两阶段的长期 UP 分布，用于 `plot_long_term_luck` 生成欧非演变图。

```python
from genshin_wish.long_term import LongTermState, make_long_solver
from genshin_wish.viz.long_term import plot_long_term_luck

# 捕获明光后 500 UP（默认 exact）
state = LongTermState(n_pre_50=0, n_post_50=500)
solver = make_long_solver(state)

# 直接查询分位点
data = solver(N=100, alphas=[0.5])
# data[0.5] = [(lo_n1, hi_n1), ..., (lo_n100, hi_n100)]

# 绘制图表
plot_long_term_luck(solver, N=500, save_path="output/long-term-500.png")

# 分段放大：仅显示第 101~200 个 UP
plot_long_term_luck(solver, N=100, n_start=100, save_path="output/long-term-200.png")

# 纯 50/50（pre-5.0）对比
pre_state = LongTermState(n_pre_50=500, n_post_50=0)
pre_solver = make_long_solver(pre_state)
plot_long_term_luck(pre_solver, N=500, save_path="output/long-term-pre.png")

# CLT 快速预览
solver_fast = make_long_solver(state, method="clt")
```

`solver(N, alphas)` 返回 `{alpha: [(lo, hi), ...]}`，长度为 N，每个 tuple 是该 alpha 分位点下的累计抽数上下界。默认用迭代卷积 exact，精度最高（N=500 约 1.2s）；CLT 约 20ms 但极欧分位（1%）在 N<30 时有偏差。

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
- `std`: `expected`, `probability`, `method`
- `joint`: `expected`, `probability`, `char_expected`, `weapon_expected`
