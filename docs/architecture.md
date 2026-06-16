<h1>genshin-wish 架构与设计决策</h1>

[TOC]

> 版本：与 `src/` 代码同步更新。

## 模块分层

```
CLI (cli/main.py)
 ↓
Joint (joint.py)          Standard (standard.py)
 ↓                         ↓
Character (character.py)  Weapon (weapon.py)       LongTerm (long_term.py)
 ↓                         ↓                         ↓
Capture Radiance           金数权重 (_single_copy_weights)     Gold PDF/CDF
(_capture_radiance.py)     (weapon_target_weights)            (_gold.py)
 ↓                         ↓                                   ↑
Gold PDF/CDF (_gold.py)  ←  PoolConfig (_constants.py)  ──────┘
```

各模块职责：

| 模块 | 职责 | 上层依赖 |
|------|------|----------|
| `_constants.py` | `PoolConfig` 参数化池配置、稳态概率 `STABLE_P`、捕获明光胜率、CLT 阈值 | 无 |
| `_gold.py` | 出金基础概率 PDF/CDF 构建与缓存，与池类型无关的纯数学 | `_constants.py` |
| `_capture_radiance.py` | 捕获明光的状态转移枚举（win/loss 序列空间） | `_constants.py` |
| `character.py` | 角色池 UP 分布：三部分分解 + CLT 近似 | `_constants.py`, `_capture_radiance.py`, `_gold.py` |
| `weapon.py` | 武器池定轨分布：金数权重枚举 + 加权 PDF 合成 | `_constants.py`, `_gold.py` |
| `standard.py` | 常驻池纯出金分布：精确卷积 + CLT 近似 | `_constants.py`, `_gold.py` |
| `joint.py` | 独立卷积角色和武器分布，得到联合分布 | `character.py`, `weapon.py` |
| `long_term.py` | 长期 UP 分布（pre/post-5.0 混合），exact 迭代卷积 + CLT 近似，供 `viz/long_term.py` 调用 | `_constants.py`, `_gold.py` |
| `viz/` | 纯绘图，不包含计算逻辑 | `character.py`, `weapon.py`, `long_term.py` |
| `cli/main.py` | click 命令行封装，暴露 `char` / `weapon` / `joint` 三个子命令 | `character.py`, `weapon.py`, `joint.py`, `click` |

---

## 核心设计决策

### 1. PoolConfig 参数化

用一个 frozen dataclass 描述池的所有概率参数，避免角色/武器代码中硬编码数值的重复。

```python
@dataclass(frozen=True)
class PoolConfig:
    base_rate: float          # 基础出金概率
    soft_pity_start: int      # 软保底起始抽数 (1-indexed)
    hard_pity: int            # 硬保底抽数
    soft_pity_step: float     # 软保底每抽概率增量
    soft_pity_start2: int | None = None   # 武器池第二段软保底起始
    soft_pity_step2: float | None = None  # 武器池第二段增量
    max_gold_cache: int = 13  # 预计算金数上限
```

设计意图：

- `_gold.py` 的 `build_gold_pdf()` 根据 `PoolConfig` 自动构建正确长度的概率数组。武器池的两段软保底通过 `soft_pity_start2` / `soft_pity_step2` 描述，代码通过 `is None` 判断单段/两段逻辑。
- `max_gold_cache` 决定预计算的金数上限：角色池 13（13 金覆盖满命最坏情况），武器池 10（10 金覆盖 5 精定轨最坏情况）。
- frozen dataclass 保证配置不可变，避免运行时意外修改。

### 2. 三部分分解（character.py）

`up_distribution` 的核心思路：将"n_up 个 UP 所需抽数"分解为三个独立部分，然后卷积合成。

分解如下：

1. **第一个金**（从当前 pity 开始）  
   将 `pdfs[1]` 按当前 pity 截断并重归一化。这是唯一受当前状态影响的金。

2. **不确定的 UP**（n_uncertain = n_up - guaranteed）  
   通过 `guarantee_seq` 枚举所有 win/loss 序列，每个序列对应特定的金数。用金数概率加权对应的多金 PDF（`pdfs[k]`），得到不确定部分的综合分布。

3. **大保底的金**（若 `guaranteed=True`）  
   额外一个 `pdfs[1]`，无条件。

三部分独立（金与金之间 pity 重置，出金是更新过程），通过卷积合成：

```
总分布 = 不确定部分 ⊗ 第一个金（shifted）  [⊗ 大保底金]
```

由于卷积满足交换律，curr_pity 的 shift 可以施加到任意一项，实际代码将其施加到"第一个金"上。

**边界情况**：n_up=0 返回 `[1.0]`（0 抽必然达成）；n_uncertain=0（即 guaranteed=True 且 n_up=1）时无不确定部分，直接返回单金 PDF 的截断重归一。

### 3. CLT 阈值

`n_up ≤ 7` 使用精确解（`guarantee_seq` 枚举最多 2^7=128 条序列，完全可行）。

`n_up > 7` 默认使用中心极限定理近似（2^8=256 条序列起枚举代价快速增长）。

正态近似基于单次 UP 的前两阶矩：

