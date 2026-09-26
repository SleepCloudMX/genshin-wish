# web/CLAUDE.md

## 定位

纯静态站点：`genshin-wish` 的交互式前端（计算器 + 画廊）。**运行时不依赖 Python**——概率内核用 JS 重算，与 `src/genshin_wish/` 平行维护。

入口是仓库根的 `index.html`，本目录只放站点资源。

## 硬约束

- **必须能 file:// 双击打开**：不得使用 ES modules（Chrome 在 file:// 下按 CORS 拒绝）、不得 `fetch` 本地文件、不得引入构建步骤。
- 全部脚本是普通 `<script src>`，在 `index.html` 底部按依赖顺序排列；跨文件通信用全局命名空间 `Wish`。
- 不引 CDN（离线可用）。第三方库放 `vendor/`，固定版本并提交。
- 不加载 webfont。

## 文件结构

```
web/
├── css/app.css          设计令牌 + 布局 + 组件 + 暗色 + 响应式（单文件）
├── vendor/              ECharts 5.5.1、MathJax 3.2.2（tex-svg；本地 vendored，不引 CDN）
├── js/core/             概率内核：constants / stats / gold / character / banners / longterm
├── js/ui/               charts（line / curve / regions / bars / table）、controls、
│                        panels（数据条等片段）、math（LaTeX 渲染）
├── js/modules/          每个页面模块：{id, title, controls(), views:{render}}
│                        char 角色池 / weapon 武器池 / joint 角色+武器 / std 常驻池 /
│                        nstd 常驻角色数 / radiance 捕获明光 / multi-gold 十连多金 /
│                        longterm 长期欧非 / player 个人记录 /
│                        about 模型与误差 / algorithms 算法 / perf 性能与验证
├── js/app.js            hash 路由、外壳渲染、主题、状态条
├── data/analysis.js     实验数据（由 scripts/build_web_data.py 生成，勿手改）
└── dev/parity-node.js   JS↔Python 一致性校验的 Node 端（入口是 scripts/parity.py）
```

图表类型与用途：`line` 类目横轴折线（CDF、PDF）；`curve` 数值/对数横轴折线（性能实验图）；
`regions` 类目横轴的区间图（扇形带、堆叠面积、阶梯——**面积堆叠只在类目轴上生效**，
数值轴会画成从 0 起填充）；`bars` 柱状（支持渐变、对数轴与叠加散点/折线）；`table` 数值表。

`js/modules/*` 里没有控件的模块（about / algorithms / perf）会自动隐藏参数面板与状态条，
标题下也不显示视图切换。

## 分层规则

- **`js/core/*` 禁止出现 `document` / `window` / `localStorage`**（只通过 IIFE 的 `global` 参数挂命名空间）。这样一致性校验脚本能用 Node `vm` 直接加载内核做数值比对，无需任何改动。
- `js/ui/*` 只依赖 `Wish.core`，不依赖模块层。
- `js/modules/*` 只通过 `Wish.ui` / `Wish.core` 做事，不直接创建 ECharts 实例。
- 每个文件统一骨架：

```js
(function (global) {
  'use strict';
  var W = global.Wish = global.Wish || {};
  var C = W.core = W.core || {};
  // ...
})(typeof globalThis !== 'undefined' ? globalThis : this);
```

## 与 Python 侧的一致性

**JS 是 `src/genshin_wish/` 的移植，不是重新设计。** 移植时的硬性要求：

- 索引语义照抄：`pdf[i]` = 恰好 i 抽，`cdf[i]` = ≤i 抽，**index 0 是占位**。
- `searchsorted` 用 `side='left'`，且**允许返回数组长度**（返回 `length-1` 会让分位点整体偏 1）。
- 算法分支、pity 平移卷积、`STABLE_P` 不归一、CLT 的 ±0.5 连续性修正等细节逐行对齐。
- **改动内核后必须跑 `python scripts/parity.py`**：Python 生成基准 → Node 加载 `web/js/core/*`
  重算 → 逐项比对（280 余组用例、4500 余项，含正态分布、角色/武器/常驻/联合、常驻数、
  明光、5.0 前机制、十连多金、长期分布），退出码给出结论。新增内核函数时同步补用例。

JS 相对 Python 的已知差异（有意为之，写在代码注释里）：

- `pity>0` 时 Python 退回指数枚举（`n_uncertain ≤ 20`），JS 用卷积线性性等价改写，可精算到 30 UP。
- `n_std_conditional_pulls` 在 `n_uncertain ≤ 0` 时 Python 取错了金 PDF 表，JS 按正确语义实现，该分支不参与 parity。

## 数值上限

| 路径 | 上限 | 说明 |
|---|---|---|
| 金 PDF 表 | 64 金 | 约 6MB 峰值内存 |
| 角色精算 | 30 UP | 界面限制；更大规模走「长期欧非」 |
| 武器精算 | 5 把 | R5 封顶 |
| 常驻精算 | 30 金 | — |
| 明光 / 常驻数 | 100 / 30 UP | 常驻数为 O(n³) DP |
| 长期精算 | 100 UP | 约 1 秒（N=100）；勾选「快速近似」走 CLT，毫秒级 |

## 文案与公式

- **书面技术语体。** 面向玩家的页面同样是技术文档：不用口语、第二人称、反问句；行文对齐 `docs/mechanism.md`。完整清单见 `docs/ai-output/memory.md`。
- **不把实现细节当卖点。** 页面里不出现「浏览器内实时计算」「不依赖服务器」这类对读者无信息量的表述；确有解释价值的放进 `#/about`。
- **同一组数字只出现一次**，摘要与详情用链接连接；提示类内容不要做成常驻横幅。
- **数学公式一律 LaTeX**：行内 `\( ... \)`、行间 `\[ ... \]`，模块声明 `math: true` 后由 `js/ui/math.js` 调用 MathJax 渲染（`vendor/mathjax-tex-svg.js`，SVG 输出，无需字体文件）。
  - ⚠ **JS 字符串里的反斜杠必须双写**（`\\(`、`\\text`、`\\sigma`）。单写会被 JS 当转义序列吃掉（`\(`→`(`、`\t`→制表符），且不报错。改完必须在浏览器里确认渲染，不能只跑 `node --check`。
- **代码、标识符用等宽字体**（`<code>`）。
- **内容与容器同宽**：纯文档模块标记 `layout: 'doc'` 收窄容器；图表页让说明文字与图表等宽。

## 约定

- 界面中文，代码英文；不加 emoji 图标，图标用内联 SVG。
- 颜色一律走 CSS 变量（`--gold` 等）或 `Wish.core.COLORS`，不在组件里写裸 hex。
- 所有数字列用 `font-variant-numeric: tabular-nums`。
- 参数写入 URL hash，可分享；hash 是唯一的路由状态来源。
