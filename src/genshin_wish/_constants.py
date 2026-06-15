"""Pool configuration and probability constants."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PoolConfig:
    """Gacha pool probability parameters.

    soft_pity_start is the 1-indexed pull where probability first exceeds base_rate.
    E.g. character: pulls 1~73 are constant, soft pity starts at pull 74.
    """

    base_rate: float
    soft_pity_start: int
    hard_pity: int
    soft_pity_step: float
    soft_pity_start2: int | None = None
    soft_pity_step2: float | None = None
    max_gold_cache: int = 13


CHARACTER_POOL = PoolConfig(
    base_rate=0.006,
    soft_pity_start=74,
    hard_pity=90,
    soft_pity_step=0.06,
)

WEAPON_POOL = PoolConfig(
    base_rate=0.007,
    soft_pity_start=63,
    hard_pity=80,
    soft_pity_step=0.07,
    soft_pity_start2=74,
    soft_pity_step2=0.035,
    max_gold_cache=10,
)

# Steady-state distribution of consecutive_loss (k_miss = 0,1,2,3)
# Derived from guarantee_seq transition matrix:
#   p0=0.550404, p1=0.274707, p2=0.124167, p3=0.0507224
STABLE_P: list[float] = [0.550404, 0.274707, 0.124167, 0.0507224]

# Effective win rate at each consecutive_loss level
# p_up[k] = 0.5 + 0.5 * capture_radiance[k]
CAPTURE_RADIANCE_WIN_RATE: list[float] = [0.50009, 0.54800, 0.59150, 1.0]

# Threshold: use CLT when n_up > CLT_THRESHOLD
CLT_THRESHOLD: int = 7
