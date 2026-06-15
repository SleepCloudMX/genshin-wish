"""Joint distribution: character + weapon banner combined."""

from dataclasses import dataclass

import numpy as np

from .character import CharacterState, UpDistribution, up_distribution
from .weapon import WeaponState, WeaponTarget, WeaponUpDistribution, weapon_up_distribution


@dataclass
class JointDistribution:
    """Distribution of total pulls for a character target AND a weapon target.

    The two banners are independent, so the total-pull PDF is the
    convolution of the two marginal PDFs.
    """

    pdf: np.ndarray
    cdf: np.ndarray
    char: UpDistribution | None = None
    weapon: WeaponUpDistribution | None = None

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


def joint_distribution(
    char_state: CharacterState,
    char_n_up: int,
    weapon_state: WeaponState,
    weapon_target: WeaponTarget,
) -> JointDistribution:
    """Distribution of total pulls needed for both character and weapon targets.

    Character and weapon banners are independent — the total-pull PDF is
    the convolution of the two marginal PDFs.
    """
    char = up_distribution(char_state, char_n_up)
    weapon = weapon_up_distribution(weapon_state, weapon_target)
    joint_pdf = np.convolve(char.pdf, weapon.pdf)
    joint_cdf = np.cumsum(joint_pdf)
    return JointDistribution(pdf=joint_pdf, cdf=joint_cdf, char=char, weapon=weapon)
