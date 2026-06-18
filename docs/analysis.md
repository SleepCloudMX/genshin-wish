<h1>分析与验证</h1>

[TOC]

开发分析工具，用于验证模型精度和比较算法方案。输出到 `output/analysis/`。

## CLT 误差分析

4 状态捕获明光精确解 vs CLT 近似的误差，N=1..100。

```bash
python scripts/analysis/clt_error.py
```

输出：`output/analysis/clt-error/` — 误差曲线图 + 数据 + 结论。

误差以每 UP 平均抽数衡量。CLT 分位点公式：$\mu_1 + \sigma_1 \cdot \Phi^{-1}(q) / \sqrt{N}$。

**收敛点（相对误差 < 2%）：**

| 分位点 | 收敛 N | 说明 |
|--------|--------|------|
| 1% | N=31 | 收敛最慢，CLT 在 N<30 时可能为负 |
| 10%/30%/50%/70%/90%/99% | N ≤ 3 | 快速收敛 |

N=100 时所有分位 CLT 误差 < 1.1 抽/UP，中部 < 0.2 抽/UP。**CLT 在 N ≥ 7 时完全可靠。**

## Solver 对比

5 种 long-term solver 的精度、收敛性、速度对比，N=1..100。

```bash
python scripts/analysis/solver_compare.py
```

输出：`output/analysis/solver-compare/` — 精度图、收敛图、速度图 + 数据 + 结论。

| 方案 | 模型 | 方法 | 推荐 |
|------|------|------|------|
| A | 55/45 固定 win rate | 独立同分布卷积 | 快速估算 |
| C | 55/45 | FFT 加速 | 不推荐 |
| D | 55/45 | CLT | 不推荐 |
| E | 捕获明光 4 状态 | 迭代卷积 (ground truth) | **N ≤ 500 首选** |
| F | 捕获明光 4 状态 | CLT | N > 500 |

> B（55/45 2 状态矩阵）已移除——结构性错误导致 ~9 抽/UP 的系统性低估。

**关键数据（N=100）：**

| 方案 | 耗时 | 说明 |
|------|------|------|
| A（55/45 naive） | 20ms | numpy 自动 FFT 加速 |
| C（55/45 FFT） | 148ms | 每步 IFFT 开销，反而不如 A |
| D/F（CLT） | 22ms | 几乎全是 scipy norm.ppf 开销 |
| E（4-state exact） | 103ms | 每步 7 次卷积，精度最高 |

**结论：** N ≤ 500 推荐 E（4-state exact，N=100 仅 ~100ms），N > 500 用 F（4-state CLT）。55/45 模型不推荐——精度不如 4-state，速度优势无实际意义。
