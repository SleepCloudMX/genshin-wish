"""Weapon banner: epitomized-path probability for rate-up 5-star weapons.

The epitomized path guarantees that after one miss (not getting the chosen
weapon), the next 5-star is the chosen one.  `epitomized_points` is 0 or 1.

The standard guarantee (independent): after a standard 5-star, the next is
guaranteed limited (50% A, 50% B).
"""

import warnings
from dataclasses import dataclass, field

import numpy as np

from ._constants import WEAPON_POOL
from ._gold import get_gold_pdfs, gold_count_pmf, joint_from_labels


@dataclass
class WeaponState:
    """State of the weapon banner before pulling.

    Attributes:
        pity:              Pulls since last 5-star (0..79).
        epitomized_points: Epitomized Path points (0..1).
                          1 means the last 5-star was not the chosen weapon
                          → next 5-star is guaranteed to be the chosen one.
        prev_standard:     Whether the previous 5-star was standard
                          (triggers standard guarantee: next is limited).
    """

    pity: int = 0
    epitomized_points: int = 0
    prev_standard: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.pity < WEAPON_POOL.hard_pity:
            raise ValueError(f"pity must be 0..{WEAPON_POOL.hard_pity - 1}, got {self.pity}")
        if self.epitomized_points not in (0, 1):
            raise ValueError(f"epitomized_points must be 0 or 1, got {self.epitomized_points}")


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
    if epitomized_points == 1:
        # Already have a "miss" — next gold IS the chosen weapon
        return {1: 1.0}

    if prev_standard:
        # Standard guarantee active: no standard possible
        # 50% A (1 gold), 50% B → epitomized=1 → next is A (2 golds)
        return {1: 0.5, 2: 0.5}

    # Default: 25% standard, 37.5% A, 37.5% B
    return {1: 0.375, 2: 0.625}


def weapon_pulls_joint_distribution(
    state: WeaponState, n_pulls: int,
) -> dict[int, dict[int, float]]:
    """给定抽数下（定轨目标数, 歪出的五星数）的联合分布。

    与角色池同理：出金时刻由 pity 过程决定，与「每金是目标 / 另一把限定 / 常驻」相互独立，
    故分解为 ``P(恰好 g 金 | n_pulls 抽) · D[g][u]``（g = u + 歪出数）。

    Returns ``{目标数: {歪出数: 概率}}``，只列出概率非零的项。
    """
    if n_pulls < 0:
        raise ValueError(f"n_pulls must be >= 0, got {n_pulls}")

    pmf = gold_count_pmf(WEAPON_POOL, state.pity, n_pulls)
    chain = _weapon_label_chain(len(pmf) - 1, state.epitomized_points, state.prev_standard)
    return joint_from_labels(pmf, chain)


def _weapon_label_chain(
    g_max: int, epitomized_points: int, prev_standard: bool,
) -> np.ndarray:
    """D[g][u] = P(前 g 个金中恰有 u 个是定轨目标)。

    每金的标签取决于状态 (命定值, 上一金为常驻)：命定值满则必为目标；常驻保底生效时
    池中只有两把限定（各半）；否则 37.5% 目标 / 37.5% 另一把限定 / 25% 常驻。
    得到目标后状态归零；得到另一把限定 → 命定值 +1；得到常驻 → 命定值 +1 且常驻保底生效。
    """
    states = [(0, False), (0, True), (1, False), (1, True)]
    label = {
        (0, False): (0.375, 0.375, 0.25),
        (0, True): (0.5, 0.5, 0.0),
        (1, False): (1.0, 0.0, 0.0),
        (1, True): (1.0, 0.0, 0.0),
    }
    A = {st: np.zeros(g_max + 1) for st in states}
    A[(epitomized_points, bool(prev_standard))][0] = 1.0

    D = np.zeros((g_max + 1, g_max + 1))
    D[0, 0] = 1.0
    for g in range(1, g_max + 1):
        B = {st: np.zeros(g_max + 1) for st in states}
        for st in states:
            src = A[st]
            if not src.any():
                continue
            p_a, p_b, p_s = label[st]
            if p_a:
                B[(0, False)][1:] += src[:-1] * p_a      # 目标
            if p_b:
                B[(1, False)] += src * p_b               # 另一把限定 → 命定值 +1
            if p_s:
                B[(1, True)] += src * p_s                # 常驻 → 命定值 +1 且保底生效
        A = B
        for st in states:
            D[g] += A[st]
    return D


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
    if target.count_a > 500:
        warnings.warn(
            f"count_a={target.count_a} exceeds 500, computation may be slow."
        )
    weights = weapon_target_weights(
        target,
        epitomized_points=state.epitomized_points,
        prev_standard=state.prev_standard,
    )
    pdfs = get_gold_pdfs(WEAPON_POOL)

    # Weighted sum of multi-gold PDFs.
    # The first gold gets pity-shifted; remaining golds use full pdfs.
    if state.pity == 0:
        first_gold_pdf = pdfs[1]
    else:
        first_gold_pdf = np.insert(
            pdfs[1][state.pity + 1:] / pdfs[1][state.pity + 1:].sum(),
            0, 0,
        )

    max_gold = max(weights.keys())
    if max_gold == 0:
        return WeaponUpDistribution(
            pdf=np.array([1.0], dtype=np.float64),
            cdf=np.array([1.0], dtype=np.float64),
            gold_weights=weights,
        )

    # weights count total golds; the first gold's pulls come from
    # first_gold_pdf, so only the remaining golds (gold - 1) are convolved in.
    result_pdf = np.zeros(len(first_gold_pdf) + len(pdfs[max_gold - 1]) - 1,
                          dtype=np.float64)
    for gold, w in weights.items():
        if w > 0 and gold > 0:
            contrib = np.convolve(first_gold_pdf, pdfs[gold - 1]) * w
            if len(contrib) > len(result_pdf):
                result_pdf = np.pad(result_pdf,
                                    (0, len(contrib) - len(result_pdf)))
            result_pdf[: len(contrib)] += contrib

    cdf = np.cumsum(result_pdf)
    return WeaponUpDistribution(pdf=result_pdf, cdf=cdf, gold_weights=weights)
