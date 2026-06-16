"""Long-term UP distribution over many 5-star acquisitions.

Supports pre-5.0 (pure 50/50 + guarantee) and post-5.0 (Capture Radiance)
phases, combined via convolution. Exports a solver factory compatible with
``viz/long_term.py``.
"""

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.stats import norm

from ._constants import CHARACTER_POOL, STABLE_P, CAPTURE_RADIANCE_WIN_RATE
from ._gold import get_gold_pdfs


@dataclass
class LongTermState:
    """Number of UPs obtained before and after version 5.0.

    Pre-5.0  uses pure 50/50 + guarantee (2-state, p_up = [0.5, 1.0]).
    Post-5.0 uses Capture Radiance (4-state).

    The two phases are independent — pre-5.0 always resets to state 0 after
    each UP, so post-5.0 always starts from k_miss=0.  Total distribution =
    conv(pre_N1_pdf, post_N2_pdf).
    """

    n_pre_50: int = 0
    n_post_50: int = 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pad(a: np.ndarray, length: int) -> np.ndarray:
    c = np.zeros(length, dtype=np.float64)
    c[: len(a)] = a
    return c


def _solve_exact(
    max_n: int,
    p_up: list[float],
    p_gold: np.ndarray,
    p_gold2: np.ndarray,
) -> dict[int, np.ndarray]:
    """Generic exact iterative convolution over *n_states*.

    Args:
        max_n: Number of UPs to compute (1..max_n).
        p_up:  Win probability per state.  State ``s`` (s < n_states-1) can
               lose; the last state always has p_up = 1.0.
        p_gold:  Single-gold PDF.
        p_gold2: Two-gold PDF (``np.convolve(p_gold, p_gold)``).

    Returns:
        ``{n: pdf}`` where pdf[i] = P(exactly *i* pulls for *n* UPs).
    """
    n_states = len(p_up)
    pdf_state: list[np.ndarray | None] = [None] * n_states
    pdf_state[0] = np.array([1.0], dtype=np.float64)
    result: dict[int, np.ndarray] = {}

    for n in range(1, max_n + 1):
        new = [np.zeros(1, dtype=np.float64) for _ in range(n_states)]
        for s in range(n_states):
            ps = pdf_state[s]
            if ps is None:
                continue
            # Win → state 0
            wc = np.convolve(ps, p_gold)
            new[0] = _pad(new[0], max(len(new[0]), len(wc)))
            new[0][: len(wc)] += wc * p_up[s]
            # Loss → state s+1  (last state never loses)
            if s < n_states - 1:
                lc = np.convolve(ps, p_gold2)
                new[s + 1] = _pad(new[s + 1], max(len(new[s + 1]), len(lc)))
                new[s + 1][: len(lc)] += lc * (1 - p_up[s])

        pdf_state = new
        non_none = [p for p in pdf_state if p is not None]
        mlen = max(len(p) for p in non_none)
        total = np.zeros(mlen, dtype=np.float64)
        for p in non_none:
            total[: len(p)] += p
        result[n] = total

    return result


# ---------------------------------------------------------------------------
# Steady-state per-UP moments
# ---------------------------------------------------------------------------

def _pre50_moments(p_gold: np.ndarray, p_gold2: np.ndarray) -> tuple[float, float]:
    """Pre-5.0 steady-state per-UP mean and variance.

    In steady state the system is always in state 0 (each UP completion
    resets to state 0), so each UP is i.i.d. with
    PDF = 0.5·p_gold + 0.5·p_gold2.
    """
    length = max(len(p_gold), len(p_gold2))
    p_up_single = 0.5 * _pad(p_gold, length) + 0.5 * _pad(p_gold2, length)
    mu = float(np.sum(np.arange(len(p_up_single)) * p_up_single))
    var = float(np.sum((np.arange(len(p_up_single)) ** 2) * p_up_single)) - mu**2
    return mu, var


