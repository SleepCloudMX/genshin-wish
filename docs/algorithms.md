<h1>算法总览</h1>

[TOC]

角色池五种精确求解方案的原理、复杂度、实验对比与推荐选择。

记 $n = n_{\text{uncertain}} = n_{up} - [\text{guaranteed}]$，$m = 90$（硬保底抽数）。

---

## 方案 1：dp-pulls（逐抽 DP）

每抽取一抽，在 (k_miss, gold_count) 状态上递推概率质量，等同于逐抽蒙特卡洛的解析版。

- **复杂度**：$O(n^2 \cdot m^2)$
- **适用任务**：任务 1（任务 2/3 可扩展 n_std 维度，但更慢）
- **当前用法**：仅基准测试基线，不在 auto 中使用
- **结论**：n=10 时比 dp-path 慢 100×，无实用价值

---

## 方案 2：dp-path（win/loss 序列枚举）

枚举所有 win(1)/loss(2) 序列，$2^n$ 条。每条序列天然携带 gold_count（= sum(seq)）和 n_std（= count(2)），按金数分组后加权多金 PDF。

- **复杂度**：$O(2^n)$
- **适用任务**：全部三个任务
- **当前用法**：显式指定 `--method dp-path`，n≤20
- **性能**：n=10 时 1024 条序列 ~0.5ms，n=20 时 ~1M 条序列 ~611ms
- **结论**：小 n 自然枚举最快（无 DP 表开销），n>10 后被 dp-golds 反超

---

## 方案 3：dp-state（迭代卷积）

按 k_miss 状态聚合抽数 PDF（4 个状态 × 每步 2 次卷积），利用马尔可夫性质递推。仅需 k_miss 维度，不区分 n_std。

状态转移（第 i 步）：

| 事件 | 概率 | 卷积 | 下一 k_miss |
|------|------|------|-------------|
| Win | $p_{up}[k]$ | `pdf[k] ⊗ p_gold` → new[0] | 0 |
| Loss | $1 - p_{up}[k]$ | `pdf[k] ⊗ p_{g2}` → new[k+1] | min(k+1, 3) |

- **复杂度**：$\sum_{i=1}^n O(i \cdot m \cdot \log) = O(n^2 \cdot m \cdot \log(n \cdot m))$
- **适用任务**：仅任务 1
- **当前用法**：显式指定 `--method dp-state`
- **性能**：n=500 约 5190ms
- **结论**：n>10 时曾是最优，现被 dp-golds 取代

---

## 方案 4：dp-golds（金数计数 DP）★ 当前默认

### 原理

不逐序列枚举，而是 DP 直接统计每种 (gold_count, n_std) 组合的概率。

**任务 1 降维版**：状态 $(i, k)$，仅追踪 gold_count（边际化 n_std）。

**完整版**（任务 2/3）：状态 $(i, k, s)$，$s$ = 累计常驻数。

转移（从状态 $(i, k, s)$，概率质量 $p$）：

| 事件 | 概率 | 金数增量 | 下一状态 |
|------|------|----------|----------|
| Win | $p_{up}[k]$ | +1 | $(i+1, 0, s)$ |
| Loss | $1 - p_{up}[k]$ | +2 | $(i+1, \min(k+1, 3), s+1)$ |

Loss 仅在 $k \neq 3$ 时可行。

### 后处理（金数 → 抽数）

DP 产出概率表后加权多金 PDF：

- **任务 1**：$\text{pdf} = \sum_g P(g) \cdot \text{pdfs}[g]$
- **任务 2**：$\text{pdf}[n_{std}] = \sum_g P(g \mid n_{std}) \cdot \text{pdfs}[g]$
- **任务 3**：$P(n_{std}) = \sum_g P(g, n_{std})$（仅边际化，无需 PDF 卷积）

### 实验数据

| n | dp-path | dp-state | dp-golds |
|---|---------|----------|----------|
| 10 | 0.5 ms | 2 ms | 0.4 ms |
| 100 | — | 103 ms | 3.6 ms |
| 500 | — | 5190 ms | **111 ms** |

任务 1：dp-golds 在所有 n 领先 dp-state，在 n≥6 领先 dp-path。

任务 2：dp-golds 在 n≥6 时更快，n=1–5 与 dp-path 接近。

任务 3：dp-golds 在 n≥7 时更快；任务 3 无需 PDF 卷积，仅 O(n²) 整数 DP，极快。

### 推荐

| n_uncertain | 首选 | 说明 |
|-------------|------|------|
| ≤ 500 | dp-golds | auto 默认，O(n²) + O(n²·m)，全面领先 |
| > 500 | CLT | 精度已收敛（中位数误差 <0.01%） |

---

