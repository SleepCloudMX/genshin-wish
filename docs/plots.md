<h1>图表系统</h1>

[TOC]

genshin-wish 使用 matplotlib 生成全部统计图表。所有绘图函数定义在 `src/genshin_wish/viz/` 下，统一由 `scripts/plot_all.py` 驱动输出。

## 一键生成

```bash
python scripts/plot_all.py
```

所有图表输出到 `output/` 目录。

## 输出目录结构

```
output/
├── character/
│   ├── cdf/
│   │   ├── n=1/{n=1-table.md, n=1-heatmap.png, n=1,miss=0..3.png}
│   │   ├── ...
│   │   └── n=7/{n=7-table.md, n=7-heatmap.png, n=7,miss=0..3.png}
│   ├── fan-3interval/   # miss0.png ~ stable.png (三区间扇形图)
│   ├── fan-5interval/   # miss0.png ~ stable.png (五区间扇形图)
│   ├── column/          # miss0.png ~ stable.png (渐变柱状图)
│   └── rolls2gold/
│       ├── multi-cdf/    # miss0.png ~ stable.png (多命座 CDF 线图)
│       ├── stack/        # miss0.png ~ stable.png (堆叠面积图)
│       └── staircase/    # miss0.png ~ stable.png (阶梯扇形图)
├── weapon/
│   ├── pdf.png          # 多金 PDF 对比
│   ├── cdf-gold1~4.png  # 1-4 金 CDF
│   └── target-one-up.png
└── multi-gold/
    ├── character-2gold~6gold.png
    └── weapon-2gold~6gold.png
```

## 样式配置

所有图表共享全局样式，通过 `setup_style()` 设置：

```python
from genshin_wish.viz._base import setup_style

setup_style()
```

设置内容：

| 配置项 | 值 | 说明 |
|--------|----|------|
| `font.sans-serif` | `SimHei` | 中文字体 |
| `axes.unicode_minus` | `False` | 负号正常显示 |
| `figure.dpi` | `150` | 屏幕显示 DPI |
| `savefig.dpi` | `300` | 保存图片 DPI |
| `savefig.bbox` | `tight` | 自动裁剪白边 |

`_base` 模块同时提供了所有图表共用的配色方案和辅助函数：

| 常量 | 说明 |
|------|------|
| `ALPHA_COLORS_6` | 6 级分位点标注色 |
| `INTERVAL_COLORS_3` | 3-interval 扇形分位带配色 |
| `INTERVAL_COLORS_5` | 5-interval 扇形分位带配色 |
| `DEFAULT_ALPHAS` | 默认分位点列表 `[0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]` |
| `MISS_LABELS` | 有序行标签（歪 0~3 次 + 稳态） |
| `write_percentile_table()` | 将 CDF map 写出为 Markdown 分位点表 |

---

## 图表类型

### 1. CDF 累积分布曲线 (`viz/cdf.py`)

**`plot_annotated_cdf`** — 单条 CDF 曲线 + 分位点标注线。

```python
def plot_annotated_cdf(
    cdf: np.ndarray,
    title: str,
    filename: str | Path,
    alphas: list[float] | None = None,
    colors: list[str] | None = None,
) -> None
```

| 参数 | 说明 |
|------|------|
| `cdf` | 1-D CDF 数组，索引 = 抽数 |
| `title` | 图表标题 |
| `filename` | 输出路径，父目录自动创建 |
| `alphas` | 分位阈值，默认 `[0.1, 0.3, 0.5, 0.7, 0.9, 0.99]` |
| `colors` | 各 alpha 标注颜色，默认 `ALPHA_COLORS_6` |

图表内容：
- 深灰色 CDF 曲线
- 各 alpha 处垂直虚线和水平虚线标注
- 每处标注 `α` 值和对应抽数 `x`
- X 轴底部有散点标记

**`plot_up_cdf_lines`** — 多命座 CDF 并排曲线，标注中位数。

```python
def plot_up_cdf_lines(
    dists: dict[int, np.ndarray],
    max_pulls: int,
    save_path: str | Path,
    title: str,
) -> None
```

| 参数 | 说明 |
|------|------|
| `dists` | `{n_up: cdf_array}` 字典，array 需已 padding 到至少 `max_pulls` 长度；key=0 忽略 |
| `max_pulls` | X 轴右边界（总抽数） |
| `save_path` | 输出路径 |
| `title` | 图表标题 |

图表内容：
- 每条曲线一种 viridis 颜色，图例标注 "至少 n UP"
- 各曲线中位数处画垂直虚线并标注抽数
- 90% 概率线（红色点划线）

---

### 2. 热力图 (`viz/heatmap.py`)

**`plot_percentile_heatmap`** — 行 = 歪次数状态，列 = 分位点，值 = 所需抽数。

```python
def plot_percentile_heatmap(
    cdf_map: dict[str, np.ndarray],
    title: str,
    filename: str | Path,
    alphas: list[float] | None = None,
) -> None
```

