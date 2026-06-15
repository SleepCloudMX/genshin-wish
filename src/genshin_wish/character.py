"""Character event banner: UP distribution for n copies of the rate-up 5-star."""

from collections import Counter
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from ._constants import CHARACTER_POOL, STABLE_P, CLT_THRESHOLD
from ._capture_radiance import guarantee_seq
from ._gold import get_gold_pdfs


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


def up_distribution(state: CharacterState, n_up: int) -> UpDistribution:
    """Exact distribution of pulls to obtain *n_up* rate-up characters from *state*.

    Decomposes the total pulls into three independent parts:
    1. The *first gold* — shifted by current pity (state.pity).
    2. The *uncertain golds* from n_up - state.guaranteed win/loss sequences.
    3. The *guaranteed gold* (if state.guaranteed) — one extra gold with no shift.

    These parts are independent because gold timing resets after each gold
    (the process is a renewal process). The shift for curr_pulls can be
    applied to any term in the convolution chain (convolution is commutative),
    so we apply it to part 1 for all cases.

    Example (n_up=2, guaranteed=False, k_miss=0):
      - win-win: 2 golds → pdfs[1] ⊗ pdfs[1] = pdfs[2]
      - win-loss: 3 golds → pdfs[2] ⊗ pdfs[1] = pdfs[3]
      The "first gold" (shifted) is the same for both paths.
    """
    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")

    n_uncertain = n_up - state.guaranteed
    # Worst-case golds: alternating (loss*3, win) groups → ~1.75n.
    # Use 2n as a safe upper bound (all-loss scenario).
    min_gold_needed = n_uncertain * 2 + 3
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=min_gold_needed)

    if n_uncertain == 0:
        # Only the guaranteed gold (or n_up=0 → immediate success)
        shifted = np.insert(
            pdfs[1][state.pity + 1:] / pdfs[1][state.pity + 1:].sum(),
            0, 0,
        )
        if not state.guaranteed and n_up == 0:
            return UpDistribution(pdf=np.array([1.0]), cdf=np.array([1.0]))
        cdf = np.cumsum(shifted)
        return UpDistribution(pdf=shifted, cdf=cdf)

    # Enumerate win/loss sequences for the uncertain UPs
    seq2p = guarantee_seq(state.consecutive_loss, n_uncertain)
    gold2p: Counter[int] = Counter()
    for seq, (_final_miss, p) in seq2p.items():
        gold2p[sum(seq)] += p

    # Weighted sum of multi-gold PDFs for the uncertain part
    max_gold = max(gold2p.keys())
    result_pdf = np.zeros(len(pdfs[max_gold]), dtype=np.float64)
    for gold, p in gold2p.items():
        result_pdf[: len(pdfs[gold - 1])] += pdfs[gold - 1] * p

    # Convolve with the first gold (shifted by current pity)
    shifted_first = np.insert(
        pdfs[1][state.pity + 1:] / pdfs[1][state.pity + 1:].sum(),
        0, 0,
    )
    result_pdf = np.convolve(result_pdf, shifted_first)

    # If the next gold is guaranteed, convolve with one extra gold
    if state.guaranteed:
        result_pdf = np.convolve(result_pdf, pdfs[1])

    cdf = np.cumsum(result_pdf)
    return UpDistribution(pdf=result_pdf, cdf=cdf)


def stable_up_distribution(n_up: int) -> UpDistribution:
    """Steady-state distribution: k_miss weighted by the stationary distribution."""
    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")

    max_len = 0
    dists: list[UpDistribution] = []
    for k_miss, weight in enumerate(STABLE_P):
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k_miss)
        d = up_distribution(state, n_up)
        dists.append(d)
        max_len = max(max_len, len(d.pdf))

    stable_pdf = np.zeros(max_len, dtype=np.float64)
    for d, weight in zip(dists, STABLE_P):
        stable_pdf[: len(d.pdf)] += d.pdf * weight
    stable_cdf = np.cumsum(stable_pdf)
    return UpDistribution(pdf=stable_pdf, cdf=stable_cdf, method="exact")


def up_distribution_clt(
    state: CharacterState | None = None, n_up: int = 1
) -> UpDistribution:
    """CLT approximation for large *n_up*.

    Uses the first two moments of a single UP distribution and the
    normal approximation with continuity correction.
    Suitable when n_up exceeds CLT_THRESHOLD.
    """
    if state is None:
        # Steady-state: weighted average of per-state moments
        mu_1 = 0.0
        m2_sum = 0.0
        for k_miss, weight in enumerate(STABLE_P):
            s = CharacterState(guaranteed=False, pity=0, consecutive_loss=k_miss)
            d = up_distribution(s, 1)
            m1 = d.expected
            m2 = float(np.sum((np.arange(len(d.pdf)) ** 2) * d.pdf))
            mu_1 += weight * m1
            m2_sum += weight * m2
        var_1 = m2_sum - mu_1**2
    else:
        d = up_distribution(state, 1)
        mu_1 = d.expected
        m2 = float(np.sum((np.arange(len(d.pdf)) ** 2) * d.pdf))
        var_1 = m2 - mu_1**2

    mu_n = n_up * mu_1
    std_n = np.sqrt(n_up * var_1)

    # Build PDF/CDF on a grid covering ±6σ (~99.9999%)
    lo = max(0, int(mu_n - 6 * std_n))
    hi = int(mu_n + 6 * std_n) + 1
    edges = np.arange(lo - 0.5, hi + 0.5, dtype=np.float64)
    pdf = np.diff(norm.cdf(edges, loc=mu_n, scale=std_n))
    cdf = np.cumsum(pdf)

    return UpDistribution(pdf=pdf, cdf=cdf, method="clt")
