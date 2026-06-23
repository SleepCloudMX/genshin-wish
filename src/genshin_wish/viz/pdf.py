"""PDF curves for multi-gold pull distributions with expectation markers."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator
import matplotlib.patheffects as pe

from genshin_wish.viz._base import _ensure_dir


def plot_base_pdfs(pdfs: list[np.ndarray], save_path: Path) -> None:
    """Plot PDF curves for 1-gold through N-gold, each with
    an expectation marker and transparent fill.

    Parameters
    ----------
    pdfs : list[np.ndarray]
        List of PDF arrays.  pdfs[0] is ignored (should be [1.0]).
        pdfs[1] = 1-gold PDF, pdfs[2] = 2-gold PDF, etc.
        Each PDF is probability mass by pull count.
    save_path : Path
        Output file path (parent directories created automatically).
    """
    save_path = _ensure_dir(save_path)

    plt.figure(figsize=(12, 7))

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    for gold in range(1, len(pdfs)):
        x = np.arange(len(pdfs[gold]))
        y = pdfs[gold]
        color = colors[(gold - 1) % len(colors)]

        # 1. 绘制 PDF 曲线
        plt.plot(x[1:], y[1:], label=f"{gold} 金", color=color, linewidth=2, zorder=3)
        # 2. 填充透明背景
        plt.fill_between(x[1:], y[1:], color=color, alpha=0.1, zorder=2)
        # 3. 计算并标注期望值 E
        expected = np.sum(x * y)
        plt.axvline(x=expected, color=color, linestyle=':', alpha=0.6, linewidth=1, zorder=1)
        # 4. 找到峰值位置 (Mode)
        # mode_idx = np.argmax(y)
        # 在图上标注期望值文本
        plt.text(expected, plt.ylim()[1] * 0.02, f' E{gold}={expected:.1f}',
                 color=color, fontsize=9, fontweight='bold', rotation=0,
                 verticalalignment='bottom', bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

    # 图表装饰
    plt.title('出 n 个金所需抽数的概率密度函数', fontsize=14, pad=20)
    plt.xlabel('抽数', fontsize=12)
    plt.ylabel('概率', fontsize=12)

    # 设置网格
    plt.grid(True, which='major', linestyle='-', alpha=0.3)
    plt.grid(True, which='minor', linestyle=':', alpha=0.1)
    plt.minorticks_on()

    # 限制 X 轴范围，避免过长
    plt.xlim(0, len(pdfs[-1]) * 1.)
    plt.ylim(0, None)

    plt.legend(loc='upper right', frameon=True, shadow=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)  # 提高分辨率
    plt.close()


def plot_simple_pdf(pdf: np.ndarray, title: str, save_path: Path) -> None:
    """Plot a single PDF curve with expectation marker."""
    save_path = _ensure_dir(save_path)
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(pdf))
    expected = float(np.sum(x * pdf))
    x_hi = int(np.searchsorted(np.cumsum(pdf), 0.9999)) + 5

    ax.plot(x[:x_hi], pdf[:x_hi], color="#2171b5", lw=1.5)
    ax.fill_between(x[:x_hi], pdf[:x_hi], color="#2171b5", alpha=0.1)
    ax.axvline(expected, color="#ff7f0e", lw=1.2, ls="-", alpha=0.6)
    ymax = float(pdf[:x_hi].max()) * 1.1
    ax.text(expected + 1, ymax * 0.85, f"E={expected:.1f}",
            fontsize=9, color="#ff7f0e", alpha=0.8)

    ax.set_xlabel("pulls")
    ax.set_ylabel("probability density")
    ax.set_title(title)
    ax.set_xlim(0, x_hi)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=200)
    plt.close(fig)
