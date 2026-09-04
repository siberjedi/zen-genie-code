"""Faz 3 readiness validasyonu — pipeline KURULU, deney KOŞULMADI, Final Test A YOK.

Kapsam: feature/label leakage, NaN, split+guard, seed reproducibility,
final_test_A guard (gerçek veri, salt-okunur), metrik entegrasyonu, CV fold yapısı.
"""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

import numpy as np
import pandas as pd

from src.freqai.features import build_features, FEATURES, WARMUP_ROWS
from src.freqai.labels import (build_labels, build_dataset, LABEL_HORIZON,
                               LABEL_THRESHOLD, expected_dropped)
from src.freqai.splits import (split_train_val, assert_no_final_leak,
                               calendar_folds, FinalTestLeakError,
                               TRAIN_START, TRAIN_END, VAL_START, VAL_END,
                               FINAL_A_START, N_FOLDS, SEEDS)
from src.freqai.model import make_model, predict_proba, HYPERPARAMS, MODEL_NAME
from src.freqai.pipeline import smoke
from src.freqai.compare import sharpe_delta, check_thresholds


def _synth(n=600, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    return pd.DataFrame({
        "date": pd.date_range("2021-01-01", periods=n, freq="5min"),
        "open": close, "high": close * 1.002, "low": close * 0.998,
        "close": close, "volume": rng.uniform(10, 100, n),
    })


def test_feature_leakage():
    df = _synth(600)
    full = build_features(df)
    trunc = build_features(df.iloc[:400])
    a = full.iloc[:400].dropna()
    b = trunc.dropna()
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
    print(f"PASS feature leakage yok (400 satir kesme, {len(b)} karsilastirildi)")


def test_label_definition():
    df = _synth(600)
    lab = build_labels(df)
    close = df["close"].values
    for t in [0, 50, 300, 587]:
        expect = 1.0 if close[t + LABEL_HORIZON] / close[t] - 1 > LABEL_THRESHOLD else 0.0
        assert lab.iloc[t] == expect, f"satir {t}"
    assert lab.iloc[-LABEL_HORIZON:].isna().all(), "son 12 satir NaN olmali"
    f1 = build_features(df)
    f2 = build_dataset(df)[FEATURES]
    # dataset ek olarak son H satiri atar (label kuyrugu) — geri kalan aynidir
    pd.testing.assert_frame_equal(
        f1.iloc[:-LABEL_HORIZON].dropna().reset_index(drop=True),
        f2.reset_index(drop=True), check_dtype=False)
    print(f"PASS label tanimi (H={LABEL_HORIZON}, thr={LABEL_THRESHOLD}), feature'lar etkilenmiyor")


def test_nan_handling():
    n = 500
    data = build_dataset(_synth(n))
    assert not data.isna().any().any(), "NaN kalmamali"
    assert len(data) == n - expected_dropped(n), f"{len(data)} != {n - expected_dropped(n)}"
    assert expected_dropped(n) == WARMUP_ROWS + LABEL_HORIZON == 211
    print(f"PASS NaN: {n} -> {len(data)} (atilan {expected_dropped(n)} = warmup 199 + kuyruk 12)")


def test_split_and_guard():
    dates = pd.date_range("2020-01-01", "2023-06-30", freq="D")
    df = pd.DataFrame({"date": dates, "v": range(len(dates))})
    train, val = split_train_val(df)
    assert train["date"].max() <= TRAIN_END and val["date"].min() >= VAL_START
    assert val["date"].max() <= VAL_END
    assert len(train) == 1096 and len(val) == 181, f"{len(train)}/{len(val)}"
    bad = pd.DataFrame({"date": pd.date_range("2023-07-01", periods=5, freq="D")})
    try:
        split_train_val(pd.concat([df, bad], ignore_index=True))
        raise SystemExit("guard yakalamaliydi")
    except FinalTestLeakError:
        pass
    try:
        assert_no_final_leak(bad["date"], "test")
        raise SystemExit("guard yakalamaliydi")
    except FinalTestLeakError:
        pass
    print("PASS split (train 1096 / val 181) + guard ABORT (final_A reddedildi)")


def test_seed_reproducibility():
    df = _synth(500)
    data = build_dataset(df)
    X, y = data[FEATURES].values, data["label"].values.astype(int)
    p1 = predict_proba(make_model(42).fit(X, y), X)
    p2 = predict_proba(make_model(42).fit(X, y), X)
    assert p1 == p2, "ayni seed farkli sonuc veremez"
    p3 = predict_proba(make_model(7).fit(X, y), X)
    assert len(p3) == len(p1) and all(0 <= p <= 1 for p in p1 + p3)
    assert make_model(42).get_params()["n_estimators"] == HYPERPARAMS["n_estimators"] == 200
    print(f"PASS seed reproducibility ({MODEL_NAME}, 5 seed: {SEEDS})")


def test_final_a_guard_real_data():
    root = pathlib.Path(__file__).parents[1]
    ddir = root / "freqtrade" / "user_data" / "data" / "binance"
    files = sorted(ddir.glob("*-5m.feather"))
    assert len(files) == 30, f"30 feather bekleniyor, {len(files)}"
    worst, worst_f, empty = None, "", []
    for f in files:
        col = pd.read_feather(f, columns=["date"])["date"]
        col = pd.to_datetime(col).dropna()
        if len(col) == 0:
            empty.append(f.name)  # tarihsiz pair'ler (2023 öncesi yok) — beklenen 12
            continue
        mx = pd.Timestamp(col.max())
        if mx.tzinfo is not None:
            mx = mx.tz_localize(None)
        if worst is None or mx > worst:
            worst, worst_f = mx, f.name
        assert mx < FINAL_A_START, f"{f.name}: {mx} FINAL_A'ya giriyor!"
    assert len(empty) == 12, f"12 bos dosya bekleniyor, {len(empty)}: {empty}"
    print(f"PASS final_test_A guard: 18/18 veri dosyasi < 2023-07-01 "
          f"(en son {worst_f} {worst}); 12 bos dosya (tarihsiz, deney disi)")


def test_metric_integration():
    import tempfile, os
    from src.backtest.evaluate import (evaluate_trades, fdr_correct, cohens_d,
                                       compute_power)
    rng = np.random.default_rng(3)
    n = 60
    df = pd.DataFrame({
        "profit_ratio": rng.normal(0.001, 0.02, n),
        "close_date": pd.date_range("2023-01-01", periods=n, freq="D"),
    })
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "tr.csv")
        df.to_csv(p, index=False)
        res = evaluate_trades(p)
    assert res.get("method") == "daily_365", res
    for k in ["sharpe", "sortino", "max_dd", "profit_factor", "n_trades"]:
        assert k in res, k
    rej, pc = fdr_correct([0.01, 0.2, 0.04, 0.5, 0.03])
    assert len(rej) == 5 and len(pc) == 5
    assert abs(compute_power(0.30, 176) - 0.80) < 0.02
    assert abs(cohens_d([1, 2, 3], [1, 2, 3])) < 1e-9
    assert sharpe_delta(0.5, -1.8) > 0.30
    ok = check_thresholds(0.5, 0.8, 0.1, 0.1)
    assert ok["checks"]["ALL_PASS"] is True
    bad = check_thresholds(-2.0, 0.1, 0.9, 0.9)
    assert bad["checks"]["ALL_PASS"] is False
    print("PASS metrik entegrasyonu (daily_365 + FDR/d/power + esik kontrolu, esikler degismedi)")


