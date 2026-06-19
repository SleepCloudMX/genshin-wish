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

---

## UP 分布计算方法对比

三种精确求解「n_up 个 UP 所需抽数分布」的方法：3D DP、指数枚举（当前 `character.py`）、迭代卷积（当前 `long_term.py`）。原理分析见 `docs/ai-output/1-refactor/10-up-dist-dp-methods.md`。

```bash
python scripts/analysis/up_dist_methods.py --dp-vs-enum     # DP vs 枚举
python scripts/analysis/up_dist_methods.py --enum-vs-conv   # 枚举 vs 卷积
```

输出：`output/analysis/up_dist_methods/dp-vs-enum/` 和 `enum-vs-conv/` — 精度图 + 速度图 + 数据 + 结论。

| 方案 | 方法 | 复杂度 | n_up=10 | n_up=20 | n_up=500 |
|------|------|--------|---------|---------|---------|
| 一（DP-full） | 3D DP 手动卷积 | $O(n_\text{up}^2 \cdot m^2)$ | 57ms | — | — |
| 一（DP-prune） | 同上 + 剪枝 | 同上，常数更大 | 67ms | — | — |
| 二（Enum） | 指数枚举序列 | $O(2^{n_\text{up}})$ | 0.5ms | 611ms | 不可用 |
| 三（Conv） | 迭代卷积 FFT | $O(n_\text{up}^2 \cdot m \cdot \log)$ | 1.1ms | 3.8ms | ~1.2s |

**结论：**

- **方案一（DP）无实用价值。** n_up=10 时比枚举慢 100×，剪枝版反而更慢（检查开销超过跳过收益）。精度极好但与枚举完全等价，没有独立优势。
- **方案二（枚举）是小 n_up 首选。** n_up ≤ 10 时 < 1ms，且天然支持多目标统计（常驻计数需记录序列中 $2$ 的个数即可）。
- **方案三（卷积）是大 n_up 首选。** n_up > 10 后速度碾压枚举（n_up=20 时快 160×），参数化 n_states 同时支持 pre/post-5.0。

**已集成到 `character.up_distribution`**：默认 `method="auto"` 自动选择 dp-path（≤10）/ dp-state（10~500）/ clt（>500+warning）。CLI 支持 `--method auto|dp-path|dp-state|clt`。详见表 `main.py:char`。
