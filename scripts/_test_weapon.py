"""Smoke test for weapon module."""
from genshin_wish.weapon import (
    WeaponState, WeaponTarget, weapon_target_weights, weapon_up_distribution,
)

# Test weights
target = WeaponTarget(count_a=1, count_b=0)
w = weapon_target_weights(target)
print(f"Weights for 1A: {w}")
assert abs(sum(w.values()) - 1.0) < 1e-10
assert abs(w[1] - 0.375) < 1e-10
assert abs(w[2] - 0.625) < 1e-10

# Test weights with epitomized_points=1
w1 = weapon_target_weights(target, epitomized_points=1)
print(f"Weights for 1A (ep=1): {w1}")
assert abs(w1[1] - 1.0) < 1e-10

# Test weights with prev_standard
ws = weapon_target_weights(target, prev_standard=True)
print(f"Weights for 1A (prev_std): {ws}")
assert abs(ws[1] - 0.5) < 1e-10
assert abs(ws[2] - 0.5) < 1e-10

# Test distribution
state = WeaponState(pity=0, epitomized_points=0)
d = weapon_up_distribution(state, target)
print(f"1A (clean): expected={d.expected:.2f}")
assert abs(d.pdf.sum() - 1.0) < 1e-8

# Two copies
target2 = WeaponTarget(count_a=2)
state2 = WeaponState(pity=0, epitomized_points=0)
d2 = weapon_up_distribution(state2, target2)
print(f"2A (clean): expected={d2.expected:.2f}")

# With pity
state_pity = WeaponState(pity=50, epitomized_points=0)
d_pity = weapon_up_distribution(state_pity, target)
print(f"1A (pity=50): expected={d_pity.expected:.2f}")

print("\nWeapon tests passed!")
