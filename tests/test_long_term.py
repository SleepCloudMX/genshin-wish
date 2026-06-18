"""Verify _solve_exact (iterative convolution) matches up_distribution (brute-force enumeration)."""

import numpy as np
import pytest

from genshin_wish._constants import CHARACTER_POOL, CAPTURE_RADIANCE_WIN_RATE
from genshin_wish._gold import get_gold_pdfs
from genshin_wish.character import CharacterState, up_distribution
from genshin_wish.long_term import _solve_exact


@pytest.fixture(scope="module")
def _gold() -> tuple[np.ndarray, np.ndarray]:
    pdfs = get_gold_pdfs(CHARACTER_POOL)
    return pdfs[1], np.convolve(pdfs[1], pdfs[1])


@pytest.mark.parametrize("k_miss", [0, 1, 2, 3])
@pytest.mark.parametrize("n_up", [1, 2, 3, 4, 5, 6, 7])
def test_exact_vs_enumeration(
    _gold: tuple[np.ndarray, np.ndarray], k_miss: int, n_up: int
) -> None:
    p_gold, p_gold2 = _gold
    p_up = list(CAPTURE_RADIANCE_WIN_RATE)

    # Iterative convolution (long-term solver, start from k_miss)
    results = _solve_exact(n_up, p_up, p_gold, p_gold2, start_state=k_miss)
    pdf_iter = results[n_up]
    expected_iter = float(np.sum(np.arange(len(pdf_iter)) * pdf_iter))

    # Brute-force enumeration (character.up_distribution)
    state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k_miss)
    dist = up_distribution(state, n_up)
    expected_enum = dist.expected

    # Expected value should match within 1e-4 relative
    assert expected_iter == pytest.approx(expected_enum, rel=1e-4), (
        f"k_miss={k_miss}, n_up={n_up}: "
        f"iter={expected_iter:.4f} vs enum={expected_enum:.4f}"
    )

    # Full distribution comparison: quantiles at key percentiles
    cdf_iter = np.cumsum(pdf_iter)
    for q in [0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99]:
        qi_iter = int(np.searchsorted(cdf_iter, q))
        qi_enum = dist.quantile(q)
        assert qi_iter == qi_enum, (
            f"k_miss={k_miss}, n_up={n_up}, q={q}: "
            f"iter={qi_iter} vs enum={qi_enum}"
        )
