# scripts/CLAUDE.md

## 脚本定位

| 脚本 | 用途 | 输出到 | 角色 |
|------|------|--------|------|
| `main_analysis.py` | 统一调用 `analysis/task*.py`（默认需显式 `--plot-only`） | — | 用户工具 |
| `main_plot.py` | 一键生成全部标准图表，通过 flag 路由到 `plots/` 子模块 | `output/` | 用户工具 |
| `plots/character.py` | 角色池图表：CDF, fan, column, rolls2gold | `output/character/` | 用户工具 |
| `plots/weapon.py` | 武器池图表：PDF, CDF, target | `output/weapon/` | 用户工具 |
| `plots/multi_gold.py` | 十连多金概率图表 | `output/multi-gold/` | 用户工具 |
| `plots/long_term.py` | 长期欧非演变图表 | `output/character/long-term/` | 用户工具 |
| `plots/nstd.py` | n_std 分布及条件抽数分布 | `output/character/std/` | 用户工具 |
| `analysis/task1_n_up_to_pulls.py` | A组：五种方法速度对比 + CLT 精度验证，支持 `--fit` 斜率拟合 | `output/analysis/task1-n_up-to-pulls/` | 开发分析 |
| `analysis/task2_n_up_n_std_to_pulls.py` | B组：dp-path vs dp-golds 条件分布 | `output/analysis/task2-n_up-n_std-to-pulls/` | 开发分析 |
| `analysis/task3_n_up_to_n_std.py` | C组：dp-path vs dp-golds n_std 分布 | `output/analysis/task3-n_up-to-n_std/` | 开发分析 |
| `analysis/clt_error.py` | CLT 近似误差分析 (N=1..100) | `output/analysis/clt-error/` | ~~DEPRECATED~~ |
| `analysis/solver_compare.py` | 多 solver 精度/速度/收敛对比 (N=1..100) | `output/analysis/solver-compare/` | ~~DEPRECATED~~ |
| `analysis/up_dist_methods.py` | 方案一/二/三性能对比与精度验证 | `output/analysis/up_dist_methods/` | ~~DEPRECATED~~ |

## 约定

- 分析脚本只输出图表 + data.json，不嵌入分析文本。分析和结论由人写在对应 `output/analysis/.../README.md` 中。
- `output/analysis/` 目录结构由脚本自动创建，不手动维护。
- 所有图表使用 `setup_style()` 统一风格。