| 参数 | 说明 |
|------|------|
| `cdf_map` | key 为 `"miss=0"` ~ `"miss=3"` 和 `"stable"`，value 为 CDF 数组 |
| `title` | 图表标题 |
| `filename` | 输出路径 |
| `alphas` | 默认 `DEFAULT_ALPHAS` |

图表内容：
- Blues 色阶热力图
- 单元格内标注抽数（浅色背景白字，深色背景深色字）
- 右侧 colorbar 标注 "所需总抽数"
- 底部附概率模型说明注释

---

### 3. 分位点表格 (`viz/_base.py`)

**`write_percentile_table`** — 将热力图数据写为 Markdown 表格。

```python
def write_percentile_table(
    cdf_map: dict[str, np.ndarray],
    title: str,
    filename: str | Path,
    alphas: list[float] | None = None,
) -> None
```

输出 `.md` 文件，列为分位点百分比，行为 `MISS_LABELS` 中的状态行。文件末尾附说明 "单元格数值表示达到对应 α 所需抽数 (CDF 分位点)。"

---

### 4. 扇形图 (`viz/fan.py`)

**`plot_luck_fan`** — 展示 "单位 UP 消耗抽数" 的分布带。

```python
def plot_luck_fan(
    pdf_func,
    max_n_up: int,
    save_path: str | Path,
    *,
    interval_set: int = 5,
    title: str | None = None,
) -> None
```

| 参数 | 说明 |
|------|------|
| `pdf_func` | `(n_up: int) -> np.ndarray`，返回获得 n_up 个 UP 的 PDF（索引 = 总抽数） |
| `max_n_up` | X 轴 UP 数量上限 (1 … max_n_up) |
| `save_path` | 输出 PNG 路径 |
| `interval_set` | 分位带数量：`3` 或 `5`（默认 5） |
| `title` | 图表标题，为 None 时自动生成 |

**3-interval 模式** 分位带：30%-70%（蓝色）、10%-90%（橙色）、1%-99%（红色）。

**5-interval 模式** 分位带：40%-60%（深蓝）、30%-70%（蓝）、20%-80%（浅蓝）、10%-90%（橙）、1%-99%（红）。

图表内容：
- Y 轴 = 总抽数 / UP 数（单位平均成本）
- X 轴 = 目标命座（0 命 ~ 6 命）
- 每个命座处标注各分位点数值和期望值（Avg）
- 黑色实线 = 单位平均期望，黑色标记点
- 红色参考线 = 160 抽/UP（极限大保底参考）

---

### 5. 渐变柱状图 (`viz/column.py`)

**`plot_success_column_chart`** — 每个命座一根柱子，颜色由 CDF 映射。

```python
def plot_success_column_chart(
    pdf_func: Callable[[int], np.ndarray],
    max_n_up: int,
    save_path: Path,
    title: str,
) -> None
```

| 参数 | 说明 |
|------|------|
| `pdf_func` | `(n_up: int) -> np.ndarray` |
| `max_n_up` | 柱子数量（UP 数上限） |
| `save_path` | 输出路径 |
| `title` | 标题（如 "已连续歪 0 次"） |

图表内容：
- 每根柱子由 YlGnBu 色阶的 2-抽步长矩形段组成，颜色深浅对应 CDF 值（浅 = 低概率区，深 = 高概率区）
- 柱子顶部标注期望抽数
- 柱内标注各分位点横线及数值（10%、30%、50%、70%、90%、99%），自动防重叠
- 右侧 colorbar 标注 "达成概率 (CDF)"
- 标题格式：`【{title}】各命座抽数分位点分布图`

---

### 6. 堆叠面积图 (`viz/stack.py`)

**`plot_stacked_up_probabilities`** — 展示 "持有 k 个 UP" 的概率随抽数变化。

```python
def plot_stacked_up_probabilities(
    dists: dict[int, np.ndarray],
    max_pulls: int,
    save_path: Path,
    title: str,
) -> None
```

| 参数 | 说明 |
|------|------|
| `dists` | `{n_up: cdf_array}`，其中 `dists[n][i] = P(>= n UP | i pulls)`。`dists[0]` 应为全 1 |
| `max_pulls` | X 轴最大抽数 |
| `save_path` | 输出路径 |
| `title` | 图表标题 |

图表内容：
- Spectral_r 色阶堆叠面积
- `dists[n] - dists[n+1]` 转换为 "恰好持有 n 个 UP" 的概率
- 最顶层 = `P(>= max_n_up UP)`
- X 轴主刻度 100、次刻度 20；Y 轴主刻度 0.1、次刻度 0.02

---

### 7. 阶梯扇形图 (`viz/staircase.py`)

**`plot_staircase_luck_fan`** — 以抽数为 X 轴，UP 数量为 Y 轴的概率分布。

```python
def plot_staircase_luck_fan(
    dists: dict[int, np.ndarray],
    max_pulls: int,
    save_path: Path,
    *,
    title: str = "",
    calc_n_limit: int = 15,
    user_data: list | None = None,
) -> None
```

