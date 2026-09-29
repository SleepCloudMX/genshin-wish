# web/CLAUDE.md

## 定位

纯静态站点：`genshin-wish` 的交互式前端（参数可调的概率图表）。**运行时不依赖 Python**——概率内核用 JS 重算，与 `src/genshin_wish/` 平行维护。

导航分两组：**可视化**（角色池等九个图表页）与**说明**（机制误差、算法介绍、算法性能）。

首页按信息类型分四段：数据准确度（无框正文）、期望与分位（每池一张小表）、
星辉等效抽数（卡片 + 推导悬浮）、可视化（平铺入口块）。

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
│                        about 机制误差 / algorithms 算法介绍 / perf 算法性能
├── js/app.js            hash 路由、外壳渲染、主题、状态条
├── data/analysis.js     实验数据（由 scripts/build_web_data.py 生成，勿手改）
├── dev/parity-node.js   JS↔Python 一致性校验的 Node 端（入口是 scripts/parity.py）
└── dev/bench-pulls-joint.js  站点内核的性能基准（入口是 scripts/analysis/task4_pulls_to_joint.py）
```

图表类型与用途：`line` 类目横轴折线（CDF、PDF）；`curve` 数值/对数横轴折线（性能实验图）；
`regions` 类目横轴的区间图（扇形带、堆叠面积、阶梯——**面积堆叠只在类目轴上生效**，
数值轴会画成从 0 起填充）；`bars` 柱状（支持渐变、对数轴、叠加散点/折线、`stack` 堆叠）；
`table` 数值表。

`js/modules/*` 里没有控件的模块（about / algorithms / perf）会自动隐藏参数面板与状态条，
标题下也不显示视图切换。页尾那条「机制参数取自社区总结的模型」由外壳统一输出，
模块标记 `noDisclaimer: true` 可不显示（机制误差页本身就是这条声明，故不重复）。

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
  重算 → 逐项比对（318 组用例、7592 项，含正态分布、角色/武器/常驻/联合、常驻数、固定抽数下
  的金数分布（两类池）、明光、5.0 前机制、十连多金、长期分布），退出码给出结论。新增内核函数时
  同步补用例。

JS 相对 Python 的已知差异（有意为之，写在代码注释里）：

- `pity>0` 时 Python 退回指数枚举（`n_uncertain ≤ 20`），JS 用卷积线性性等价改写，可精算到 30 UP。
- `n_std_conditional_pulls` 在 `n_uncertain ≤ 0` 时 Python 取错了金 PDF 表，JS 按正确语义实现，该分支不参与 parity。

## 数值上限

| 路径 | 上限 | 说明 |
|---|---|---|
| 金 PDF 表 | 64 金 | 约 6MB 峰值内存 |
| 角色精算 | 30 UP | 界面限制；更大规模走「长期欧非」 |
| 金数分布（给定抽数） | 10000 抽 | 1000 抽约 8 ms、10000 抽约 240 ms（G ≤ 209 次卷积） |
| 武器精算 | 5 把 | R5 封顶 |
| 常驻精算 | 30 金 | — |
| 明光 / 常驻数 | 100 / 30 UP | 常驻数为 O(n³) DP |
| 长期精算 | 100 UP | 约 1 秒（N=100）；界面只走精确卷积，不提供近似开关 |

CLT 是唯一的近似通道，**仅在 n > 500 时启用**（Python 侧 `CLT_THRESHOLD`）；站点内的各页都在精确路径内。

## 文案与公式

- **书面技术语体。** 面向玩家的页面同样是技术文档：不用口语、第二人称、反问句；行文对齐 `docs/mechanism.md`。完整清单见 `docs/ai-output/memory.md`。
- **不把实现细节当卖点。** 页面里不出现「浏览器内实时计算」「不依赖服务器」这类对读者无信息量的表述；确有解释价值的放进 `#/about`。
- **同一组数字只出现一次**，摘要与详情用链接连接；提示类内容不要做成常驻横幅。
- **数学公式一律 LaTeX**：行内 `\( ... \)`、行间 `\[ ... \]`，模块声明 `math: true` 后由 `js/ui/math.js` 调用 MathJax 渲染（`vendor/mathjax-tex-svg.js`，SVG 输出，无需字体文件）。
  - ⚠ **JS 字符串里的反斜杠必须双写**（`\\(`、`\\text`、`\\sigma`）。单写会被 JS 当转义序列吃掉（`\(`→`(`、`\t`→制表符），且不报错。改完必须在浏览器里确认渲染，不能只跑 `node --check`。
  - **首页的推导走悬浮 LaTeX**（`app.js` 的 `derivRow` + `.deriv`）：数值带虚线下划线，悬停或键盘聚焦时排版推导，正文里不必写公式；`opts.code` 可再挂一段可复制的 python（`copyCode`，剪贴板被拒时退化为选中代码）。
    MathJax 是 2MB 的 vendor，进入该区域先 `UI.math.preload()` 预热、首次悬停才真正排版；`UI.math.typeset` 返回 promise，排版完成前整块内容先不显形（`.deriv__body.is-ready`），失败时按老约定保留原文。
    浮层默认挂在数值**右侧、顶边与数值齐平**（表里的数值是纵排的，鼠标顺着往下看不会被浮层压住）；`placePop` 在排版后量一次：右侧放不下改挂左侧，下方放不下改底边对齐。数值与浮层之间的 8px 空隙由 `.deriv__pop::before` 铺一层透明的「桥」，鼠标移进浮层不会踩空关掉。纯文字浮层传 `math: false`，不为它拉 MathJax。
  - **悬浮推导的取舍**：官方口径的数（90.625 = 两个官方概率相乘）、能复算的推导（单金期望 = 软保底逐抽概率的生存和，配一段可复制的 python）都值得写；满命/满精直接乘上一行的期望（\(90.334\times7\approx632.32\)），结果同样取 5 位有效。注意本模型里 7 个 UP 的期望并不严格等于单 UP 的 7 倍（明光计数跨 UP 演化，且模型的有效不歪率不是整 55%），格面读数由 7 个 UP 的分布直接算得——末位对不上属正常，用 ≈ 盖过，不在主页解释。没有闭式的分位点不写。
  - **别写「不必卷积」这类反预期的话**：读者要么不知道卷积、要么早会算，先声明「不必做 X」只会让人以为 X 是默认做法。直接正面陈述方法（「单金期望 = 各抽仍未出金的概率之和」）。
  - **首页「期望与分位」是两张小表**（`statTable` + `.stattable`）：行 = 目标 + 口径（「1 个限定（按官方公示综合概率）」/「1 个限定（按玩家总结概率机制）」/「满命（按玩家总结概率机制）」，武器池同理），列 = 期望 / 50% / 90% / 99% 分位；期望列高亮，且一律 5 位有效数字（`sig5`，`toPrecision(5)`——保住 90.625 这类精确值，又不暗示精确到千分之一抽）。官方行只有期望，分位一律填「未知」（综合概率推不出分布），每个「未知」悬停说明「官方未公示具体概率机制，无法计算」；「按玩家总结概率机制」链到「机制误差」页。官方口径与玩家总结必须并排出现。
- **代码、标识符用等宽字体**（`<code>`）。
- **内容与容器同宽**：纯文档模块标记 `layout: 'doc'` 收窄容器；图表页让说明文字与图表等宽。

## 约定

- 界面中文，代码英文；不加 emoji 图标，图标用内联 SVG（`app.js` 的 `ICONS`，24 格 viewBox、
  1.8 描边、不填充）。导航一页一个图标，取该页计算对象的形状；首页入口复用同一套（`navIcon(id)`）。
  **图标要在 18px 下能认**：细碎图案（点阵、圆内套小星、并排的小人）会糊成一团，
  宁可换一个更简单、更直白的形状。
- 颜色一律走 CSS 变量（`--gold` 等）或 `Wish.core.COLORS`，不在组件里写裸 hex。
- 所有数字列用 `font-variant-numeric: tabular-nums`。
- 参数写入 URL hash，可分享；hash 是唯一的路由状态来源。
- **图内数值与单位之间不夹空格**（`637抽`、`79抽`），正文照常留空格。中文与数字之间的排版空隙在窄标注里太占位。
- **概率读数用 `P.pctAdaptive`**：越靠近 0 或 100 有效位数越多（0.2%/99.8% 之外各加一位，最多 4 位）。
- **低频视图标记 `advanced: true`**，默认收进「其他」；URL 直接指向时仍会展开并选中。
- **「已连歪次数」控件里值 4 表示稳态**（`C.STABLE_LOSS`，与 `MISS_LABELS` 的索引一致）；角色池、
  角色+武器、常驻角色数三页提供该选项：连歪次数未知，按 `STABLE_P` 的长期占比加权 `k_miss` = 0–3。
  内核由 `makeCharacterState({ stable: true })` 标记，`upDistribution`、`nStdDistribution`、
  `nStdConditionalPulls` 遇该标记即走混合（条件分布按各状态的联合概率加权后再归一），
  已垫抽数与大保底照常施加。
- **控件类型**：`range` 滑动条（拖动时实时重画）、`segmented` 分段、`switch` 开关、
  `number` 数字输入、`text` 文本框、`static` 只读推导值。`number` / `text` 只认 `change`
  （回车/失焦）——输入途中的中间值没有意义；`number` 超范围时夹回区间并写回输入框。
- **控件可写 `views: [...]`**，只在列出的视图里出现（序列输入对「次数分布」没有意义）；
  某个视图的参数全部被过滤掉时参数面板整体隐藏。`type: 'static'` 是只读的推导值，
  由 `UI.controls.refresh` 在每次重画时更新——把「按序列自动算出的 UP 数」这类结果放回参数位。
- 悬浮框按图表类型分三种写法：单条系列用 `tooltipFormatter`；区间带等需要整段自定义内容用
  `tooltipHtml(dataIndex)`（`regions`）；需要改表头（对数轴刻度是浮点）用 `tooltipHeader(axisValue)`（`curve`）。
- 成组的区间读数用 `P.tipBands(title, rows, bands, amount)`：色块对应图中区间，上下界各占一列右对齐
  （整串「85.3 – 93.3」文本对不齐）；普通两列读数仍用 `P.tip`。色块经 `UI.charts.color`
  按图内的暗色提亮幅度解析（区间带 0.2 为默认、参考线 0.18，见第 4 个参数）。
- `regions` 的 `labels` 支持 `size` 与 `bg: false`（不铺底色，供成片的参考读数使用）；
  参考线要落在纵轴刻度上时给 `yInterval`。标注系列用**透明色**隐藏符号——
  `itemStyle.opacity` 会被标注文字继承，把字一起抹掉。
- 对数轴的刻度会从 0 排起，落在轴外，`charts.js` 已统一丢弃（否则格式化后是「0e+0%」压住轴名）。
- 图表高度默认 460px；个人记录的参考读数多，用 `P.chart(host, 'player')`（600px）。
- **概率不足 0.01% 的分支不单独画柱**：横轴止于最后一个达标的分支，其余合并成最右一柱
  「> n」，高度为超出部分的总概率（分布本身照常返回全部概率，表格视图不受影响）。
  「金数分布」（角色池与武器池共用这张图）按 20 根上限截断：达标柱子多于 20 根时取概率之和
  最大的连续 18 项。两端恒有一根「< n」「> m」合并柱（不细分、按 `--text-dim` 上色），把区间外
  的全部质量——含不足 0.01% 的部分——计入，因此柱子之和恒为 100%；n = 0 或上方无正概率时省去。
  取柱规则、堆叠系列与悬浮框都在 `ui/panels.js`（`BAR_RULES` / `barSpec` / `stackBars` / `segTip`）。
- **堆叠柱**（`bars` 的 `stack`）：同一维度在各柱同色（按该维度在图中的出现区间取色带，
  而不是按柱内排名），不加圆角、改用 1px 底色描边分隔相邻段；legend 关掉（层数太多），
  读数交给 `tooltipHtml(dataIndex)`（堆叠柱的读数是跨系列排序 + 截断，单条系列表达不了）。
  只为概率 ≥ 0.0001% 的层建系列，更小的层画出来也只是细边。层数多、面积大时用
  `C.COLORS.stack`（恒亮彩虹：同明度只翻色相）——`spectral` 的中段近白，层数多时相邻档糊成一片。
  **堆叠柱关掉悬停提亮**（`bars` 传 `emphasis: false` → `emphasis.disabled`）：ECharts 默认把
  悬停的那根柱子的颜色提亮（HSV 明度 ×1.10），而这里颜色是数据（常驻数），提亮会破坏
  「同一值在各柱同色」，也让悬浮框的色块对不上柱子。
- **「金数分布」的悬浮框给条件概率**（`segTip` 的 `conditional` 模式）：读数不再是
  「n 个限定且 m 个常驻」，而是给定该柱限定数后各常驻数的占比（各行合计 100%）。
  行序照柱内堆叠自上而下（不按概率排序），仍只列概率最高的 10 项、其余合并成末尾一行；
  行首是图中的分段色块，并画横排小柱（宽度按框内最大条件概率归一，数值照读）。
  **悬浮框的颜色要经 `UI.charts.color` 解析**（与图内同一条暗色提亮规则），且留到悬浮时再算，
  否则暗色下与柱子对不上、切换主题后还会滞后一次。
- **柱顶标注**用 `overlays` 的折线 + `line: false`（只留标注，不画线与符号；符号颜色给
  `transparent`，标注文字用 `label.color` 单独指定），见「金数分布」。
- **图像导出在参数面板底部**（「复制图像」「下载图像」，作用于当前视图的图）。实现都在
  `ui/panels.js`（`chartActionButtons` / `copyChartImage` / `saveChartImage` / `toast`）：
  `getDataURL` 取 PNG、底色取 `--surface`，剪贴板不支持或被拒时退化为下载。
  **没有参数面板的页面**（模块无控件，如「算法性能」）把同两个按钮摆进 `.chartbar` 小工具条，
  放在每张图的上方。
  **不要在图里放浮动按钮**——那个角落会压住柱顶标注与右上角的图例。
