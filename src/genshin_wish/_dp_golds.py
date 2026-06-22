"""DP over (gold_count, n_std) counts — 方案4 (dp-golds)."""

from collections import defaultdict

import numpy as np

from ._constants import CAPTURE_RADIANCE_WIN_RATE, CHARACTER_POOL
from ._gold import get_gold_pdfs
from .character import UpDistribution


def _dp_golds_task1(n_uncertain: int, k_miss_start: int) -> dict[int, float]:
    """DP for {gold: prob}, marginalised over n_std.

    Complexity O(n²).  Each step tracks 4 k_miss states × O(i) gold values.
    """
    p_up = CAPTURE_RADIANCE_WIN_RATE
    state: dict[int, dict[int, float]] = {k_miss_start: {0: 1.0}}

    for _ in range(n_uncertain):
        new: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        for k, dist in state.items():
            pw = p_up[k]
            # Win: gold+1, k→0
            for gold, prob in dist.items():
                new[0][gold + 1] += prob * pw
            # Loss: gold+2, k→k+1 (k<3 only)
            if k < 3:
                pl = 1.0 - pw
                for gold, prob in dist.items():
                    new[k + 1][gold + 2] += prob * pl
        state = new

    result: dict[int, float] = defaultdict(float)
    for dist in state.values():
        for gold, prob in dist.items():
            result[gold] += prob
    return dict(result)


def _dp_golds_full(
    n_uncertain: int, k_miss_start: int
) -> dict[tuple[int, int], float]:
    """DP for {(gold, n_std): prob} — joint distribution of gold and standard counts.

    Complexity O(n²).  Each step tracks 4 k_miss states × O(i²) (gold, n_std) pairs.
    """
    p_up = CAPTURE_RADIANCE_WIN_RATE
    state: dict[int, dict[tuple[int, int], float]] = {
        k_miss_start: {(0, 0): 1.0}
    }

    for _ in range(n_uncertain):
        new: dict[int, dict[tuple[int, int], float]] = defaultdict(
            lambda: defaultdict(float)
        )
        for k, dist in state.items():
            pw = p_up[k]
            # Win: gold+1, n_std unchanged, k→0
            for (gold, ns), prob in dist.items():
                new[0][(gold + 1, ns)] += prob * pw
            # Loss: gold+2, n_std+1, k→k+1
            if k < 3:
                pl = 1.0 - pw
                for (gold, ns), prob in dist.items():
                    new[k + 1][(gold + 2, ns + 1)] += prob * pl
        state = new

    result: dict[tuple[int, int], float] = defaultdict(float)
    for dist in state.values():
        for key, prob in dist.items():
            result[key] += prob
    return dict(result)


def golds_to_pulls(
    gold_probs: dict[int, float],
    pdfs: list[np.ndarray] | None = None,
) -> UpDistribution:
    """Task 1: convert {gold: prob} to UpDistribution."""
    if pdfs is None:
        max_gold = max(gold_probs.keys())
        pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=max_gold)
    max_gold = max(gold_probs.keys())
    result = np.zeros(len(pdfs[max_gold]), dtype=np.float64)
    for gold, prob in gold_probs.items():
        if prob > 0 and gold > 0:
            result[: len(pdfs[gold])] += pdfs[gold] * prob
    cdf = np.cumsum(result)
    return UpDistribution(pdf=result, cdf=cdf)


def golds_nstd_to_pulls(
    dist: dict[tuple[int, int], float],
    pdfs: list[np.ndarray] | None = None,
) -> dict[int, UpDistribution]:
    """Task 2: convert {(gold, n_std): prob} to {n_std: UpDistribution}.

    Each n_std gets the conditional pulls distribution P(pulls | n_std).
    """
    if pdfs is None:
        all_golds = {g for g, _ in dist}
        pdfs = get_gold_pdfs(CHARACTER_POOL, min_gold=max(all_golds))

    # Group by n_std
    nstd_golds: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    nstd_total: dict[int, float] = defaultdict(float)
    for (gold, ns), prob in dist.items():
        if prob > 0:
            nstd_golds[ns][gold] += prob
            nstd_total[ns] += prob

    result: dict[int, UpDistribution] = {}
    for ns, gold_probs in nstd_golds.items():
        total = nstd_total[ns]
        max_gold = max(gold_probs.keys())
        pdf_arr = np.zeros(len(pdfs[max_gold]), dtype=np.float64)
        for gold, prob in gold_probs.items():
            if gold > 0:
                pdf_arr[: len(pdfs[gold])] += pdfs[gold] * (prob / total)
        cdf = np.cumsum(pdf_arr)
        result[ns] = UpDistribution(pdf=pdf_arr, cdf=cdf)

    return dict(result)


def golds_nstd_to_nstd_dist(
    dist: dict[tuple[int, int], float],
) -> dict[int, float]:
    """Task 3: marginalise {(gold, n_std): prob} → {n_std: prob}."""
    result: dict[int, float] = defaultdict(float)
    for (gold, ns), prob in dist.items():
        result[ns] += prob
    return dict(result)