def _post50_moments(p_gold: np.ndarray) -> tuple[float, float]:
    """Post-5.0 steady-state per-UP mean and variance."""
    p_up = CAPTURE_RADIANCE_WIN_RATE
    mu_gold = float(np.sum(np.arange(len(p_gold)) * p_gold))
    var_gold = float(np.sum((np.arange(len(p_gold)) ** 2) * p_gold)) - mu_gold**2
    mu_loss = 2.0 * mu_gold

    mu_1 = 0.0
    m2_sum = 0.0
    for s, pi in enumerate(STABLE_P):
        mu_s = p_up[s] * mu_gold + (1 - p_up[s]) * mu_loss
        m2_s = p_up[s] * (var_gold + mu_gold**2) + (1 - p_up[s]) * (
            2 * var_gold + mu_loss**2
        )
        mu_1 += pi * mu_s
        m2_sum += pi * m2_s
    return mu_1, m2_sum - mu_1**2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def make_long_solver(
    state: LongTermState,
    *,
    method: str = "exact",
) -> Callable[[int, list[float]], dict[float, list[tuple[float, float]]]]:
    """Create a solver callable for ``plot_long_term_luck``.

    Args:
        state:  Pre/post-5.0 UP counts.
        method: ``"exact"`` for iterative convolution (E) or ``"clt"`` for
                normal approximation (F).

    Returns:
        ``solver_func(N, alphas) -> {alpha: [(low, high), ...]}`` where
        each ``(low, high)`` is the cumulative pull count at quantile
        *alpha* / *1-alpha* for the *n*-th UP (n = 1 … N).
    """
    if method not in ("exact", "clt"):
        raise ValueError(f"method must be 'exact' or 'clt', got {method!r}")

    total = state.n_pre_50 + state.n_post_50
    if total == 0:
        raise ValueError(
            "LongTermState must have at least one UP (n_pre_50 + n_post_50 > 0)"
        )

    pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=total * 2 + 3)
    p_gold = pdfs[1]
    p_gold2 = np.convolve(p_gold, p_gold)

    N1 = state.n_pre_50
    N2 = state.n_post_50

    # ---- exact path ----
    if method == "exact":
        pre_pdfs: dict[int, np.ndarray] = {}
        if N1 > 0:
            pre_pdfs = _solve_exact(N1, [0.5, 1.0], p_gold, p_gold2)

        post_pdfs: dict[int, np.ndarray] = {}
        if N2 > 0:
            post_pdfs = _solve_exact(N2, list(CAPTURE_RADIANCE_WIN_RATE), p_gold, p_gold2)

        combined_cdfs: list[np.ndarray] = []
        for n in range(1, total + 1):
            if n <= N1:
                pdf = pre_pdfs[n]
            elif N1 == 0:
                pdf = post_pdfs[n]
            else:
                n_post = n - N1
                pdf = np.convolve(pre_pdfs[N1], post_pdfs[n_post])
            combined_cdfs.append(np.cumsum(pdf))

        def solver(N: int, alphas: list[float]) -> dict[float, list[tuple[float, float]]]:
            if N > total:
                raise ValueError(f"N ({N}) exceeds total UP ({total})")
            result: dict[float, list[tuple[float, float]]] = {a: [] for a in alphas}
            for i in range(N):
                cdf = combined_cdfs[i]
                for a in alphas:
                    lo = int(np.searchsorted(cdf, a))
                    hi = int(np.searchsorted(cdf, 1 - a))
                    result[a].append((lo, hi))
            return result

        return solver

    # ---- CLT path ----
    mu_pre, var_pre = _pre50_moments(p_gold, p_gold2)
    mu_post, var_post = _post50_moments(p_gold)

    def solver_clt(N: int, alphas: list[float]) -> dict[float, list[tuple[float, float]]]:
        if N > total:
            raise ValueError(f"N ({N}) exceeds total UP ({total})")
        result: dict[float, list[tuple[float, float]]] = {a: [] for a in alphas}
        for i in range(N):
            n = i + 1
            if n <= N1:
                mu_n, var_n = n * mu_pre, n * var_pre
            elif N1 == 0:
                mu_n, var_n = n * mu_post, n * var_post
            else:
                mu_n = N1 * mu_pre + (n - N1) * mu_post
                var_n = N1 * var_pre + (n - N1) * var_post
            std_n = np.sqrt(max(var_n, 0.0))
            for a in alphas:
                lo = max(0.0, norm.ppf(a, mu_n, std_n))
                hi = float(norm.ppf(1 - a, mu_n, std_n))
                result[a].append((lo, hi))
        return result

    return solver_clt
