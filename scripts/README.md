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
| `plots/radiance.py` | `output/character/radiance/` — 捕获明光次数分布 |
| `plots/joint.py` | `output/joint/` — 角色+武器联合 CDF |

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
| `cli_examples/calc_char.sh` | `genshin-wish char` 角色池查询示例 |
| `cli_examples/calc_weapon.sh` | `genshin-wish weapon` 武器池查询示例 |
| `cli_examples/calc_std.sh` | `genshin-wish std` 常驻池查询示例 |
| `cli_examples/calc_joint.sh` | `genshin-wish joint` 联合计算示例 |
| `cli_examples/plot_char.sh` | `genshin-wish plot char-*` 角色池绘图示例 |
| `cli_examples/plot_nstd.sh` | `genshin-wish plot nstd-*` 常驻分布绘图示例 |
| `cli_examples/plot_radiance.sh` | `genshin-wish plot radiance-*` 捕获明光绘图示例 |
| `cli_examples/plot_weapon.sh` | `genshin-wish plot weapon-*` 武器池绘图示例 |

## 约定

见 `scripts/CLAUDE.md` 和 `scripts/analysis/CLAUDE.md`。