## 方案 5：dp-state-golds（多维迭代卷积）

方案 3 的扩展：`pdf_state[k][s]` 按 n_std 分层的 PDF，每步对每个 (k, s) 做卷积。

- **复杂度**：$O(n^3 \cdot m \cdot \log)$
- **适用任务**：全部三个
- **当前用法**：待实现（仅理论分析）
- **结论**：方案 4 常数小得多（整数 vs 长数组），方案 5 无实用优势

---

## CLT：混合矩正态近似

### 原理

CLT 将 $n$ 个 UP 视为独立同分布近似，但 k_miss 非固定——会在序列中从初始值迁移到稳态分布。

**修正后的混合矩方法**：

- 首 UP：从初始 $k_{miss}$ 出发，矩 $\mu_{first}, \sigma^2_{first}$ 由单 UP 精确计算
- 剩余 $n-1$ 个 UP：使用稳态矩 $\mu_{steady}, \sigma^2_{steady}$（STABLE_P 加权平均）

$$\mu_n = \mu_{first} + (n-1) \cdot \mu_{steady}$$

$$\sigma^2_n = \sigma^2_{first} + (n-1) \cdot \sigma^2_{steady}$$

离散正态：

$$P(\text{pulls} = p) \approx \Phi\left(\frac{p+0.5 - \mu_n}{\sigma_n}\right) - \Phi\left(\frac{p-0.5 - \mu_n}{\sigma_n}\right)$$

### 精度

| n | exact | CLT | 相对误差 | 中位数偏差 |
|---|-------|-----|---------|-----------|
| 50 | 4521.4 | 4519.8 | 0.036% | 4 pulls |
| 100 | 9038.0 | 9036.5 | 0.017% | 4 pulls |
| 500 | 45170.4 | 45170.0 | 0.0008% | 3 pulls |

per-UP 误差随 n↗收敛到 0。auto 在 n>500 自动使用。

### 与纯稳态矩的对比

| 方法 | $\mu_n$ | n=500 误差 | 说明 |
|------|--------|-----------|------|
| 纯稳态矩（旧正确版） | $n \cdot \mu_{steady}$ | ≈ 0.01% | 忽略初始 k_miss，大 n 极准 |
| 混合矩（当前） | $\mu_{first} + (n-1)\mu_{steady}$ | ≈ 0.001% | 首个 UP 精确，剩余稳态 |
| 纯初始矩（bug 版） | $n \cdot \mu_1(k_{miss})$ | 3.6% | ❌ 偏差不收敛 |

---

## 方法覆盖矩阵

| 方案 | 任务 1 | 任务 2 | 任务 3 | 精确 | 复杂度 |
|------|:---:|:---:|:---:|:---:|------|
| dp-pulls | ✓ | (✓) | (✓) | ✓ | $O(n^2 \cdot m^2)$ |
| dp-path | ✓ | ✓ | ✓ | ✓ | $O(2^n)$ |
| dp-state | ✓ | | | ✓ | $O(n^2 \cdot m \cdot \log)$ |
| dp-golds | ✓ | ✓ | ✓ | ✓ | $O(n^2 \cdot m)$ |
| dp-state-golds | ✓ | ✓ | ✓ | ✓ | $O(n^3 \cdot m \cdot \log)$ |
| CLT | ✓ | | | ✗ | $O(1)$ |

(✓) = 理论可行但过于缓慢，不予实现。

---

## 性能对比总表

任务 1，n=500（k_miss=0, pity=0）：

| 方案 | 耗时 | vs dp-golds | 状态 |
|------|------|------------|------|
| dp-pulls | —（n=7 时 3.3s） | — | 已废弃 |
| dp-path | —（仅到 n=20） | — | 可显式指定 |
| dp-state | 5190 ms | 47× slower | 可显式指定 |
| dp-golds | **111 ms** | 1× | **auto ≤500** |
| CLT | **2 ms** | 0.02× | **auto >500** |

---

## FFT 卷积优化评估

曾考虑用 FFT 加速卷积操作。结论：不需要。

- `np.convolve` 已在所有测试尺寸（100–90000）比 `fftconvolve` / `oaconvolve` 快，numpy 内部自动选择 direct/FFT 算法
- FFT power 方法（`IFFT(FFT(p1)^k)`）在 k=101 时误差已达 2.0，数值不可用
- 真正的优化方向是**绕过卷积**（dp-golds 的整数 DP + 加权 PDF），而非加速卷积本身

---

## 参考

- 方法选型与实验设计：`docs/ai-output/1-refactor/13-tasks-solutions.md`
- CLT bug 修复记录：`docs/ai-output/1-refactor/14-clt-bug-postmortem.md`
- 概率机制：`docs/mechanism.md`
