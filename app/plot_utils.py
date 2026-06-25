"""Thin wrappers around ``src/genshin_wish/viz/`` functions for Gradio.

Each wrapper creates a temp path under ``temp/gradio/``, calls the original
viz function (which saves to file and closes the figure), then returns the
path or text content for Gradio components.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np

from genshin_wish.viz._base import write_percentile_table
from genshin_wish.viz.cdf import plot_annotated_cdf
from genshin_wish.viz.nstd import (
    plot_nstd_bar,
    plot_nstd_heatmap_per_up,
    plot_nstd_pdf,
)
from genshin_wish.viz.pdf import plot_simple_pdf
from genshin_wish.viz.radiance import plot_radiance_bar

TEMP_DIR = Path("temp/gradio")


# ── helpers ──────────────────────────────────────────────

def _png(name: str) -> str:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return str(TEMP_DIR / f"{name}_{uuid.uuid4().hex[:8]}.png")


def _txt(name: str) -> str:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return str(TEMP_DIR / f"{name}_{uuid.uuid4().hex[:8]}.txt")


# ── public wrappers ──────────────────────────────────────

def plot_cdf(
    cdf,
    title: str,
    alphas=None,
    colors=None,
) -> str:
    """Return PNG path for an annotated CDF chart."""
    path = _png("cdf")
    plot_annotated_cdf(cdf, title, path, alphas=alphas, colors=colors)
    return path


def plot_pdf(pdf, title: str) -> str:
    """Return PNG path for a simple PDF chart with expectation marker."""
    path = _png("pdf")
    plot_simple_pdf(pdf, title, Path(path))
    return path


def plot_radiance(
    dist: dict[int, float],
    n_up: int,
    k_miss: int,
    *,
    title: str | None = None,
    fmt: str = ".2%",
    min_prob: float = 0.0001,
) -> str:
    """Return PNG path for a radiance count bar chart."""
    path = _png("radiance")
    plot_radiance_bar(dist, n_up, k_miss, path,
                      title=title, fmt=fmt, min_prob=min_prob)
    return path


def plot_nstd(
    nstd_dist: dict[int, float],
    n_up: int,
    k_miss: int,
) -> str:
    """Return PNG path for an n_std bar chart."""
    path = _png("nstd")
    plot_nstd_bar(nstd_dist, n_up, k_miss, path)
    return path


def plot_nstd_cond(
    dists: dict[int, object],  # UpDistribution (avoid import)
    n_up: int,
    k_miss: int,
    nstd_probs: dict[int, float] | None = None,
    min_prob: float = 0.01,
) -> str:
    """Return PNG path for a conditional pulls PDF overlay."""
    path = _png("nstd_pdf")
    plot_nstd_pdf(dists, n_up, k_miss, path,
                  nstd_probs=nstd_probs, min_prob=min_prob)
    return path


def plot_nstd_hm(
    nstd_by_k: dict[int, dict[int, float]],
    n_up: int,
    *,
    xlabel: str = "$n_\\mathrm{std}$",
    ylabel: str = "k_miss",
    fmt: str = ".1%",
    prune_threshold: float = 0.0001,
    title: str | None = None,
) -> str:
    """Return PNG path for a single-n_up heatmap (rows = k_miss)."""
    path = _png("nstd_hm")
    plot_nstd_heatmap_per_up(
        nstd_by_k, n_up, path,
        xlabel=xlabel, ylabel=ylabel, fmt=fmt,
        prune_threshold=prune_threshold, title=title,
    )
    return path


def make_pct_table(cdf, *, alphas=None) -> str:
    """Return a markdown percentile table for a single CDF."""
    if alphas is None:
        alphas = [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
    headers = " | ".join(f"**{int(a * 100)}%**" for a in alphas)
    vals = " | ".join(str(int(np.searchsorted(cdf, a))) for a in alphas)
    sep = " | ".join("---:" for _ in alphas)
    return f"| {headers} |\n| {sep} |\n| {vals} |\n\n> 表格数值：达到对应 α 所需的最少抽数"
