"""Standard (Wanderlust) banner: pure gold-count probability.

No rate-up mechanism — every 5-star is just a 5-star.
Uses the same gold probability as the character event banner.
"""

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from ._constants import CHARACTER_POOL, CLT_THRESHOLD
from ._gold import get_gold_pdfs
from .character import UpDistribution


@dataclass
class StandardState:
    """State of the standard banner before pulling.

    Attributes:
        pity: Pulls since last 5-star (0..89).
    """

    pity: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.pity < CHARACTER_POOL.hard_pity:
            raise ValueError(
                f"pity must be 0..{CHARACTER_POOL.hard_pity - 1}, got {self.pity}"
            )


def standard_distribution(state: StandardState, n_gold: int) -> UpDistribution:
    """Distribution of pulls for *n_gold* 5-stars on the standard banner.

    n_gold ≤ CLT_THRESHOLD: exact convolution of multi-gold PDFs.
    n_gold > CLT_THRESHOLD: CLT approximation for remaining golds,
    with the first gold handled exactly (to account for pity).
    """
    if n_gold < 0:
        raise ValueError(f"n_gold must be >= 0, got {n_gold}")
    if n_gold == 0:
        return UpDistribution(pdf=np.array([1.0]), cdf=np.array([1.0]))

    if n_gold > CLT_THRESHOLD:
        return _standard_clt(state, n_gold)
    return _standard_exact(state, n_gold)


def _standard_exact(state: StandardState, n_gold: int) -> UpDistribution:
    """Exact distribution via multi-gold PDF convolution."""
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=n_gold)

    # Shift first gold by current pity
    shifted_first = np.insert(
        pdfs[1][state.pity + 1:] / pdfs[1][state.pity + 1:].sum(),
        0, 0,
    )

    if n_gold == 1:
        cdf = np.cumsum(shifted_first)
        return UpDistribution(pdf=shifted_first, cdf=cdf)

    # Convolve remaining golds into the first gold
    result = shifted_first.copy()
    for _ in range(n_gold - 1):
        result = np.convolve(result, pdfs[1])

    cdf = np.cumsum(result)
    return UpDistribution(pdf=result, cdf=cdf)


def _standard_clt(state: StandardState, n_gold: int) -> UpDistribution:
    """CLT approximation: exact first gold + normal for the rest."""
    pdfs = get_gold_pdfs(CHARACTER_POOL)

    # First gold: exact (handles pity precisely)
    shifted_first = np.insert(
        pdfs[1][state.pity + 1:] / pdfs[1][state.pity + 1:].sum(),
        0, 0,
    )

    if n_gold == 1:
        cdf = np.cumsum(shifted_first)
        return UpDistribution(pdf=shifted_first, cdf=cdf, method="clt")

    # Single gold moments for CLT
    vals = np.arange(len(pdfs[1]), dtype=np.float64)
    m1 = float(np.sum(vals * pdfs[1]))
    m2 = float(np.sum(vals**2 * pdfs[1]))
    var1 = m2 - m1**2

    n_remaining = n_gold - 1
    mu_r = n_remaining * m1
    std_r = np.sqrt(n_remaining * var1)

    # Discretized normal with continuity correction (±6σ coverage)
    lo = max(0, int(mu_r - 6 * std_r))
    hi = int(mu_r + 6 * std_r)
    # For each integer k in [lo, hi]: P(k) ≈ Φ(k+0.5) - Φ(k-0.5)
    edges = np.arange(lo - 0.5, hi + 1.0, dtype=np.float64)
    pdf_raw = np.diff(norm.cdf(edges, loc=mu_r, scale=std_r))
    # Position correctly: pdf_raw[i] corresponds to pull count (lo + i)
    clt_pdf = np.zeros(hi + 1, dtype=np.float64)
    clt_pdf[lo : hi + 1] = pdf_raw

    # Convolve exact first gold with CLT remaining
    result = np.convolve(shifted_first, clt_pdf)
    cdf = np.cumsum(result)
    return UpDistribution(pdf=result, cdf=cdf, method="clt")