| 参数 | 说明 |
|------|------|
| `dists` | `{n_up: cdf_array}`，需覆盖 n = 0 .. calc_n_limit |
| `max_pulls` | X 轴最大抽数 |
| `save_path` | 输出路径 |
| `title` | 图表标题 |
| `calc_n_limit` | 期望值计算的上限 n_up（默认 15） |
| `user_data` | `[(pulls, up_count), ...]`，标注用户实际记录点 |

图表内容：
- 5 层蓝系分位带：40%-60%、30%-70%、20%-80%、10%-90%、1%-99%
- 黑色实线 = 期望 UP 数曲线
- 黑色虚线 = 中位数 step 线
- 青绿色竖线 = 期望达到整数的抽数切面（标注抽数）
- 支持标注用户实际记录（深红 X 标记 + 白底黑字）

---

### 8. 长期欧非演变 (`viz/long_term.py`)

**`plot_long_term_luck`** — N 次获取 UP 的长期趋势，分位带随 N 增大逐渐收敛于期望线。

```python
def plot_long_term_luck(
    solver_func,
    N: int,
    save_path: str | Path,
    *,
    interval_set: int = 5,
    title: str | None = None,
) -> None
```

| 参数 | 说明 |
|------|------|
| `solver_func` | `(N, alphas) -> dict[float, list[(low, high)]]`，返回各 alpha 在 1..N 步的累积抽数上下界 |
| `N` | 总 UP 获取次数 |
| `save_path` | 输出路径 |
| `interval_set` | `3` 或 `5`（默认 5） |
| `title` | 图表标题 |

与 `plot_luck_fan` 的区别：
- `plot_luck_fan` 展示不同命座（1~7 次获取）的单位平均成本
- `plot_long_term_luck` 展示长期（N 可达数百次获取）的趋势收敛，Y 轴 = 单位平均消耗

图表内容：
- 同扇形图的分位带体系（3 或 5 层）
- 黑色虚线 = 理论均值
- 采样点（10, 20, 50, 100...）标注各分位点数值
- 灰色竖线辅助定位

---

### 9. 十连多金 (`viz/multi_gold.py`)

**`plot_multi_gold`** — 十连至少出 k 金的累计概率随十连次数变化。

```python
def plot_multi_gold(p: float, title: str, save_path: Path) -> None
```

| 参数 | 说明 |
|------|------|
| `p` | 单次十连出多金事件的概率 |
| `title` | 图表标题 |
| `save_path` | 输出路径 |

图表内容：
- 金色曲线 `y = 1 - (1-p)^x` + 透明填充
- 菱形标记期望值（`1/p`）
- 10%~70% 分位点随线标注；90%、99% 分位点在右下角固定标注
- seaborn-v0_8-muted 风格
- 无顶部和右侧边框

---

### 10. 武器/多金 PDF 对比 (`viz/pdf.py`)

**`plot_base_pdfs`** — 1~4 金的 PDF 曲线对比，标注期望值。

```python
def plot_base_pdfs(pdfs: list[np.ndarray], save_path: Path) -> None
```

| 参数 | 说明 |
|------|------|
| `pdfs` | PDF 数组列表，`pdfs[0]` 忽略（为 `[1.0]`），`pdfs[1]` = 1 金 PDF，`pdfs[2]` = 2 金 PDF，以此类推 |
| `save_path` | 输出路径 |

图表内容：
- 每条 PDF 曲线不同颜色 + 透明填充
- 各曲线期望值处竖虚线标注 `E{金数}={期望抽数}`
- 网格含主次刻度

---

## 自定义绘图

所有 viz 函数的 `save_path` 参数接受 `Path | str`，父目录自动创建。

```python
from genshin_wish.viz._base import setup_style
from genshin_wish.viz.cdf import plot_annotated_cdf

setup_style()

# 给任意分布的 CDF 画图
plot_annotated_cdf(dist.cdf, "标题", "output/custom.png")
```

可复用的公开 API 汇总：

| 模块 | 函数 | 用途 |
|------|------|------|
| `viz.cdf` | `plot_annotated_cdf` | 单条 CDF + 分位标注 |
| `viz.cdf` | `plot_up_cdf_lines` | 多 CDF 并排对比 |
| `viz.heatmap` | `plot_percentile_heatmap` | 分位点热力图 |
| `viz._base` | `write_percentile_table` | 分位点 Markdown 表格 |
| `viz.fan` | `plot_luck_fan` | 命座扇形分布图 |
| `viz.column` | `plot_success_column_chart` | 渐变柱状图 |
| `viz.stack` | `plot_stacked_up_probabilities` | 堆叠面积图 |
| `viz.staircase` | `plot_staircase_luck_fan` | 阶梯扇形图 |
| `viz.long_term` | `plot_long_term_luck` | 长期欧非演变 |
| `viz.multi_gold` | `plot_multi_gold` | 十连多金概率 |
| `viz.pdf` | `plot_base_pdfs` | 多金 PDF 对比 |
