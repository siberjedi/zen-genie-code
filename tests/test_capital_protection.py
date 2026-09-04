"""
Regression test for Capital Protection reserve vs theoretical lock.

Bug: reserve was synced directly to locked_profit (HWM based), even when realized_profit == 0,
showing 0.29 USDT as if it was actually reserved, while no profit was realized.

Rule: actual_reserve <= min(locked_profit_theoretical, max(realized_profit,0)*lock_ratio)
When realized==0, actual_reserve must be 0, even if locked_theoretical >0.

Case: core=100, realized=0, equity=100.23, HWM=100.58, lock_ratio=0.5
=> locked_theoretical = (100.58-100)*0.5 = 0.29
=> actual_reserve = min(0.29, 0*0.5) = 0
=> threshold = 100 + 0.29 = 100.29
"""
import sys
sys.path.insert(0, r'C:\Users\ALPI\Desktop\Zen-Genie\src\risk')
import capital, importlib, pathlib, json

def test_regression_realized_zero():
    importlib.reload(capital)
    # Mock DB to return realized 0 and unrealized to make equity 100.23
    orig_real = capital._get_realized_from_db
    orig_unreal = capital._get_unrealized_from_db
    capital._get_realized_from_db = lambda: 0.0
    capital._get_unrealized_from_db = lambda: 0.23  # equity = 100 + 0 + 0.23 = 100.23

    # Set state to simulate HWM 100.58, previous buggy reserve 0.29
    state = capital.load_state()
    state['high_water_mark'] = 100.58
    state['locked_profit'] = 0.29
    state['protection_threshold'] = 100.29
    state['reserve_balance'] = 0.29  # buggy value
    capital.save_state(state)

    v = capital.compute_capital_view()
    print("Test case: core=100, realized=0, equity=100.23, HWM=100.58")
    print(f"  locked_theoretical={v['locked_profit']:.2f} (expected 0.29)")
    print(f"  actual_reserve={v['actual_reserve']:.2f} (expected 0.00)")
    print(f"  threshold={v['protection_threshold']:.2f} (expected 100.29)")
    print(f"  reserve_balance={v['reserve_balance']:.2f} (expected 0.00)")
    print(f"  equity={v['total_equity']:.2f}")

    assert abs(v['locked_profit'] - 0.29) < 1e-6, f"locked {v['locked_profit']} != 0.29"
    assert abs(v['locked_profit_theoretical'] - 0.29) < 1e-6
    assert abs(v['actual_reserve'] - 0.0) < 1e-6, f"actual {v['actual_reserve']} != 0"
    assert abs(v['reserve_balance'] - 0.0) < 1e-6
    assert abs(v['protection_threshold'] - 100.29) < 1e-6
    assert v['realized_profit'] == 0.0

    # Ensure dashboard would not say "0.29 ayrıştırıldı"
    assert v['actual_reserve'] == 0, "Actual reserve must be 0 when realized is 0"
    assert v['locked_profit_theoretical'] == 0.29, "Theoretical should still be 0.29"

    print("REGRESSION PASS: theoretical vs actual correctly separated")

    # Restore
    capital._get_realized_from_db = orig_real
    capital._get_unrealized_from_db = orig_unreal
    # Cleanup state
    for p in [r'C:\Users\ALPI\Desktop\Zen-Genie\data\capital_state.json', r'C:\Users\ALPI\Desktop\Zen-Genie\freqtrade\user_data\capital_state.json']:
        pp = pathlib.Path(p)
        if pp.exists():
            j = json.loads(pp.read_text())
            j['reserve_balance'] = 0
            j['locked_profit'] = 0.29
            j['high_water_mark'] = 100.58
            j['protection_threshold'] = 100.29
            # keep actual 0
            pp.write_text(json.dumps(j, indent=2))
    return True

if __name__ == "__main__":
    test_regression_realized_zero()
