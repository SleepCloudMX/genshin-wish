"""n_std distribution and conditional pulls visualisation."""

from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from ._base import _ensure_dir

# n_std curve colours — blue (few) to red (many)
_NSTD_CMAP = plt.colormaps["coolwarm"]


def plot_nstd_heatmap(
    nstd_by_up: dict[int, dict[int, float]],
    k_miss: int,
    save_path: str | Path,
) -> None:
    """Global heatmap: rows = n_up, cols = n_std, colour = probability."""
    n_ups = sorted(nstd_by_up.keys())
    max_nstd = max(max(d.keys()) for d in nstd_by_up.values())

    data = np.zeros((len(n_ups), max_nstd + 1))
    for i, nu in enumerate(n_ups):
        for ns, prob in nstd_by_up[nu].items():
            data[i, ns] = prob

    fig, ax = plt.subplots(figsize=(10, 6))
    cmap = plt.colormaps["Blues"]
    cax = ax.imshow(data, cmap=cmap, aspect="auto", origin="lower")

    vmax = data.max()
    for i, nu in enumerate(n_ups):
        for j in range(max_nstd + 1):
            val = data[i, j]
            if val < 0.01:
                continue
            norm_v = val / (vmax + 1e-9)
            colour = "white" if norm_v > 0.5 else "#2b2b2b"
            ax.text(j, i, f"{val:.1%}", ha="center", va="center",
                    fontsize=8, color=colour)

    ax.set_xticks(range(max_nstd + 1))
    ax.set_yticks(range(len(n_ups)))
    ax.set_xticklabels([str(j) for j in range(max_nstd + 1)])
    ax.set_yticklabels([str(nu) for nu in n_ups])
    ax.set_xlabel("$n_\\mathrm{std}$")
    ax.set_ylabel("$n_\\mathrm{up}$")
    ax.set_title(f"$P(n_\\mathrm{{std}} \\mid n_\\mathrm{{up}})$  (k_miss={k_miss})")
    fig.colorbar(cax, ax=ax, label="probability")
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)


def plot_nstd_heatmap_per_up(
    nstd_by_k: dict[int, dict[int, float]],
    n_up: int,
    save_path: str | Path,
) -> None:
    """Single-n_up heatmap: rows = k_miss, cols = n_std, colour = probability."""
    k_vals = sorted(nstd_by_k.keys())
    if not k_vals:
        return
    max_nstd = max(max(d.keys()) for d in nstd_by_k.values())

    data = np.zeros((len(k_vals), max_nstd + 1))
    for i, k in enumerate(k_vals):
        for ns, prob in nstd_by_k[k].items():
            data[i, ns] = prob

    fig, ax = plt.subplots(figsize=(8, 3))
    cmap = plt.colormaps["Blues"]
    cax = ax.imshow(data, cmap=cmap, aspect="auto", origin="lower")

    vmax = data.max()
    for i in range(len(k_vals)):
        for j in range(max_nstd + 1):
            val = data[i, j]
            if val < 0.01:
                continue
            norm_v = val / (vmax + 1e-9)
            colour = "white" if norm_v > 0.5 else "#2b2b2b"
            ax.text(j, i, f"{val:.1%}", ha="center", va="center",
                    fontsize=9, color=colour)

    ax.set_xticks(range(max_nstd + 1))
    ax.set_yticks(range(len(k_vals)))
    ax.set_xticklabels([str(j) for j in range(max_nstd + 1)])
    ax.set_yticklabels([f"k={k}" for k in k_vals])
    ax.set_xlabel("$n_\\mathrm{std}$")
    ax.set_ylabel("k_miss")
    ax.set_title(f"$P(n_\\mathrm{{std}} \\mid n_\\mathrm{{up}}={n_up})$")
    fig.colorbar(cax, ax=ax, label="probability")
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)


