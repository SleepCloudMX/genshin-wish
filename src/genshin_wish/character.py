"""Character event banner: UP distribution for n copies of the rate-up 5-star."""

import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from ._constants import CHARACTER_POOL, STABLE_P, CLT_THRESHOLD, CAPTURE_RADIANCE_WIN_RATE
from ._capture_radiance import guarantee_seq
from ._gold import get_gold_pdfs
from .long_term import _post50_moments, _pre50_moments, _solve_exact, _solve_pre50


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

    # gold2p counts total golds; the first gold's pulls are added by the
    # caller, so the array only spans the remaining golds (gold - 1).
    max_gold = max(gold2p.keys())
    result = np.zeros(len(pdfs[max_gold - 1]), dtype=np.float64)
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


def pulls_joint_distribution(
    state: CharacterState, n_pulls: int,
) -> dict[int, dict[int, float]]:
    """Joint distribution of (rate-ups, standard 5★) within *n_pulls* pulls.

    出金时刻由 pity 过程决定，与「每金是 UP 还是常驻」相互独立，故可分解为
    ``P(恰好 g 金 | n_pulls 抽) · D[g][u]``（g = u + n_std，D 为标记链给出的
    「前 g 金的 UP 数分布」）。

    Returns ``{n_up: {n_std: probability}}``，只列出概率非零的项。
    """
    if n_pulls < 0:
        raise ValueError(f"n_pulls must be >= 0, got {n_pulls}")

    pmf = _gold_count_pmf(state.pity, n_pulls)
    chain = _label_chain(len(pmf) - 1, state.consecutive_loss, state.guaranteed)

    acc: dict[int, dict[int, float]] = defaultdict(dict)
    for g, p in enumerate(pmf):
        if p == 0.0:
            continue
        for u in range(g + 1):
            w = chain[g][u]
            if w == 0.0:
                continue
            row = acc[u]
            row[g - u] = row.get(g - u, 0.0) + p * w
    return {u: dict(row) for u, row in acc.items()}


def stable_pulls_joint_distribution(n_pulls: int) -> dict[int, dict[int, float]]:
    """Steady-state variant: k_miss weighted by the stationary distribution."""
    acc: dict[int, dict[int, float]] = {}
    for k_miss, weight in enumerate(STABLE_P):
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k_miss)
        for u, row in pulls_joint_distribution(state, n_pulls).items():
            dst = acc.setdefault(u, {})
            for n_std, p in row.items():
                dst[n_std] = dst.get(n_std, 0.0) + weight * p
    return acc


def _gold_count_pmf(pity: int, n_pulls: int, eps: float = 1e-15) -> np.ndarray:
    """P(恰好 g 金 | n_pulls 抽)，g = 0..g_max，尾部概率 < eps 时截断。

    ``P(恰好 g 金) = P(T_g ≤ P) − P(T_{g+1} ≤ P)``，T_g 由单金 PDF 逐次卷积得到
    （首金按当前 pity 平移）；只对 t ≤ n_pulls 求和，卷积可截断到 n_pulls + 1 项。
    """
    p_first = get_gold_pdfs(CHARACTER_POOL)[1]
    if pity == 0:
        dist = p_first.copy()
    else:
        tail = p_first[pity + 1:]
        dist = np.insert(tail / tail.sum(), 0, 0)

    out: list[float] = []
    prev = 1.0
    for _ in range(n_pulls + 2):
        cur = float(dist[: n_pulls + 1].sum())
        out.append(max(prev - cur, 0.0))
        if cur < eps:
            break
        dist = np.convolve(dist[: n_pulls + 1], p_first)
        prev = cur
    return np.array(out, dtype=np.float64)


def _label_chain(g_max: int, k_miss: int, guaranteed: bool) -> np.ndarray:
    """D[g][u] = P(前 g 个金中恰有 u 个 UP)。

    标记链：中的金 1 金换 1 UP 且 k_miss 归零；歪的金计 2 金（歪出的常驻 + 下一金
    保底 UP），k_miss + 1（上限 3）；保底待发时下一金必为 UP。
    """
    p_up = CAPTURE_RADIANCE_WIN_RATE
    A = [[np.zeros(g_max + 1), np.zeros(g_max + 1)] for _ in range(4)]
    A[k_miss][1 if guaranteed else 0][0] = 1.0

    D = np.zeros((g_max + 1, g_max + 1))
    D[0, 0] = 1.0
    for g in range(1, g_max + 1):
        B = [[np.zeros(g_max + 1), np.zeros(g_max + 1)] for _ in range(4)]
        for k in range(4):
            for pend in (0, 1):
                src = A[k][pend]
                if not src.any():
                    continue
                if pend:
                    B[k][0][1:] += src[:-1]
                else:
                    B[0][0][1:] += src[:-1] * p_up[k]
                    if k < 3:
                        B[k + 1][1] += src * (1.0 - p_up[k])
        A = B
        for k in range(4):
            for pend in (0, 1):
                D[g] += A[k][pend]
    return D


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


# ---------------------------------------------------------------------------
# Pre-5.0 (no Capture Radiance) distribution functions
# ---------------------------------------------------------------------------


