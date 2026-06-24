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
    fmt: str = ".2%",
    min_prob: float = 0.0001,
) -> None:
    """Bar chart of radiance count distribution for a single n_up.

    Right-tail bins with probability < *min_prob* are trimmed.
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

    fig_w = max(8, len(items) * 0.45)
    fig, ax = plt.subplots(figsize=(fig_w, 4))

    bars = ax.bar(xs, probs, width=0.7, color="#deebf7", edgecolor="#4292c6",
                  linewidth=0.5)

    fontsize = 9 if len(items) <= 15 else (8 if len(items) <= 25 else 7)
    for bar, prob in zip(bars, probs):
        if prob >= min_prob:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.005,
                    f"{prob:{fmt}}", ha="center", va="bottom",
                    fontsize=fontsize)

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
