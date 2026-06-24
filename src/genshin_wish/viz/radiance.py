"""Capturing Radiance distribution visualisation."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from scipy.stats import gaussian_kde

from ._base import _ensure_dir


def plot_radiance_bar(
    dist: dict[int, float],
    n_up: int,
    k_miss: int,
    save_path: str | Path,
    *,
    title: str | None = None,
    fmt: str = ".1%",
    min_prob: float = 0.001,
) -> None:
    """Chart of radiance count distribution for a single n_up.

    Bar chart when ≤ 10 bins; KDE-smoothed line otherwise.  Bins with
    probability < *min_prob* are omitted.
    """
    all_items = sorted(dist.items())
    # Filter below threshold
    items = [(k, v) for k, v in all_items if v >= min_prob]
    xs = [k for k, _ in items]
    probs = [v for _, v in items]
    expected = sum(k * v for k, v in all_items)

    fig, ax = plt.subplots(figsize=(8, 4))

    if len(items) <= 10:
        bars = ax.bar(xs, probs, width=0.7, color="#4292c6", edgecolor="white")
        for bar, prob in zip(bars, probs):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.005,
                    f"{prob:{fmt}}", ha="center", va="bottom", fontsize=9)
        ax.set_xticks(xs)
    else:
        # KDE on weighted samples
        weights = np.array([v for _, v in all_items])
        samples = np.array([k for k, _ in all_items], dtype=float)
        weights /= weights.sum()
        # Resample to get enough points for KDE
        rng = np.random.default_rng(42)
        n_samples = 5000
        resampled = rng.choice(samples, size=n_samples, p=weights)
        kde = gaussian_kde(resampled)
        x_kde = np.linspace(samples[0], samples[-1], 200)
        y_kde = kde(x_kde)
        ax.plot(x_kde, y_kde, color="#4292c6", lw=1.5)
        ax.fill_between(x_kde, y_kde, alpha=0.15, color="#4292c6")

    ax.set_xlabel("radiance count")
    ax.set_ylabel("probability density")
    if title is not None:
        ax.set_title(title)
    else:
        ax.set_title(
            f"$n_\\mathrm{{up}}={n_up}$, k_miss={k_miss}  "
            f"($E[\\mathrm{{radiance}}]={expected:.2f}$)"
        )
    ax.grid(alpha=0.3)
    if len(items) <= 10 and len(probs) > 0:
        ax.set_ylim(0, max(probs) * 1.15)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)
