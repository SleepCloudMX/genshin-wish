"""Character event banner: UP distribution for n copies of the rate-up 5-star."""

import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from ._constants import CHARACTER_POOL, STABLE_P, CLT_THRESHOLD, CAPTURE_RADIANCE_WIN_RATE
from ._capture_radiance import guarantee_seq
from ._gold import get_gold_pdfs
from .long_term import _post50_moments, _solve_exact


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
    ``"auto"`` n_uncertain ≤ 500 → dp-golds, > 500 → clt + warning
    ``"dp-path"``  enumerate all win/loss sequences (≤ 20 only)
    ``"dp-state"`` iterative state-space convolution
    ``"dp-golds"`` DP over gold counts + weighted PDFs
    ``"clt"``     CLT normal approximation
    ========== ====================================================
    """
    from ._dp_golds import _dp_golds_task1, golds_to_pulls as _golds_to_pulls

    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")

    n_uncertain = n_up - state.guaranteed

    # Resolve method
    if method == "auto":
        if n_uncertain <= 500:
            eff_method = "dp-golds"
        else:
            eff_method = "clt"
            warnings.warn(
                f"n_up={n_up} exceeds 500, switching to CLT approximation. "
                f"Use method='dp-golds' to force exact computation."
            )
    elif method == "dp-path":
        if n_uncertain > 20:
            raise ValueError(
                f"dp-path limited to n_uncertain ≤ 20, got {n_uncertain}. "
                f"Use method='dp-golds', 'dp-state', or 'clt'."
            )
        eff_method = "dp-path"
    elif method in ("dp-golds", "dp-state", "clt"):
        eff_method = method
    else:
        raise ValueError(
            f"Unknown method: {method!r}. "
            f"Valid: 'auto', 'dp-golds', 'dp-path', 'dp-state', 'clt'."
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
            eff_method = "dp-path"  # fall back for pity handling
            result_pdf = _uncertain_pdf_path(state.consecutive_loss, n_uncertain, pdfs)
            method_label = "exact"
        else:
            p_up = list(CAPTURE_RADIANCE_WIN_RATE)
            dp_result = _solve_exact(n_uncertain, p_up, p_gold, p_gold2,
                                     start_state=state.consecutive_loss)
            result_pdf = dp_result[n_uncertain]
            method_label = "exact"
    elif eff_method == "dp-golds":
        if state.pity > 0:
            eff_method = "dp-path"  # fall back for pity handling
            result_pdf = _uncertain_pdf_path(state.consecutive_loss, n_uncertain, pdfs)
            method_label = "exact"
        else:
            gold_probs = _dp_golds_task1(n_uncertain, state.consecutive_loss)
            dist = _golds_to_pulls(gold_probs, pdfs)
            result_pdf = dist.pdf
            method_label = "exact"
    else:  # clt
        return _up_distribution_clt_impl(state, n_up)

    # --- pity shift + guaranteed gold ---
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


def n_std_distribution(state: CharacterState, n_up: int) -> dict[int, float]:
    """Marginal distribution of standard character count given *n_up* rate-ups.

    Only supports ``pity=0`` (raises ``ValueError`` otherwise).

    Returns ``{n_std: probability}``.
    """
    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")
    if state.pity != 0:
        raise ValueError(f"pity must be 0 (not yet supported), got {state.pity}")

    n_uncertain = n_up - (1 if state.guaranteed else 0)

    if n_uncertain <= 0:
        return {0: 1.0}

    if n_uncertain <= 6:
        return _n_std_dist_path(state.consecutive_loss, n_uncertain)

    from ._dp_golds import _dp_golds_full, golds_nstd_to_nstd_dist
    joint = _dp_golds_full(n_uncertain, state.consecutive_loss)
    return golds_nstd_to_nstd_dist(joint)


def radiance_distribution(state: CharacterState, n_up: int) -> dict[int, float]:
    """Distribution of Capturing Radiance trigger count for *n_up* UPs.

    Only supports ``pity=0``.  Returns ``{radiance_count: probability}``.
    """
    from ._capture_radiance import radiance_dist_from_n_up

    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")
    if state.pity != 0:
        raise ValueError(f"pity must be 0 (not yet supported), got {state.pity}")

    n_uncertain = n_up - (1 if state.guaranteed else 0)
    if n_uncertain <= 0:
        return {0: 1.0}
    return radiance_dist_from_n_up(n_uncertain, state.consecutive_loss)


def _n_std_dist_path(k_miss: int, n_uncertain: int) -> dict[int, float]:
    """dp-path: count losses (2s) per sequence to get n_std distribution."""
    seq2p = guarantee_seq(k_miss, n_uncertain)
    result: dict[int, float] = defaultdict(float)
    for seq, (_final_k, prob) in seq2p.items():
        result[seq.count(2)] += prob
    return dict(result)


def n_std_conditional_pulls(
    state: CharacterState, n_up: int, n_std: int | None = None,
) -> dict[int, UpDistribution]:
    """Conditional pulls distribution per standard count given *n_up* rate-ups.

    Only supports ``pity=0`` (raises ``ValueError`` otherwise).

    Returns ``{n_std: UpDistribution}``.  If *n_std* is given, only that
    key is returned.
    """
    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")
    if state.pity != 0:
        raise ValueError(f"pity must be 0 (not yet supported), got {state.pity}")

    n_uncertain = n_up - (1 if state.guaranteed else 0)
    p_gold = get_gold_pdfs(CHARACTER_POOL, min_gold=1)[0]

    if n_uncertain <= 0:
        dist = UpDistribution(pdf=p_gold, cdf=np.cumsum(p_gold), method="exact")
        return {0: dist}

    if n_uncertain <= 6:
        dists = _n_std_conditional_path(state.consecutive_loss, n_uncertain)
    else:
        from ._dp_golds import _dp_golds_full, golds_nstd_to_pulls
        joint = _dp_golds_full(n_uncertain, state.consecutive_loss)
        dists = golds_nstd_to_pulls(joint)

    # Convolve guaranteed gold if applicable
    if state.guaranteed:
        for ns in list(dists):
            d = dists[ns]
            conv = np.convolve(d.pdf, p_gold)
            dists[ns] = UpDistribution(pdf=conv, cdf=np.cumsum(conv), method=d.method)

    if n_std is not None:
        if n_std in dists:
            return {n_std: dists[n_std]}
        # n_std not reachable → empty distribution
        return {n_std: UpDistribution(
            pdf=np.array([np.nan]), cdf=np.array([np.nan]), method="exact",
        )}
    return dists


def _n_std_conditional_path(
    k_miss: int, n_uncertain: int,
) -> dict[int, UpDistribution]:
    """dp-path: per-n_std conditional pulls distributions."""
    seq2p = guarantee_seq(k_miss, n_uncertain)
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=n_uncertain * 2)

    nstd_golds: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for seq, (_final_k, prob) in seq2p.items():
        gold = sum(seq)
        ns = seq.count(2)
        nstd_golds[ns][gold] += prob

    result: dict[int, UpDistribution] = {}
    for ns, gold_probs in nstd_golds.items():
        total = sum(gold_probs.values())
        max_gold = max(gold_probs.keys())
        pdf_arr = np.zeros(len(pdfs[max_gold]), dtype=np.float64)
        for gold, prob in gold_probs.items():
            if gold > 0:
                pdf_arr[: len(pdfs[gold])] += pdfs[gold] * (prob / total)
        cdf = np.cumsum(pdf_arr)
        result[ns] = UpDistribution(pdf=pdf_arr, cdf=cdf, method="exact")

    return result


def _up_distribution_clt_impl(
    state: CharacterState, n_up: int
) -> UpDistribution:
    """CLT approximation — mixed moments: first UP from initial k_miss,
    remaining n−1 from steady-state."""
    n_uncertain = n_up - state.guaranteed

    pdfs = get_gold_pdfs(CHARACTER_POOL)
    p_gold = pdfs[1]

    # First UP moments (from initial k_miss)
    p_up = list(CAPTURE_RADIANCE_WIN_RATE)
    p_gold2 = np.convolve(p_gold, p_gold)
    dp1 = _solve_exact(1, p_up, p_gold, p_gold2,
                       start_state=state.consecutive_loss)
    d1_pdf = dp1[1]
    mu_first = float(np.sum(np.arange(len(d1_pdf)) * d1_pdf))
    m2_first = float(np.sum((np.arange(len(d1_pdf)) ** 2) * d1_pdf))
    var_first = m2_first - mu_first**2

    # Steady-state moments for remaining UPs
    mu_steady, var_steady = _post50_moments(p_gold)

    # Mixed moments: first UP + (n−1) × steady
    mu_n = mu_first + (n_uncertain - 1) * mu_steady
    var_n = var_first + (n_uncertain - 1) * var_steady
    std_n = np.sqrt(max(var_n, 0.0))

    lo = max(0, int(mu_n - 6 * std_n))
    hi = int(mu_n + 6 * std_n)
    edges = np.arange(lo - 0.5, hi + 1.0, dtype=np.float64)
    pdf_clt = np.diff(norm.cdf(edges, loc=mu_n, scale=std_n))

    pdf = np.zeros(hi + 1, dtype=np.float64)
    pdf[lo : hi + 1] = pdf_clt

    # Pity shift — only when pity > 0 (pity=0: CLT moments already correct)
    if state.pity > 0:
        shifted_first = np.insert(
            p_gold[state.pity + 1:] / p_gold[state.pity + 1:].sum(), 0, 0,
        )
        pdf = np.convolve(pdf, shifted_first)
    if state.guaranteed:
        pdf = np.convolve(pdf, p_gold)

    cdf = np.cumsum(pdf)
    return UpDistribution(pdf=pdf, cdf=cdf, method="clt")

