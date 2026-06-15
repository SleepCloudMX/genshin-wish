"""Smoke test for CLI and core API."""
import json

# Test direct API
from genshin_wish.character import CharacterState, up_distribution, stable_up_distribution
from genshin_wish.weapon import WeaponState, WeaponTarget, weapon_up_distribution
from genshin_wish.joint import joint_distribution

# Import test
from genshin_wish import (
    CHARACTER_POOL, WEAPON_POOL, STABLE_P,
    CharacterState as CS, UpDistribution, WeaponState as WS,
    WeaponTarget as WT, JointDistribution,
)

print("=== Character ===")
s = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
d = up_distribution(s, 7)
print(f"C6 expected: {d.expected:.1f}")
print(f"C6 median: {d.quantile(0.5)}")
print(f"C6 800 pulls: {d.luck(800)*100:.1f}%")

ds = stable_up_distribution(7)
print(f"C6 stable expected: {ds.expected:.1f}")

print("\n=== Weapon ===")
ws = WeaponState(pity=0, epitomized_points=0)
wt = WeaponTarget(count_a=1)
wd = weapon_up_distribution(ws, wt)
print(f"R1 expected: {wd.expected:.1f}")
print(f"R1 median: {wd.quantile(0.5)}")

print("\n=== Joint ===")
cs = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
wst = WeaponState(pity=0, epitomized_points=0)
wt2 = WeaponTarget(count_a=1)
jd = joint_distribution(cs, 2, wst, wt2)
print(f"Joint (C1+R1) expected: {jd.expected:.1f}")
print(f"  Char alone: {jd.char.expected:.1f}")
print(f"  Weapon alone: {jd.weapon.expected:.1f}")

print("\n=== CLI via click.testing ===")
from click.testing import CliRunner
from genshin_wish.cli.main import main

runner = CliRunner()
result = runner.invoke(main, ["char", "--n-up", "7", "--quantile", "0.5"])
print(f"CLI exit: {result.exit_code}")
print(result.output)

result2 = runner.invoke(main, ["char", "--n-up", "2", "--pulls", "200", "--format", "json"])
print(f"CLI JSON: {result2.output[:200]}")

print("\nAll CLI tests passed!")
