"""Phase 5 — Frozen model set (DESIGN 500 sec 9): M1 LR/Ridge, M2 RF, M3 LGBM, BASE.

- M1: LogisticRegression / Ridge + StandardScaler (train-fit ONLY; val'e yalnizca
  uygulanir; scaler istatistikleri artefakta saklanir).
- M2: RandomForest (Phase 3 kilitli config: 200/8/50/balanced/n_jobs=1).
- M3: LightGBM (500/0.05/31/0.8/0.8/verbosity=-1, frozen).
- BASE: majority-class (L0/L1) / mean(Y) (L2) — feature kullanmaz.
n_jobs=1 RF: bit-exact reproducibility (Phase 3 gerekcesi, degistirilmez).
LGBM determinism: random_state=seed + n_jobs=1 dengeli guidi (hiz-denge).
"""
import hashlib

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler

M1_LR_PARAMS = {"C": 1.0, "penalty": "l2", "solver": "lbfgs",
                "max_iter": 1000, "class_weight": "balanced"}
M1_RIDGE_PARAMS = {"alpha": 1.0}
M2_PARAMS = {"n_estimators": 200, "max_depth": 8, "min_samples_leaf": 50,
             "n_jobs": 1}
M3_PARAMS = {"n_estimators": 500, "learning_rate": 0.05, "num_leaves": 31,
             "colsample_bytree": 0.8, "subsample": 0.8, "verbosity": -1}

M1 = "M1"
M2 = "M2"
M3 = "M3"
BASE = "BASE"


def is_classification(label):
    return label in ("L0", "L1")


def cell_seed(cell_id: str, seed: int) -> int:
    """Deterministik (cell, seed) RNG tohumu."""
    return int(hashlib.sha256(f"{cell_id}|{seed}".encode()).hexdigest()[:8], 16)


def make_model(model_id, label, seed):
    if model_id == M1:
        if is_classification(label):
            return LogisticRegression(random_state=seed, **M1_LR_PARAMS), StandardScaler()
        return Ridge(random_state=seed, **M1_RIDGE_PARAMS), StandardScaler()
    if model_id == M2:
        if is_classification(label):
            return RandomForestClassifier(random_state=seed, class_weight="balanced",
                                          **M2_PARAMS), None
        return RandomForestRegressor(random_state=seed, **M2_PARAMS), None
    if model_id == M3:
        from lightgbm import LGBMClassifier, LGBMRegressor
        if is_classification(label):
            return LGBMClassifier(random_state=seed, n_jobs=1, **M3_PARAMS), None
        return LGBMRegressor(random_state=seed, n_jobs=1, **M3_PARAMS), None
    raise ValueError(f"bilinmeyen model: {model_id}")


def fit_predict(model, scaler, X_train, y_train, X_val, label=None):
    """Model fit (train-only) + val OOF puanları. (model, scaler) fit modelini dondurur.

    Dönüş: (numpy float array val_scores, fitted_model, fitted_scaler).
    - L0/L1: class 1 olasılığı (positif sinyal olasıligi).
    - L2: regresyon öngörüsü.
    label parametresi, sklearn api değişiklikleri nedeniyle sınıflandırma kararını
    model tipi üzerinden yapar (is_classification kullanılmaz); geriye uyumluluk
    için opsiyoneldir.
    """
    from lightgbm import LGBMClassifier  # noqa: F401  (kurulum dogrulamasi)
    Xtr = scaler.fit_transform(X_train) if scaler is not None else X_train
    Xv = scaler.transform(X_val) if scaler is not None else X_val
    model.fit(Xtr, y_train)
    use_proba = (label in ("L0", "L1") if label else hasattr(model, "predict_proba"))
    if use_proba:
        probas = model.predict_proba(Xv)
        scores = probas[:, 1] if probas.shape[1] > 1 else np.zeros(len(Xv))
    else:
        scores = model.predict(Xv)
    return np.asarray(scores, dtype=float), model, scaler


def fit_baseline_scores(y_train, y_val, label, seed=42):
    """BASE hücresi puanı: L0/L1 -> majority sınıfı probası; L2 -> train ortalaması."""
    yt = np.asarray(y_train, dtype=float)
    if is_classification(label):
        p = np.clip(np.nanmean(yt), 1e-9, 1 - 1e-9)
        return np.full(len(y_val), float(p)), {"base_rate": float(p)}
    m = float(np.nanmean(yt))
    return np.full(len(y_val), float(m)), {"mean": m}


if __name__ == "__main__":
    print("model factories OK")
    for m in (M1, M2, M3):
        est, sc = make_model(m, "L1", 42)
        print(m, type(est).__name__, "scaler=", sc is not None if sc else None)