"""Faz 3 — Pipeline orkestrasyonu (readiness; tam deney KOŞULMADI).

Akış: OHLCV -> Features -> Label -> Train -> Validation -> Signal -> Backtest -> OOS eval.
- Backtest/OOS adımları deney aşamasında çalışır (şimdi değil).
- `smoke()`: sentetik veriyle uçtan-uca akış kanıtı; gerçek veri yok,
  seçim yok, Final Test A yok.

Trade simülasyonu (deneyde kullanılacak, kilitli tanım):
- Sinyal 1 ve flat -> long aç; sinyal 0 -> kapat.
- ROI %2 / SL -%10 (Baseline ile aynı ekonomi, adil karşılaştırma).
- Maliyet: fee_taker 0.001 x2, slippage 5bps varsayımı (Madde 12).
"""
import pandas as pd

from .features import build_features, FEATURES
from .labels import build_dataset
from .splits import split_train_val, assert_no_final_leak, SEEDS, N_FOLDS
from .model import make_model, predict_proba, proba_to_signal

ROI = 0.02
STOPLOSS = -0.10


def run_fold_seed(X_train, y_train, X_val, seed: int) -> dict:
    """Tek (fold, seed) koşumu: eğit -> validation sinyalleri."""
    model = make_model(seed)
    model.fit(X_train, y_train)
    probas = predict_proba(model, X_val)
    signals = proba_to_signal(probas)
    return {"seed": seed, "probas": probas, "signals": signals,
            "n_train": len(X_train), "n_val": len(X_val)}


def smoke(n_rows: int = 600, seed: int = 42) -> dict:
    """Sentetik uçtan-uca duman testi (gerçek veri yok)."""
    import numpy as np
    rng = np.random.default_rng(0)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n_rows)))
    df = pd.DataFrame({
        "date": pd.date_range("2021-01-01", periods=n_rows, freq="5min"),
        "open": close, "high": close * 1.002,
        "low": close * 0.998, "close": close,
        "volume": rng.uniform(10, 100, n_rows),
    })
    data = build_dataset(df)
    X = data[FEATURES].values
    y = data["label"].values.astype(int)
    out = run_fold_seed(X, y, X, seed)
    out.update({"n_rows": n_rows, "n_kept": len(data),
                "label_rate": float(data["label"].mean())})
    return out
