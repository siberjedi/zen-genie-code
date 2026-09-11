"""Phase 5 — Walk-forward (DESIGN 500 sec 13): locked config 365/90/90/90, expanding
false, Phase 2 generate_folds aynı üreteci, aralık 2020-01-01->2023-06-30 (~9 fold).

Akış: kronolojik TRAIN -> sonraki 90 gün VALIDATION (OOF), shuffle YOK.
Aday üzerinde koşulur (seçim-sonrası kanıt). Tutarlılık eşiği: fold'ların >=60%
tanesinde PSS ana-val sonucuyla AYNI YÖNDE ve cost-aware anlamlı (net>0).
Foldlar overlap -> bagimsiz DEGIL (raporlanir).
"""
import numpy as np
import pandas as pd

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.backtest.walk_forward import WFConfig, generate_folds
from src.freqai.p5_splits import VAL_END, check_not_in_protected

WF_MIN_CONSISTENCY = 0.60


def phase5_folds(start="2020-01-01", end="2023-06-30"):
    """Locked config ile foldlari üretir (generate_folds). dtype alanlari ekler."""
    cfg = WFConfig(train_days=365, validation_days=90, test_days=90,
                   step_days=90, expanding=False)
    folds = generate_folds(start, end, cfg)
    for f in folds:
        f["train"] = tuple(pd.Timestamp(t, tz="UTC") for t in f["train"])
        f["validation"] = tuple(pd.Timestamp(t, tz="UTC") for t in f["validation"])
        f["test"] = tuple(pd.Timestamp(t, tz="UTC") for t in f["test"])
    return folds


def overlap_report(folds):
    """Fold indis çiftleri: önceki fold val sonu ile sonraki train basi arasi gap."""
    rows = []
    for i in range(1, len(folds)):
        prev_val_end = folds[i - 1]["validation"][1]
        cur_train_start = folds[i]["train"][0]
        gap = (cur_train_start - prev_val_end).days
        rows.append({"fold": i, "gap_days": int(gap), "overlap": gap < 0})
    return {"folds": len(folds), "overlap_report": rows,
            "n_overlaps": sum(r["overlap"] for r in rows),
            "note": "foldlar overlap -> bagimsiz degil; yon-gostergesi olarak raporlanir"}


def bounds_respected(folds):
    """Tüm fold pencere uçları VAL_END sonrasına TASMAMALI (FINAL_A korunur)."""
    for f in folds:
        for name in ("train", "validation", "test"):
            for t in f[name]:
                ts = pd.Timestamp(t)
                if getattr(ts, "tz", None) is None:
                    ts = ts.tz_localize("UTC")
                if ts > VAL_END:
                    raise AssertionError(f"fold {name} sinirin otesinde: {ts}")
    return True


def fold_slices(fold, frame5, label, block, horizon=12, tf_minutes=5):
    """Fold train/val indekslerini frame5 (date kolonlu) üzerinde döndürür.

    train: [train_start, train_end] ; val: [validation_start, validation_end].
    Label siniri korunur (fold val sonundan horizon mum).
    """
    from phase501_features import BLOCKS
    cols = BLOCKS[block]
    ts = pd.to_datetime(frame5["date"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("UTC")
    tr_start, tr_end = tuple(pd.Timestamp(t) for t in fold["train"])
    va_start, va_end = tuple(pd.Timestamp(t) for t in fold["validation"])
    if getattr(tr_start, "tz", None) is None:
        tr_start, tr_end = tr_start.tz_localize("UTC"), tr_end.tz_localize("UTC")
        va_start, va_end = va_start.tz_localize("UTC"), va_end.tz_localize("UTC")
    cutoff_val = va_end - pd.Timedelta(minutes=horizon * tf_minutes)
    tr_mask = (ts >= tr_start) & (ts <= tr_end)
    va_mask = (ts >= va_start) & (ts <= cutoff_val)
    tr = frame5.loc[tr_mask].copy().dropna(subset=cols + [label]).reset_index(drop=True)
    va = frame5.loc[va_mask].copy().dropna(subset=cols + [label]).reset_index(drop=True)
    check_not_in_protected(pd.concat([tr["date"], va["date"]]), f"fold[{label}]")
    return {
        "X_train": tr[cols].to_numpy(), "y_train": tr[label].to_numpy(),
        "X_val": va[cols].to_numpy(), "y_val": va[label].to_numpy(),
        "y_future_val": va["future_return"].to_numpy(),
        "val_dates": va["date"].to_numpy(),
        "n_train": len(tr), "n_val": len(va),
    }


def run_fold(fold_slice, model_id, label, seed):
    """Tek fold: fit -> val puanlari. (frozen model config kullanilir.)"""
    from phase503_models import make_model, fit_predict
    model, scaler = make_model(model_id, label, seed)
    scores, _, _ = fit_predict(model, scaler,
                               fold_slice["X_train"], fold_slice["y_train"],
                               fold_slice["X_val"])
    return scores


def wf_pss_scores(scores, future_returns, cost=0.003):
    """Top-decile PSS hesabi (phase505_stats ile AYNI fonksiyon, gecis engeli):
    rank -> top %10 -> mean future return - C -> (PSS, n_top, mean10, net_pos)."""
    s = np.asarray(scores, float)
    r = np.asarray(future_returns, float)
    k = max(1, int(np.ceil(len(s) * 0.10)))
    idx = np.argsort(-s, kind="stable")[:k]
    mean10 = float(r[idx].mean())
    return mean10 - cost, int(k), mean10, bool(mean10 - cost > 0)


def wf_consistency(fold_pss_results, main_pss_direction):
    """PSS yönü ana-val sonucuyla ayni VE net>0 olan fold orani."""
    same_dir = 0
    n = len(fold_pss_results)
    for res in fold_pss_results:
        pss = res["pss"]
        net_positive = res["net_positive"]
        same_direction = (pss > 0) == main_pss_direction
        if same_direction and net_positive:
            same_dir += 1
    return same_dir / n if n else 0.0


if __name__ == "__main__":
    folds = phase5_folds()
    print(f"{len(folds)} fold üretildi; min consistency {WF_MIN_CONSISTENCY}")
    print(overlap_report(folds))
    bounds_respected(folds)
    print("bounds respected (tüm foldlar VAL_END öncesi) OK")