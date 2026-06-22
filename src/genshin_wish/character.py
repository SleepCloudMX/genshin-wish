"""Character event banner: UP distribution for n copies of the rate-up 5-star."""

import warnings
from collections import Counter
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from ._constants import CHARACTER_POOL, STABLE_P, CLT_THRESHOLD, CAPTURE_RADIANCE_WIN_RATE
from ._capture_radiance import guarantee_seq
from ._gold import get_gold_pdfs
from .long_term import _solve_exact


@dataclass
class CharacterState:
    """State of the character event banner before pulling.

    Attributes:
        guaranteed: Whether the next 5-star is guaranteed to be the rate-up.
        pity:       Number of pulls since last 5-star (0..89).
        consecutive_loss: Number of consecutive 50/50 losses (0..3), drives Capture Radiance.
    """

    guaranteed: bool = False
    pity: int = 0
    consecutive_loss: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.pity < CHARACTER_POOL.hard_pity:
            raise ValueError(f"pity must be 0..{CHARACTER_POOL.hard_pity - 1}, got {self.pity}")
        if not 0 <= self.consecutive_loss <= 3:
            raise ValueError(f"consecutive_loss must be 0..3, got {self.consecutive_loss}")


@dataclass
class UpDistribution:
    """Distribution of pulls needed to obtain *n_up* rate-up characters.

    Attributes:
        pdf: pdf[i] = probability that exactly *i* pulls are needed.
        cdf: cdf[i] = probability that ≤ *i* pulls are needed.
        method: "exact" or "clt".
    """

    pdf: np.ndarray
    cdf: np.ndarray
    method: str = "exact"

    @property
    def expected(self) -> float:
        return float(np.sum(np.arange(len(self.pdf)) * self.pdf))

    def quantile(self, q: float) -> int:
        """Pull count at which CDF first reaches or exceeds *q*."""
        return int(np.searchsorted(self.cdf, q))

    def luck(self, pulls: int) -> float:
        """Percentile: what fraction of players need ≤ *pulls*."""
        if pulls >= len(self.cdf):
            return 1.0
        return float(self.cdf[max(0, pulls)])

    def probability(self, pulls: int) -> float:
        """Probability of succeeding within *pulls*."""
        return self.luck(pulls)


def up_distribution(
    state: CharacterState, n_up: int, method: str = "auto"
) -> UpDistribution:
    """Distribution of pulls to obtain *n_up* rate-up characters from *state*.

    Decomposes the total pulls into three independent parts:
    1. The *first gold* — shifted by current pity (state.pity).
    2. The *uncertain golds* from n_up - state.guaranteed win/loss sequences.
    3. The *guaranteed gold* (if state.guaranteed) — one extra gold with no shift.

    *method* selects the algorithm for part 2:

    ========== ====================================================
    ``"auto"`` n_uncertain ≤ 10 → dp-path, ≤ 500 → dp-state, > 500 → clt + warning
    ``"dp-path"``  enumerate all win/loss sequences (≤ 20 only)
    ``"dp-state"`` iterative state-space convolution
    ``"clt"``     CLT normal approximation
    ========== ====================================================
    """
    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")

    n_uncertain = n_up - state.guaranteed

    # Resolve method
    if method == "auto":
        if n_uncertain <= 10:
            eff_method = "dp-path"
        elif n_uncertain <= 500:
            eff_method = "dp-state"
        else:
            eff_method = "clt"
            warnings.warn(
                f"n_up={n_up} exceeds 500, switching to CLT approximation. "
                f"Use method='dp-state' to force exact computation."
            )
    elif method == "dp-path":
        if n_uncertain > 20:
            raise ValueError(
                f"dp-path limited to n_uncertain ≤ 20, got {n_uncertain}. "
                f"Use method='dp-state' or 'clt'."
            )
        eff_method = "dp-path"
    elif method in ("dp-state", "clt"):
        eff_method = method
    else:
        raise ValueError(
            f"Unknown method: {method!r}. "
            f"Valid: 'auto', 'dp-path', 'dp-state', 'clt'."
        )

    # Gold PDFs
    min_gold_needed = 3 if n_uncertain == 0 else n_uncertain * 2 + 3
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=min_gold_needed)
    p_gold = pdfs[1]

    if n_uncertain == 0:
        shifted = np.insert(
            p_gold[state.pity + 1:] / p_gold[state.pity + 1:].sum(), 0, 0,
        )
        if not state.guaranteed and n_up == 0:
            return UpDistribution(pdf=np.array([1.0]), cdf=np.array([1.0]))
        cdf = np.cumsum(shifted)
        return UpDistribution(pdf=shifted, cdf=cdf)

    # --- uncertain part ---
    p_gold2 = np.convolve(p_gold, p_gold)

    if eff_method == "dp-path":
        result_pdf = _uncertain_pdf_path(state.consecutive_loss, n_uncertain, pdfs)
        method_label = "exact"
    elif eff_method == "dp-state":
        if state.pity > 0:
            # dp-state result is complete; can't easily replace first gold.
            # Fall back to dp-path for accurate pity handling.
            result_pdf = _uncertain_pdf_path(state.consecutive_loss, n_uncertain, pdfs)
            method_label = "exact"
        else:
            p_up = list(CAPTURE_RADIANCE_WIN_RATE)
            dp_result = _solve_exact(n_uncertain, p_up, p_gold, p_gold2,
                                     start_state=state.consecutive_loss)
            result_pdf = dp_result[n_uncertain]
            method_label = "exact"
    else:  # clt
        return _up_distribution_clt_impl(state, n_up)

    # --- pity shift + guaranteed gold (dp-path only; dp-state result is complete) ---
    if eff_method == "dp-path":
        shifted_first = np.insert(
            p_gold[state.pity + 1:] / p_gold[state.pity + 1:].sum(), 0, 0,
        )
        result_pdf = np.convolve(result_pdf, shifted_first)
    if state.guaranteed:
        result_pdf = np.convolve(result_pdf, p_gold)

    cdf = np.cumsum(result_pdf)
    return UpDistribution(pdf=result_pdf, cdf=cdf, method=method_label)