- 中部分位（10%~90%）误差 < 1%
- 尾部误差约 ±8 抽
- 对于 n_up=7，精确解和 CLT 在常用分位点的相对误差 < 2%

`UpDistribution.method` 字段标记使用的方法（`"exact"` 或 `"clt"`）。

### 4. PDF 不截断

精确计算中，PDF 天然有界：硬保底保证 k 金所需抽数 ≤ k × hard_pity。不存在需要截断的无穷尾巴。

可视化中的 `max_pulls` 参数是展示截断（非计算截断），应自适应计算为 E + 6σ，覆盖约 99.9999% 的概率质量。

### 5. 武器池策略

当前仅支持「定轨不取消」（strategy1），即定轨目标 A 后不改变目标直到抽到 A，对应 `WeaponTarget(count_a=k, count_b=0)`。

金数权重通过 `_single_copy_weights` 枚举每把 A 所需金数的离散分布，再对 count_a 次重复进行卷积（每获得一把后状态重置为 `ep=0, prev_standard=False`）。

三种状态组合：

| epitomized_points | prev_standard | 金数分布 |
|---|---|---|
| ≥ 1 | 任意 | {1: 1.0} — 命定值触发，下一金必为目标 |
| 0 | True | {1: 0.5, 2: 0.5} — 大保底，池中仅两把限定 |
| 0 | False | {1: 0.375, 2: 0.625} — 默认状态，可能出常驻 |

同时要两把不同限定武器的策略（需取消重定轨），列入后续扩展（`count_b > 0` 时抛出 `NotImplementedError`）。

### 6. 蒙特卡洛的定位

解析解优先。蒙特卡洛仅用于测试验证（对比解析结果），不在计算和可视化中使用。

### 7. 缓存策略

`_gold.py` 将多金 PDF/CDF 的卷积结果通过 pickle 缓存到项目根目录 `.cache/`，按池（character / weapon）分别存储 `{label}-pdfs.pkl` 和 `{label}-cdfs.pkl`。

首次计算约 0.1s（12 次卷积），缓存命中后加载 < 1ms。缓存文件随 Python 版本和 pickle 协议变化自动失效重建。

### 8. long-term 双模型解耦

`long_term.py` 用一个通用迭代卷积函数 `_solve_exact(n_states, p_up, max_n, p_gold, p_gold2)` 同时支持：

- **Pre-5.0**（2 状态，p_up=[0.5, 1.0]）：纯 50/50 + 大保底，稳态每 UP ~93.75 抽
- **Post-5.0**（4 状态，p_up=CAPTURE_RADIANCE_WIN_RATE）：捕获明光，稳态每 UP ~90.3 抽

`LongTermState(n_pre_50, n_post_50)` 指定两段 UP 数量。工厂函数 `make_long_solver(state, method)` 预计算 1..N 的 PDF 并返回标准 solver callable，直接喂给 `viz/long_term.py` 的 `plot_long_term_luck`。

混合场景（N1>0, N2>0）通过卷积连接：总分布 = conv(pre_N1_pdf, post_N2_pdf)。CLT 方法下直接矩相加。

默认 exact，N=500 约 1.2s。CLT 方法 ~20ms，仅用于快速预览或 N>500。

### 9. 模块导入设计

- `import genshin_wish` 不应触发 matplotlib 导入。`viz/` 模块按需加载，不在 `__init__.py` 中引用。
- 计算模块（`character.py`、`weapon.py`、`joint.py`、`_gold.py`）不 import 任何绘图库。
- `viz/_base.py` 的 `setup_style()` 需用户显式调用，不在 import 时自动执行（避免无头环境下崩溃）。

---

## 依赖

| 依赖 | 用途 |
|------|------|
| `numpy` | 数组运算、卷积 (`np.convolve`)、累积和 (`np.cumsum`)、搜索 (`np.searchsorted`) |
| `scipy` | CLT 正态分布 CDF/PPF (`scipy.stats.norm`)、FFT 加速（备选） |
| `matplotlib` | 全部可视化（`viz/` 模块） |
| `click` | CLI 命令定义与参数解析 |

所有数值计算使用 `np.float64`，卷积精度敏感。

---

## 测试策略

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_gold.py` | PDF 构建正确性（关键位置数值校验）、归一化、多金 PDF 长度 |
| `test_character.py` | guarantee_seq 概率和、边界情况（n_up=0、guaranteed+n_up=1）、CLT 一致性、monotonicity |
| `test_weapon.py` | 权重计算与归一化、命定值重置逻辑、prev_standard 分支、count_b 拒绝 |

测试框架：pytest。

无集成测试。回归验证通过手工对比 `ref/` 关键数值（期望抽数、分位点），差异要求 < 0.01%。

---

## 命名约定

- **`_` 前缀模块**（`_constants.py`、`_gold.py`、`_capture_radiance.py`）：内部实现，不承诺 API 稳定。
- **公开模块**（`character.py`、`weapon.py`、`joint.py`）：API 稳定，对外暴露。
- **`_` 前缀函数**（如 `_single_copy_weights`、`_compute_pdf_cdf`）：模块内部使用。
- **`ref/`**：旧参考代码，只读，禁止修改。