def up_distribution_pre50(
    state: CharacterState, n_up: int, method: str = "auto",
) -> UpDistribution:
    """Pre-5.0 distribution: each 50/50 is independent, no Capture Radiance.

    State only tracks ``guaranteed`` and ``pity``; ``consecutive_loss`` is
    ignored (always treated as 0).
    """
    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")

    n_uncertain = n_up - (1 if state.guaranteed else 0)
    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=3 if n_uncertain == 0 else n_uncertain * 2 + 3)
    p_gold = pdfs[1]

    if n_uncertain == 0:
        shifted = np.insert(
            p_gold[state.pity + 1:] / p_gold[state.pity + 1:].sum(), 0, 0,
        )
        if not state.guaranteed and n_up == 0:
            return UpDistribution(pdf=np.array([1.0]), cdf=np.array([1.0]))
        cdf = np.cumsum(shifted)
        return UpDistribution(pdf=shifted, cdf=cdf)

    p_gold2 = np.convolve(p_gold, p_gold)

    if method == "auto":
        eff_method = "exact" if n_uncertain <= 500 else "clt"
    elif method == "exact":
        eff_method = "exact"
    elif method == "clt":
        eff_method = "clt"
    else:
        raise ValueError(
            f"Unknown method: {method!r}. Valid: 'auto', 'exact', 'clt'."
        )

    if eff_method == "exact":
        if state.pity == 0:
            pre50_pdfs = _solve_pre50(n_uncertain, p_gold, p_gold2)
            result_pdf = pre50_pdfs[n_uncertain]
        else:
            # pity>0: first gold shifted, rest from pity=0
            p_gold_pity = np.insert(
                p_gold[state.pity + 1:] / p_gold[state.pity + 1:].sum(), 0, 0,
            )
            p_two = np.convolve(p_gold_pity, p_gold)
            max_len = max(len(p_gold_pity), len(p_two))
            p1 = np.zeros(max_len, dtype=np.float64)
            p2 = np.zeros(max_len, dtype=np.float64)
            p1[: len(p_gold_pity)] = p_gold_pity
            p2[: len(p_two)] = p_two
            first_up = 0.5 * p1 + 0.5 * p2
            if n_uncertain == 1:
                result_pdf = first_up
            else:
                rest = _solve_pre50(n_uncertain - 1, p_gold, p_gold2)
                result_pdf = np.convolve(first_up, rest[n_uncertain - 1])
    else:
        return _up_distribution_clt_impl_pre50(state, n_up)

    if state.guaranteed:
        result_pdf = np.convolve(result_pdf, p_gold)

    cdf = np.cumsum(result_pdf)
    return UpDistribution(pdf=result_pdf, cdf=cdf, method="exact")


def _up_distribution_clt_impl_pre50(
    state: CharacterState, n_up: int,
) -> UpDistribution:
    """CLT approximation for pre-5.0: all uncertain UPs are i.i.d."""
    n_uncertain = n_up - (1 if state.guaranteed else 0)

    pdfs = get_gold_pdfs(CHARACTER_POOL)
    p_gold = pdfs[1]
    p_gold2 = np.convolve(p_gold, p_gold)

    mu_steady, var_steady = _pre50_moments(p_gold, p_gold2)
    mu_n = n_uncertain * mu_steady
    var_n = n_uncertain * var_steady
    std_n = np.sqrt(max(var_n, 0.0))

    lo = max(0, int(mu_n - 6 * std_n))
    hi = int(mu_n + 6 * std_n)
    edges = np.arange(lo - 0.5, hi + 1.0, dtype=np.float64)
    pdf_clt = np.diff(norm.cdf(edges, loc=mu_n, scale=std_n))

    pdf = np.zeros(hi + 1, dtype=np.float64)
    pdf[lo: hi + 1] = pdf_clt

    if state.pity > 0:
        shifted_first = np.insert(
            p_gold[state.pity + 1:] / p_gold[state.pity + 1:].sum(), 0, 0,
        )
        pdf = np.convolve(pdf, shifted_first)
    if state.guaranteed:
        pdf = np.convolve(pdf, p_gold)

    cdf = np.cumsum(pdf)
    return UpDistribution(pdf=pdf, cdf=cdf, method="clt")


def stable_up_distribution_pre50(
    n_up: int, method: str = "auto",
) -> UpDistribution:
    """Pre-5.0 steady-state distribution.

    In pre-5.0 the system always resets to non-guaranteed after each UP,
    so the steady state is simply state 0.
    """
    return up_distribution_pre50(
        CharacterState(guaranteed=False, pity=0), n_up, method=method,
    )


def n_std_distribution_pre50(
    state: CharacterState, n_up: int,
) -> dict[int, float]:
    """Pre-5.0 n_std distribution: Binomial(n_uncertain, 0.5)."""
    from math import comb

    if n_up < 0:
        raise ValueError(f"n_up must be >= 0, got {n_up}")
    if state.pity != 0:
        raise ValueError(f"pity must be 0 (not yet supported), got {state.pity}")

    n_uncertain = n_up - (1 if state.guaranteed else 0)
    if n_uncertain <= 0:
        return {0: 1.0}

    result = {}
    for k in range(n_uncertain + 1):
        result[k] = comb(n_uncertain, k) * (0.5 ** n_uncertain)
    return result


def radiance_distribution_pre50(
    state: CharacterState, n_up: int,
) -> dict[int, float]:
    """Pre-5.0: no Capture Radiance, always 0 triggers."""
    return {0: 1.0}
