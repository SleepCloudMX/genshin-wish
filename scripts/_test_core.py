"""Quick smoke test for core modules."""
from genshin_wish._constants import CHARACTER_POOL, STABLE_P
from genshin_wish._capture_radiance import guarantee_seq
from genshin_wish._gold import build_gold_pdf, get_gold_pdfs
from genshin_wish.character import CharacterState, up_distribution, stable_up_distribution

# Test gold PDF
pdf = build_gold_pdf(CHARACTER_POOL)
assert len(pdf) == 91, f"Expected 91, got {len(pdf)}"
assert pdf[0] == 0.0
assert pdf[1] == 0.006
assert pdf[90] == 1.0

pdfs = get_gold_pdfs(CHARACTER_POOL)
exp = sum(i * p for i, p in enumerate(pdfs[1]))
print(f"Single gold expected pulls: {exp:.2f} (target: ~62.5)")
assert 60 < exp < 65, f"Expected ~62.5, got {exp:.2f}"

# Test guarantee_seq
seq = guarantee_seq(0, 2)
total_p = sum(p for _, (_, p) in seq.items())
assert abs(total_p - 1.0) < 1e-10, f"Sum should be 1.0, got {total_p}"

# Test character
state = CharacterState(guaranteed=False, pity=0, consecutive_loss=0)
d = up_distribution(state, 1)
assert abs(d.pdf.sum() - 1.0) < 1e-8, f"PDF sum: {d.pdf.sum()}"
print(f"n_up=1 (clean): expected={d.expected:.2f}")

# Bug 1 fix: guaranteed True, n_up=1
state_g = CharacterState(guaranteed=True, pity=0, consecutive_loss=0)
d_g = up_distribution(state_g, 1)
assert abs(d_g.pdf.sum() - 1.0) < 1e-8
print(f"n_up=1 (guaranteed): expected={d_g.expected:.2f}")

# n_up=7
d7 = up_distribution(state, 7)
print(f"n_up=7: expected={d7.expected:.2f}, median={d7.quantile(0.5)}")

# stable
ds = stable_up_distribution(7)
print(f"stable n_up=7: expected={ds.expected:.2f}, median={ds.quantile(0.5)}")

# n_up=0
d0 = up_distribution(state, 0)
assert len(d0.pdf) == 1 and d0.pdf[0] == 1.0

print("\nAll core tests passed!")
