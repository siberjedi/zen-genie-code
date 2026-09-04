"""
Power =0.80 kontrolü — PROTOCOL phase_05 power_target (değişmedi)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from src.backtest.evaluate import compute_power, cohens_d

def test_power_target():
    # PROTOCOL: required_effect_size d >=0.30, power 0.80, alpha 0.05
    # n=176 per group (352 total) → power ~0.80
    p = compute_power(0.30, 176, alpha=0.05)
    print(f"power d=0.30 n=176 -> {p:.4f}")
    assert 0.79 < p < 0.82, f"power {p} != 0.80"
    # d=0.30 n=100 → power ~0.53
    p2 = compute_power(0.30, 100)
    assert p2 < 0.80, "n=100 should be underpowered"
    # cohens_d sanity
    d = cohens_d([1,2,3,4],[1,2,3,4])
    assert abs(d) < 1e-9
    d2 = cohens_d([1,2,3],[5,6,7])
    assert d2 < 0
    print("PASS power 0.80")

if __name__ == "__main__":
    test_power_target()
