# scripts/CLAUDE.md

## 脚本定位

| 脚本 | 用途 | 输出到 | 角色 |
|------|------|--------|------|
| `plot_all.py` | 一键生成全部标准图表 | `output/character/`, `output/weapon/`, `output/multi-gold/` | 用户工具 |
| `analysis/clt_error.py` | CLT 近似误差分析 (N=1..100) | `output/analysis/clt-error/` | 开发分析 |
| `analysis/solver_compare.py` | 多 solver 精度/速度/收敛对比 (N=1..100) | `output/analysis/solver-compare/` | 开发分析 |
| `analysis/up_dist_methods.py` | 方案一/二/三性能对比与精度验证 | `output/analysis/method-compare/` | 开发分析 |

## 约定

- 分析脚本只输出图表 + data.json，不嵌入分析文本。分析和结论由人写在对应 `output/analysis/.../README.md` 中。
- `output/analysis/` 目录结构由脚本自动创建，不手动维护。
- 所有图表使用 `setup_style()` 统一风格。
