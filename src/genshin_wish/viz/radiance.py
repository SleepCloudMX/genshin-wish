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
    fmt: str = ".2%",
    min_prob: float = 0.0001,
) -> None:
    """Chart of radiance count distribution for a single n_up.

    Bar chart overlaid with KDE when > 10 bins.  Right-tail bins with
    probability < *min_prob* are trimmed.
    """
    all_items = sorted(dist.items())

    # Trim right tail below min_prob
    trim = len(all_items)
    while trim > 0 and all_items[trim - 1][1] < min_prob:
        trim -= 1
    items = all_items[:trim]

    xs = [k for k, _ in items]
    probs = [v for _, v in items]
    expected = sum(k * v for k, v in all_items)

    use_kde = len(items) > 10
    fig_w = max(8, len(items) * 0.45) if not use_kde else 10
    fig, ax = plt.subplots(figsize=(fig_w, 4))

    bars = ax.bar(xs, probs, width=0.7, color="#deebf7", edgecolor="#4292c6",
                  linewidth=0.5, zorder=1)

    if use_kde:
        # KDE overlay on weighted samples
        weights = np.array(probs, dtype=float)
        weights /= weights.sum()
        rng = np.random.default_rng(42)
        resampled = rng.choice(np.array(xs, dtype=float), size=5000, p=weights)
        kde = gaussian_kde(resampled)
        x_kde = np.linspace(xs[0], xs[-1], 200)
        y_kde = kde(x_kde)
        # Scale KDE to match bar heights
        y_kde *= 1.0 / y_kde.max() * max(probs) if max(probs) > 0 else 1.0
        ax.plot(x_kde, y_kde, color="#2171b5", lw=1.5, zorder=2)

    for bar, prob in zip(bars, probs):
        if prob >= min_prob:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.005,
                    f"{prob:{fmt}}", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(xs)
    if len(xs) > 20:
        step = max(1, len(xs) // 15)
        ax.set_xticks(xs[::step])
    ax.set_xlabel("capture radiance")
    ax.set_ylabel("probability")
    if title is not None:
        ax.set_title(title)
    else:
        ax.set_title(
            f"$n_\\mathrm{{up}}={n_up}$, k_miss={k_miss}  "
            f"($E[\\mathrm{{radiance}}]={expected:.2f}$)"
        )
    ax.grid(axis="y", alpha=0.3)
    if len(probs) > 0:
        ax.set_ylim(0, max(probs) * 1.15)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)
