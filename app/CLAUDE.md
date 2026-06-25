# app/CLAUDE.md

## 定位

Gradio Web UI，提供 `genshin-wish` 的图形化交互入口。面向不熟悉命令行的玩家，支持调参计算 + 实时图表展示。

**`app/` 是 `src/genshin_wish/` 的消费者，不参与库的公开 API。** `import genshin_wish` 不应触发 gradio 导入。

启动：

```bash
python app/main.py
```

依赖 `gradio>=5.0`，已加入 `pyproject.toml` 的 `[project.optional-dependencies] ui` 组。

## 文件结构

```
app/
├── __init__.py
├── main.py             # gr.Blocks 入口：主题、标题、9 个 Tab 组装、launch()
├── plot_utils.py       # viz 函数薄封装：生成 temp/gradio/*.png → 返回路径
├── CLAUDE.md           # 本文件
└── tabs/
    ├── __init__.py
    ├── character.py    # 角色池：CDF + PDF + 分位点表 + 双向查询
    ├── weapon.py       # 武器池
    ├── joint.py        # 联合计算（角色+武器）
    ├── standard.py     # 常驻池
    ├── nstd.py         # 常驻分布：柱状图 + 条件 PDF 迭图 + k_miss 热力图
    ├── radiance.py     # 捕获明光：柱状图 + k_miss 热力图
    ├── fan.py          # 幸运扇形图
    ├── multi_gold.py   # 十连多金概率
    └── long_term.py    # 长期欧非演变（固定 3 区间）
```

## 约定

### 新增 Tab

每个 tab 模块导出 `build_tab()` 函数，在 `gr.Tab()` 上下文内创建所有组件并绑定回调。`app/main.py` 调用 `build_tab()` 组装。

Tab 内部结构：
1. `gr.Markdown` 引导文字（解释用途）
2. 参数区（常用参数直接展示，高级参数放入 `gr.Accordion("高级设置", open=False)`）
3. 查询区（仅计算型 Tab：抽数→概率 + 分位点→抽数）
4. `gr.Button("计算", variant="primary")` — **不设 `live=True`**，避免托滑块时频繁重算
5. 图表区：`gr.Image(label="...", type="filepath")` 接收 PNG 路径，`gr.Row()` + `gr.Column()` 实现横排 2 列

### 绘图

**不在 `app/` 内独立绘图。** 所有图表通过 `app/plot_utils.py` 调用 `src/genshin_wish/viz/` 的函数生成。

`plot_utils.py` 中的每个封装函数：
1. 生成 `temp/gradio/{name}_{uuid}.png` 路径
2. 调用原始 viz 函数，输出到临时路径
3. 返回文件路径字符串给 `gr.Image(type="filepath")`

临时文件由 viz 函数内部 `plt.close()` 自动清理 figure，PNG 文件留在 `temp/gradio/`（可定期清理，已 gitignore）。

返回给 Gradio 的规则：
- **单输出 callback**：直接 `return path`（不要 `return (path,)` — tuple 会导致 `ValueError`）
- **多输出 callback**：`return (path1, path2, ...)`

### 不修改 `src/`

UI 代码不修改 `src/genshin_wish/` 下任何文件。viz 函数的行为完全不变。如需新绘图能力，在 `app/plot_utils.py` 添加封装函数或自定义 matplotlib 代码（后者仅限 `app/` 内未覆盖的简单场景）。

## 设计决策

- **Gradio 而非 Streamlit**：计算模型是"调参→点按钮→出图"，Gradio 的 `Button.click` 触发机制更匹配（Streamlit 每次改参数都重跑全脚本）
- **`gr.Image` 而非 `gr.Plot`**：viz 函数输出高 DPI PNG（200-300 dpi），`gr.Image(type="filepath")` 直接展示，零质量损失
- **`sys.path` 路径处理**：`app/main.py` 顶部插入项目根到 path，无需 `pip install -e .` 即可运行
- **单文件回调 vs generator**：计算+渲染总耗时 1-2s，不做渐进展示（复杂度换 1s 体验改善，不值）

## 已知限制

- Gradio 无真正的路由/导航，Tab 超过 10 个时体验下降
- 移动端适配差
- 无服务端状态，无法 URL 参数分享查询
- 画廊不适合在 Gradio 做 — 留给阶段 2 web 前端（见 `docs/ai-output/3-ui/4-beyond-gradio.md`）
