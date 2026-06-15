"""Weapon banner: epitomized-path probability for rate-up 5-star weapons.

The epitomized path guarantees that after one miss (not getting the chosen
weapon), the next 5-star is the chosen one.

Standard guarantee (independent): after a standard 5-star, the next is
guaranteed limited (50% A, 50% B).
"""

from dataclasses import dataclass, field

import numpy as np

from ._constants import WEAPON_POOL
from ._gold import get_gold_pdfs


@dataclass
class WeaponState:
    """State of the weapon banner before pulling.

    Attributes:
        pity:              Pulls since last 5-star (0..79).
        epitomized_points: Epitomized Path points (0..2).
                          At ≥1, next non-chosen 5-star triggers the guarantee
                          (so effectively the next is the chosen one).
        prev_standard:     Whether the previous 5-star was standard
                          (triggers standard guarantee: next is limited).
    """

    pity: int = 0
    epitomized_points: int = 0
    prev_standard: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.pity < WEAPON_POOL.hard_pity:
            raise ValueError(f"pity must be 0..{WEAPON_POOL.hard_pity - 1}, got {self.pity}")
        if not 0 <= self.epitomized_points <= 2:
            raise ValueError(f"epitomized_points must be 0..2, got {self.epitomized_points}")


@dataclass
class WeaponTarget:
    """What you want from the weapon banner.

    Only ``count_a`` is supported (定轨不取消).
    ``count_b`` > 0 is deferred to Phase 4.
    """

    count_a: int = 1
    count_b: int = 0

    def __post_init__(self) -> None:
        if self.count_b > 0:
            raise NotImplementedError(
                "Multi-weapon targets (count_b > 0) are not yet supported."
            )


def _single_copy_weights(
    epitomized_points: int, prev_standard: bool
) -> dict[int, float]:
    """Gold-count weights for ONE copy of weapon A from the given state.

    Epitomized path: if you don't get A → next is guaranteed A (2 golds).
    Standard guarantee: if prev was standard → next cannot be standard
    → pool is 50% A, 50% B.
    """
    if epitomized_points >= 1:
        # Already have a "miss" — next gold IS the chosen weapon
        return {1: 1.0}

    if prev_standard:
        # Standard guarantee active: no standard possible
        # 50% A (1 gold), 50% B → epitomized=1 → next is A (2 golds)
        return {1: 0.5, 2: 0.5}

    # Default: 25% standard, 37.5% A, 37.5% B
    return {1: 0.375, 2: 0.625}


def weapon_target_weights(
    target: WeaponTarget,
    epitomized_points: int = 0,
    prev_standard: bool = False,
) -> dict[int, float]:
    """Gold-count weights for *target* from the given state.

    For *k* copies the distribution is the *k*-fold convolution of the
    per-copy distribution, with state resetting after each obtained copy.
    """
    if target.count_b > 0:
        raise NotImplementedError("count_b > 0 not supported yet")

    weights: dict[int, float] = {0: 1.0}
    ep = epitomized_points
    ps = prev_standard

    for _ in range(target.count_a):
        single = _single_copy_weights(ep, ps)
        new: dict[int, float] = {}
        for g1, p1 in weights.items():
            for g2, p2 in single.items():
                new[g1 + g2] = new.get(g1 + g2, 0.0) + p1 * p2
        weights = new
        # After obtaining A, state resets
        ep = 0
        ps = False

    return weights


@dataclass
class WeaponUpDistribution:
    """Distribution of pulls for a weapon target."""

    pdf: np.ndarray
    cdf: np.ndarray
    gold_weights: dict[int, float] = field(default_factory=dict)

    @property
    def expected(self) -> float:
        return float(np.sum(np.arange(len(self.pdf)) * self.pdf))

    def quantile(self, q: float) -> int:
        return int(np.searchsorted(self.cdf, q))

    def luck(self, pulls: int) -> float:
        if pulls >= len(self.cdf):
            return 1.0
        return float(self.cdf[max(0, pulls)])

    def probability(self, pulls: int) -> float:
        return self.luck(pulls)


def weapon_up_distribution(
    state: WeaponState,
    target: WeaponTarget,
) -> WeaponUpDistribution:
    """Distribution of pulls to obtain *target* from *state*.

    Weights are computed analytically. Then each gold-count branch is
    convolved with the corresponding multi-gold PDF, and finally the
    current pity is applied via a shifted convolution.
    """
    weights = weapon_target_weights(
        target,
        epitomized_points=state.epitomized_points,
        prev_standard=state.prev_standard,
    )
    pdfs = get_gold_pdfs(WEAPON_POOL)

    # Weighted sum of multi-gold PDFs (gold > 0 only)
    max_gold = max(weights.keys())
    result_pdf = np.zeros(len(pdfs[max_gold]), dtype=np.float64)
    for gold, w in weights.items():
        if w > 0 and gold > 0:
            result_pdf[: len(pdfs[gold])] += pdfs[gold] * w

    # Shift by current pity
    shifted_first = np.insert(
        pdfs[1][state.pity + 1:] / pdfs[1][state.pity + 1:].sum(),
        0, 0,
    )
    result_pdf = np.convolve(result_pdf, shifted_first)

    cdf = np.cumsum(result_pdf)
    return WeaponUpDistribution(pdf=result_pdf, cdf=cdf, gold_weights=weights)
