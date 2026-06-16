# CLAUDE.md

## 项目概述

genshin-wish — 原神抽卡概率计算器。基于玩家总结的概率机制，**解析计算**（非蒙特卡洛）角色池和武器池的抽数分布。

## 项目结构

```
src/genshin_wish/       # Python 包
├── _constants.py       # PoolConfig, STABLE_P, 概率参数
├── _gold.py            # 出金 PDF/CDF (pickle 缓存到 .cache/)
├── _capture_radiance.py # guarantee_seq (捕获明光 win/loss 序列枚举)
├── character.py        # CharacterState, UpDistribution, up_distribution
├── weapon.py           # WeaponState, WeaponTarget, weapon_up_distribution
├── joint.py            # 角色+武器联合分布
├── viz/                # matplotlib 可视化 (10 个模块)
│   ├── _base.py        # setup_style(), 配色, 通用工具
│   ├── cdf.py          # plot_annotated_cdf, plot_up_cdf_lines
│   ├── heatmap.py      # plot_percentile_heatmap
│   ├── column.py       # plot_success_column_chart
│   ├── fan.py          # plot_luck_fan (合并 3/5 interval)
│   ├── stack.py        # plot_stacked_up_probabilities
│   ├── staircase.py    # plot_staircase_luck_fan
│   ├── long_term.py    # plot_long_term_luck (合并 3/5 interval)
│   ├── multi_gold.py   # plot_multi_gold
│   └── pdf.py          # plot_base_pdfs
└── cli/main.py         # click CLI (genshin-wish 命令)

ref/                    # 旧参考代码，只读，禁止修改
tests/                  # pytest
scripts/plot_all.py     # 一键生成全部图表
output/                 # 图表输出 (gitignore)
.cache/                 # PDF/CDF pickle 缓存 (gitignore)
docs/                   # 详细文档
```

## 运行

```bash
# 安装
pip install -e .

# 测试
python -m pytest tests/ -v

# 生成图表
python scripts/plot_all.py
```

测试环境：`conda activate ai`（Python 3.12，numpy 2.x，scipy 1.16，matplotlib 3.10）

## 开发约定

- **`_` 前缀模块** 是内部实现，不承诺 API 稳定。公开 API 在 `character.py`、`weapon.py`、`joint.py`。
- **`ref/` 只读**。新旧代码通过关键数值对比验证（期望抽数、分位点），差异 < 0.01%。
- **`import genshin_wish` 不应触发 matplotlib 导入**（viz 模块按需导入）。
- **概率计算不 import matplotlib**。`character.py`、`weapon.py`、`joint.py` 不依赖任何绘图库。
- **解析解优先**。蒙特卡洛仅用于测试验证。CLT 在 `n_up > CLT_THRESHOLD (7)` 时使用，`method` 字段标注。
- **PDF 使用 float64**。卷积精度敏感。
- **程序输出放 `output/`**（已 gitignore）。图表、分析结果等程序生成的文件统一放到 `output/` 下按用途分子目录。不要放到 `docs/`。
- **PoolConfig 参数含义**：`soft_pity_start` 是概率首次超过 `base_rate` 的 1-indexed 抽数。如角色池 pulls 1~73 恒定 0.6%，soft pity 从 pull 74 开始。
- **`prev_standard` 不影响 `character.py`**，仅 `weapon.py` 使用。
- **Capture Radiance**：`p_up[k] = 0.5 + 0.5 * capture_radiance[k]`。稳态概率 `STABLE_P` 由 `guarantee_seq` 转移矩阵解析导出。
- **武器池仅支持「定轨不取消」**。同时要两把不同限定武器列入后续需求。
- **提交前运行 `python -m pytest tests/ -v`** 确保 26 个测试全绿。
- **CLI 入口**：`pyproject.toml` 的 `[project.scripts]` 注册，启动 `genshin_wish.cli.main:main`。
