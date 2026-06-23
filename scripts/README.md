# scripts/

脚本目录，分为三类：

| 文件 | 说明 |
|------|------|
| `main_plot.py` | 一键生成全部标准图表（路由到 `plots/`） |
| `main_analysis.py` | 统一运行分析脚本（路由到 `analysis/task*.py`） |

## 绘图 (`plots/`)

| 脚本 | 输出 |
|------|------|
| `plots/character.py` | `output/character/` — CDF / fan / column / rolls2gold |
| `plots/weapon.py` | `output/weapon/` — PDF / CDF / target |
| `plots/multi_gold.py` | `output/multi-gold/` — 十连多金概率 |
| `plots/long_term.py` | `output/character/long-term/` — 长期欧非演变 |
| `plots/nstd.py` | `output/character/std/` — 常驻角色分布 |

每个 `plots/*.py` 可独立运行。

```bash
python scripts/main_plot.py            # 生成全部图表
python scripts/main_plot.py -c -w      # 仅角色 + 武器
python scripts/main_plot.py -n         # 仅 n_std
```

## 分析 (`analysis/`)

| 脚本 | 说明 |
|------|------|
| `analysis/task1_n_up_to_pulls.py` | A组：五种方法速度对比 + CLT 精度验证 |
| `analysis/task2_n_up_n_std_to_pulls.py` | B组：dp-path vs dp-golds 条件分布 |
| `analysis/task3_n_up_to_n_std.py` | C组：dp-path vs dp-golds n_std 分布 |
| `analysis/clt_error.py` | DEPRECATED |
| `analysis/solver_compare.py` | DEPRECATED |
| `analysis/up_dist_methods.py` | DEPRECATED |

```bash
python scripts/main_analysis.py --plot-only              # 全部 task (plot-only)
python scripts/main_analysis.py --plot-only --tasks 1 --fit
```

## CLI 示例 (`cli_examples/`)

| 文件 | 说明 |
|------|------|
| `cli_examples/plot.sh` | `genshin-wish plot` 单图绘制示例 |
| `cli_examples/calc_prob.sh` | `genshin-wish char/weapon/std/joint` 概率查询示例 |

## 约定

见 `scripts/CLAUDE.md` 和 `scripts/analysis/CLAUDE.md`。