def test_cv_folds():
    folds = calendar_folds()
    assert len(folds) == N_FOLDS == 5
    assert (folds["train_start"] == str(TRAIN_START.date())).all(), "expanding: sabit baslangic"
    assert folds["train_end"].is_monotonic_increasing
    assert (pd.to_datetime(folds["test_end"]) < FINAL_A_START).all()
    assert folds["test_start"].iloc[0] > folds["train_start"].iloc[0]
    print(f"PASS CV fold yapisi (5 expanding, train-ici, final_A disi)\n{folds.to_string(index=False)}")


def test_smoke():
    out = smoke()
    assert out["n_kept"] == out["n_rows"] - expected_dropped(out["n_rows"])
    assert len(out["signals"]) == out["n_val"] > 0
    assert set(out["signals"]) <= {0, 1}
    print(f"PASS smoke (uçtan-uca, sentetik, secim yok): {out['n_kept']} satir")


if __name__ == "__main__":
    test_feature_leakage()
    test_label_definition()
    test_nan_handling()
    test_split_and_guard()
    test_seed_reproducibility()
    test_final_a_guard_real_data()
    test_metric_integration()
    test_cv_folds()
    test_smoke()
    print("ALL PASS — pipeline kurulu, deney kosulmadi, Final Test A'ya dokunulmadi")
