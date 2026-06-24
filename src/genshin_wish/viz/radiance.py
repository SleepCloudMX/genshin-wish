"""Capturing Radiance distribution visualisation."""

from pathlib import Path

from matplotlib import pyplot as plt

from ._base import _ensure_dir


def plot_radiance_bar(
    dist: dict[int, float],
    n_up: int,
    k_miss: int,
    save_path: str | Path,
    *,
    title: str | None = None,
) -> None:
    """Bar chart of radiance count distribution for a single n_up."""
    items = sorted(dist.items())
    xs = [k for k, _ in items]
    probs = [v for _, v in items]
    expected = sum(k * v for k, v in items)

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(xs, probs, width=0.7, color="#4292c6", edgecolor="white")
    for bar, prob in zip(bars, probs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{prob:.1%}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(xs)
    ax.set_xlabel("radiance count")
    ax.set_ylabel("probability")
    if title is not None:
        ax.set_title(title)
    else:
        ax.set_title(
            f"$n_\\mathrm{{up}}={n_up}$, k_miss={k_miss}  "
            f"($E[\\mathrm{{radiance}}]={expected:.2f}$)"
        )
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(probs) * 1.15)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)