def plot_nstd_bar(
    nstd_dist: dict[int, float],
    n_up: int,
    k_miss: int,
    save_path: str | Path,
) -> None:
    """Bar chart of n_std marginal distribution for a single n_up."""
    items = sorted(nstd_dist.items())
    xs = [k for k, _ in items]
    probs = [v for _, v in items]
    expected = sum(k * v for k, v in items)

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(xs, probs, width=0.7, color="#4292c6", edgecolor="white")
    for bar, prob in zip(bars, probs):
        if prob >= 0.03:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{prob:.1%}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(xs)
    ax.set_xlabel("$n_\\mathrm{std}$")
    ax.set_ylabel("probability")
    ax.set_title(
        f"$n_\\mathrm{{up}}={n_up}$, k_miss={k_miss}  "
        f"($E[n_\\mathrm{{std}}]={expected:.2f}$)"
    )
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(probs) * 1.15)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)


def plot_nstd_pdf(
    dists: dict[int, "UpDistribution"],  # noqa: F821
    n_up: int,
    k_miss: int,
    save_path: str | Path,
    min_prob: float = 0.01,
) -> None:
    """Multi-curve PDF overlay: one curve per n_std, coloured."""
    fig, ax = plt.subplots(figsize=(10, 5))

    total_p = sum(d.pdf.sum() for d in dists.values())
    items = sorted(dists.items())

    for i, (ns, dist) in enumerate(items):
        prob = dist.pdf.sum() / total_p if total_p > 0 else 0
        if prob < min_prob:
            continue
        colour = _NSTD_CMAP(i / max(len(items) - 1, 1))
        x_hi = int(np.searchsorted(dist.cdf, 0.9999))
        x = np.arange(min(x_hi + 10, len(dist.pdf)))
        ax.plot(x, dist.pdf[x], color=colour, lw=1.2,
                label=f"$n_\\mathrm{{std}}$={ns} ({prob:.1%})")

    ax.set_xlabel("pulls")
    ax.set_ylabel("probability density")
    ax.set_title(f"Conditional pulls PDF  ($n_\\mathrm{{up}}={n_up}$, k_miss={k_miss})")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    _auto_xlim(ax, [d.pdf for d in dists.values()])
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)


def plot_nstd_cdf(
    dist: "UpDistribution",  # noqa: F821
    n_up: int,
    n_std: int,
    k_miss: int,
    save_path: str | Path,
) -> None:
    """Annotated CDF for a single (n_up, n_std) combination."""
    fig, ax = plt.subplots(figsize=(10, 5))

    x_hi = int(np.searchsorted(dist.cdf, 0.9999))
    x = np.arange(min(x_hi + 10, len(dist.cdf)))
    ax.plot(x, dist.cdf[x], color="#2171b5", lw=1.5)

    for alpha in [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]:
        qi = int(np.searchsorted(dist.cdf, alpha))
        ax.axvline(qi, color="#d62728", alpha=0.25, lw=0.8, ls="--")
        ax.text(qi + 1, alpha, f"  P{int(alpha*100)}={qi}", fontsize=7,
                va="bottom" if alpha < 0.8 else "top", alpha=0.7)

    expected = float(sum(i * p for i, p in enumerate(dist.pdf)))
    ax.axvline(expected, color="#ff7f0e", lw=1.2, ls="-", alpha=0.6)
    ax.text(expected + 1, 0.62, f"E={expected:.1f}", fontsize=8,
            color="#ff7f0e", alpha=0.8)

    ax.set_xlabel("pulls")
    ax.set_ylabel("CDF")
    ax.set_title(
        f"Conditional pulls CDF  "
        f"($n_\\mathrm{{up}}={n_up}$, $n_\\mathrm{{std}}={n_std}$, k_miss={k_miss})"
    )
    ax.grid(alpha=0.3)
    ax.set_xlim(0, x_hi + 5)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=200)
    plt.close(fig)


def _auto_xlim(ax, pdfs: list[np.ndarray]) -> None:
    """Set x-axis to cover 99.99% of probability mass across all PDFs."""
    hi = 0
    for pdf in pdfs:
        cdf = np.cumsum(pdf)
        hi = max(hi, int(np.searchsorted(cdf, 0.9999)) + 5)
    if hi > 0:
        ax.set_xlim(0, hi)
