"""Regression tests: compare new genshin_wish results against ref/."""
import sys
import numpy as np
import pytest

# Import ref/ (add to path)
sys.path.insert(0, "ref/character")
from gold2rolls import character_up2rolls, query_luck_percentile


def _ref_percentile(k_miss, n_up, pulls):
    return query_luck_percentile(k_miss, n_up, pulls)


def _ref_full_dist(guaranteed, pity, k_miss, n_up, pulls):
    pdf = character_up2rolls(guaranteed, pity, k_miss, n_up)
    cdf = np.cumsum(pdf)
    expected = sum(i * p for i, p in enumerate(pdf))
    return expected, float(cdf[pulls])


def _new_percentile(k_miss, n_up, pulls):
    from genshin_wish.character import CharacterState, up_distribution, stable_up_distribution
    if k_miss is None:
        dist = stable_up_distribution(n_up)
    else:
        state = CharacterState(guaranteed=False, pity=0, consecutive_loss=k_miss)
        dist = up_distribution(state, n_up)
    return dist.luck(pulls)


def _new_full_dist(guaranteed, pity, k_miss, n_up, pulls):
    from genshin_wish.character import CharacterState, up_distribution
    state = CharacterState(guaranteed=guaranteed, pity=pity, consecutive_loss=k_miss)
    dist = up_distribution(state, n_up)
    return dist.expected, dist.probability(pulls)


# --- n_up ≤ 7 exact tests ---

@pytest.mark.parametrize("k_miss,n_up,pulls", [
    (1, 3, 384),
    (0, 7, 733),
    (None, 7, 733),
    (2, 7, 733),
    (3, 7, 733),
])
def test_percentile_exact(k_miss, n_up, pulls):
    ref = _ref_percentile(k_miss, n_up, pulls)
    new = _new_percentile(k_miss, n_up, pulls)
    assert abs(ref - new) < 1e-6, f"k_miss={k_miss}, n_up={n_up}, pulls={pulls}: ref={ref}, new={new}"


@pytest.mark.parametrize("guaranteed,pity,k_miss,n_up,pulls", [
    (False, 32, 0, 2, 244),
    (False, 32, 0, 3, 244),
    (False, 32, 0, 4, 244),
])
def test_full_dist_exact(guaranteed, pity, k_miss, n_up, pulls):
    ref_exp, ref_prob = _ref_full_dist(guaranteed, pity, k_miss, n_up, pulls)
    new_exp, new_prob = _new_full_dist(guaranteed, pity, k_miss, n_up, pulls)
    assert abs(ref_exp - new_exp) < 0.01, f"E diff: ref={ref_exp:.2f}, new={new_exp:.2f}"
    assert abs(ref_prob - new_prob) < 1e-6, f"P diff: ref={ref_prob:.6f}, new={new_prob:.6f}"


@pytest.mark.parametrize("k", range(1, 6))
def test_stable_c6_percentiles(k):
    pulls = k * 100
    ref = _ref_percentile(None, 7, pulls)
    new = _new_percentile(None, 7, pulls)
    assert abs(ref - new) < 1e-6, f"pulls={pulls}: ref={ref}, new={new}"


def test_guaranteed_n1_bug_fixed():
    """Bug 1: guaranteed=True, n_up=1 should work and give correct expected."""
    from genshin_wish.character import CharacterState, up_distribution
    state = CharacterState(guaranteed=True, pity=0, consecutive_loss=0)
    dist = up_distribution(state, 1)
    assert 60 < dist.expected < 65, f"Expected ~62.3, got {dist.expected:.1f}"
    assert abs(dist.pdf.sum() - 1.0) < 1e-8