def _uncertain_pdf_path(
    k_miss: int, n_uncertain: int, pdfs: list[np.ndarray]
) -> np.ndarray:
    """dp-path: enumerate win/loss sequences, group by total golds."""
    seq2p = guarantee_seq(k_miss, n_uncertain)
    gold2p: Counter[int] = Counter()
    for seq, (_final_miss, p) in seq2p.items():
        gold2p[sum(seq)] += p

    max_gold = max(gold2p.keys())
    result = np.zeros(len(pdfs[max_gold]), dtype=np.float64)
    for gold, p in gold2p.items():
        result[: len(pdfs[gold - 1])] += pdfs[gold - 1] * p
    return result


def stable_up_distribution(n_up: int, method: str = "auto") -> UpDistribution:
    """Steady-state distribution: k_miss weighted by the stationary distribution."""
    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")

    max_len = 0
    dists: list[UpDistribution] = []
    for k_miss, weight in enumerate(STABLE_P):
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k_miss)
        d = up_distribution(state, n_up, method=method)
        dists.append(d)
        max_len = max(max_len, len(d.pdf))

    stable_pdf = np.zeros(max_len, dtype=np.float64)
    for d, weight in zip(dists, STABLE_P):
        stable_pdf[: len(d.pdf)] += d.pdf * weight
    stable_cdf = np.cumsum(stable_pdf)
    return UpDistribution(pdf=stable_pdf, cdf=stable_cdf, method=dists[0].method)


def _up_distribution_clt_impl(
    state: CharacterState, n_up: int
) -> UpDistribution:
    """CLT approximation core — returns UpDistribution with pity + guaranteed handled."""
    n_uncertain = n_up - state.guaranteed

    # Moments via single-UP _solve_exact (no pity shift — added below)
    pdfs = get_gold_pdfs(CHARACTER_POOL)
    p_gold_loc = pdfs[1]
    p_gold2_loc = np.convolve(p_gold_loc, p_gold_loc)
    p_up = list(CAPTURE_RADIANCE_WIN_RATE)
    dp1 = _solve_exact(1, p_up, p_gold_loc, p_gold2_loc,
                       start_state=state.consecutive_loss)
    d1_pdf = dp1[1]
    mu_1 = float(np.sum(np.arange(len(d1_pdf)) * d1_pdf))
    m2 = float(np.sum((np.arange(len(d1_pdf)) ** 2) * d1_pdf))
    var_1 = m2 - mu_1**2

    mu_n = n_uncertain * mu_1
    std_n = np.sqrt(n_uncertain * var_1)

    lo = max(0, int(mu_n - 6 * std_n))
    hi = int(mu_n + 6 * std_n)
    edges = np.arange(lo - 0.5, hi + 1.0, dtype=np.float64)
    pdf_clt = np.diff(norm.cdf(edges, loc=mu_n, scale=std_n))

    # Zero-pad to align pull counts with array indices
    pdf = np.zeros(hi + 1, dtype=np.float64)
    pdf[lo : hi + 1] = pdf_clt

    # Pity shift + guaranteed gold
    shifted_first = np.insert(
        p_gold_loc[state.pity + 1:] / p_gold_loc[state.pity + 1:].sum(), 0, 0,
    )
    result_pdf = np.convolve(pdf, shifted_first)
    if state.guaranteed:
        result_pdf = np.convolve(result_pdf, p_gold_loc)

    cdf = np.cumsum(result_pdf)
    return UpDistribution(pdf=result_pdf, cdf=cdf, method="clt")

