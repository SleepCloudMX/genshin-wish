"""Capture Radiance mechanism: enumerate win/loss sequences for n_up UPs."""

from collections import defaultdict

from ._constants import CAPTURE_RADIANCE_WIN_RATE


def radiance_dist_from_seq(seq: list[int]) -> dict[int, float]:
    """Poisson-binomial: given a win/loss sequence, compute P(radiance count = r).

    Args:
        seq: List of 1 (win) / 2 (loss) outcomes.

    Returns:
        ``{radiance_count: probability}``.
    """
    p_up = CAPTURE_RADIANCE_WIN_RATE
    k = 0
    probs: list[float] = []
    for outcome in seq:
        if outcome == 1:  # win
            pk = p_up[k]
            if pk > 0.5:
                probs.append((pk - 0.5) / pk)
            k = 0
        else:  # loss
            if k < 3:
                k += 1

    dp: dict[int, float] = {0: 1.0}
    for p in probs:
        new: dict[int, float] = defaultdict(float)
        for r, prob in dp.items():
            new[r] += prob * (1 - p)
            new[r + 1] += prob * p
        dp = new
    return dict(dp)


def radiance_dist_from_n_up(n_up: int, k_miss: int = 0) -> dict[int, float]:
    """3-D DP: distribution of radiance trigger count for *n_up* UPs from *k_miss*.

    Complexity O(n_up²).
    """
    p_up = CAPTURE_RADIANCE_WIN_RATE
    dp: dict[tuple[int, int], float] = {(k_miss, 0): 1.0}

    for _ in range(n_up):
        new: dict[tuple[int, int], float] = defaultdict(float)
        for (k, r), prob in dp.items():
            pk = p_up[k]
            new[(0, r)] += prob * 0.5          # win via 50/50
            new[(0, r + 1)] += prob * (pk - 0.5)  # win via radiance
            if k < 3:
                new[(k + 1, r)] += prob * (1 - pk)  # loss
        dp = new

    result: dict[int, float] = defaultdict(float)
    for (k, r), prob in dp.items():
        result[r] += prob
    total = sum(result.values())
    return {r: p / total for r, p in result.items()}


def guarantee_seq(
    k_miss: int, n_up: int
) -> dict[tuple[int, ...], tuple[int, float]]:
    """Enumerate all win/loss sequences for *n_up* uncertain UPs and their probabilities.

    A *win* (1) means the 50/50 was won (or captured by radiance) — costs 1 gold.
    A *loss* (2) means the 50/50 was lost — the guaranteed UP follows, costing 2 golds.

    Args:
        k_miss: Current consecutive 50/50 losses (0..3).
        n_up:   Number of uncertain UPs to obtain.

    Returns:
        {seq: (final_k_miss, probability)} where seq is a tuple of 1s and 2s.

    Example:
        guarantee_seq(0, 2)
        → {(1,1): (0, 0.25009..), (1,2): (1, 0.25000..), (2,1): (0, 0.27470..), (2,2): (2, 0.22530..)}
    """
    p_up = CAPTURE_RADIANCE_WIN_RATE
    dp: dict[tuple[int, ...], tuple[int, float]] = {(): (k_miss, 1.0)}
    for _ in range(n_up):
        new_dp: dict[tuple[int, ...], tuple[int, float]] = {}
        for seq, (km, p) in dp.items():
            # Win: k_miss resets to 0
            new_dp[seq + (1,)] = (0, p * p_up[km])
            # Loss: k_miss increases (capped at 3)
            if km != 3:
                new_dp[seq + (2,)] = (km + 1, p * (1 - p_up[km]))
        dp = new_dp
    return dp
