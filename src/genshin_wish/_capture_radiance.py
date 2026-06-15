"""Capture Radiance mechanism: enumerate win/loss sequences for n_up UPs."""

from ._constants import CAPTURE_RADIANCE_WIN_RATE


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
