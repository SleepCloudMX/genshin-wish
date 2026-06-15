"""Tests for weapon banner probability."""
from genshin_wish.weapon import (
    WeaponState,
    WeaponTarget,
    weapon_target_weights,
    weapon_up_distribution,
)


def test_single_copy_weights_clean():
    w = weapon_target_weights(WeaponTarget(count_a=1))
    assert abs(sum(w.values()) - 1.0) < 1e-10
    assert abs(w[1] - 0.375) < 1e-10
    assert abs(w[2] - 0.625) < 1e-10


def test_single_copy_weights_epitomized():
    w = weapon_target_weights(WeaponTarget(count_a=1), epitomized_points=1)
    assert abs(w[1] - 1.0) < 1e-10


def test_single_copy_weights_prev_std():
    w = weapon_target_weights(WeaponTarget(count_a=1), prev_standard=True)
    assert abs(w[1] - 0.5) < 1e-10
    assert abs(w[2] - 0.5) < 1e-10


def test_two_copies_weights():
    w = weapon_target_weights(WeaponTarget(count_a=2))
    # {2: 0.375^2, 3: 2*0.375*0.625, 4: 0.625^2}
    assert abs(w[2] - 0.140625) < 1e-10
    assert abs(w[3] - 0.46875) < 1e-10
    assert abs(w[4] - 0.390625) < 1e-10


def test_epitomized_resets_per_copy():
    """After obtaining a copy, epitomized_path resets."""
    w = weapon_target_weights(WeaponTarget(count_a=2), epitomized_points=1)
    # First copy is guaranteed (1 gold), second is normal
    # Total: {1+1=2: 0.375, 1+2=3: 0.625}
    assert abs(sum(w.values()) - 1.0) < 1e-10
    assert abs(w[2] - 0.375) < 1e-10
    assert abs(w[3] - 0.625) < 1e-10


def test_distribution_pdf_sums_to_one():
    state = WeaponState(pity=0)
    d = weapon_up_distribution(state, WeaponTarget(count_a=1))
    assert abs(d.pdf.sum() - 1.0) < 1e-8


def test_distribution_with_pity():
    state0 = WeaponState(pity=0)
    state_p = WeaponState(pity=50)
    d0 = weapon_up_distribution(state0, WeaponTarget(count_a=1))
    dp = weapon_up_distribution(state_p, WeaponTarget(count_a=1))
    # With pity, expected pulls should be lower
    assert dp.expected < d0.expected


def test_count_b_raises():
    try:
        WeaponTarget(count_a=1, count_b=1)
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass
