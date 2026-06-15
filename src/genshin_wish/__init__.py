"""genshin-wish — Genshin Impact gacha probability calculator.

Usage::

    from genshin_wish import CharacterState, up_distribution

    state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
    dist = up_distribution(state, n_up=7)
    print(f"Expected pulls for C6: {dist.expected:.0f}")
    print(f"Median: {dist.quantile(0.5)}")
"""

from genshin_wish._constants import PoolConfig, CHARACTER_POOL, WEAPON_POOL, STABLE_P
from genshin_wish.character import CharacterState, UpDistribution, up_distribution, stable_up_distribution
from genshin_wish.standard import StandardState, standard_distribution
from genshin_wish.weapon import WeaponState, WeaponTarget, WeaponUpDistribution, weapon_up_distribution
from genshin_wish.joint import JointDistribution, joint_distribution

__all__ = [
    "PoolConfig",
    "CHARACTER_POOL",
    "WEAPON_POOL",
    "STABLE_P",
    "CharacterState",
    "UpDistribution",
    "up_distribution",
    "stable_up_distribution",
    "StandardState",
    "standard_distribution",
    "WeaponState",
    "WeaponTarget",
    "WeaponUpDistribution",
    "weapon_up_distribution",
    "JointDistribution",
    "joint_distribution",
]
