"""Shared visualization utilities: style setup, colors, common helpers."""

from pathlib import Path

import numpy as np

# Must set before importing pyplot, otherwise font init caches wrong minus glyph.
import matplotlib
matplotlib.rcParams['axes.unicode_minus'] = False

from matplotlib import pyplot as plt


def setup_style() -> None:
    """Apply global matplotlib style for consistent chart appearance."""
    plt.rcParams.update({
        'font.sans-serif': ['SimHei'],
        'axes.unicode_minus': False,
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
    })


# Colors for 6-level percentile annotations
ALPHA_COLORS_6: list[str] = [
    '#2ca02c', '#1f77b4', '#ff7f0e', '#9467bd', '#d62728', '#4b0082',
]

# Colors for 5-interval fan charts (inner to outer)
INTERVAL_COLORS_5: list[dict] = [
    {'a': 0.40, 'color': '#084594'},
    {'a': 0.30, 'color': '#2171b5'},
    {'a': 0.20, 'color': '#4292c6'},
    {'a': 0.10, 'color': '#f16913'},
    {'a': 0.01, 'color': '#cb181d'},
]

# Colors for 3-interval fan charts
INTERVAL_COLORS_3: list[dict] = [
    {'a': 0.30, 'color': '#1f77b4'},
    {'a': 0.10, 'color': '#ff7f0e'},
    {'a': 0.01, 'color': '#d62728'},
]

# Standard alpha list for percentile tables / heatmaps
DEFAULT_ALPHAS: list[float] = [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]

# Ordered row labels for k_miss state
MISS_LABELS: list[tuple[str, str]] = [
    ('已连歪 0 次', 'miss=0'),
    ('已连歪 1 次', 'miss=1'),
    ('已连歪 2 次', 'miss=2'),
    ('已连歪 3 次', 'miss=3'),
    ('稳态', 'stable'),
]


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_percentile_table(
    cdf_map: dict[str, np.ndarray],
    title: str,
    filename: str | Path,
    alphas: list[float] | None = None,
) -> None:
    """Write a Markdown table of percentile values from a CDF map.

    Columns: alpha percentiles.  Rows: miss/stable states.
    """
    if alphas is None:
        alphas = [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]

    alpha_headers = [f"{int(a * 100)}%" for a in alphas]

    lines = [f'# {title}', '']
    lines.append('| 状态 | ' + ' | '.join(alpha_headers) + ' |')
    lines.append('| :--: | ' + ' | '.join(':--:' for _ in alpha_headers) + ' |')

    for row_name, key in MISS_LABELS:
        cdf = cdf_map.get(key)
        if cdf is None:
            continue
        q_vals = [str(int(np.searchsorted(cdf, a))) for a in alphas]
        lines.append('| ' + row_name + ' | ' + ' | '.join(q_vals) + ' |')

    lines.append('')
    lines.append('> 单元格数值表示达到对应 α 所需抽数 (CDF 分位点)。')
    Path(filename).write_text('\n'.join(lines), encoding='utf-8')
