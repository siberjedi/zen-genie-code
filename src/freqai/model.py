"""Faz 3 — Tek kontrollü baseline model (sonuç öncesi kilitli, 2026-09-04).

Amaç "en iyi modeli bulmak" DEĞİL; kontrollü FreqAI baseline'ı.
Model çeşitliliği YOK: yalnızca RandomForestClassifier, aşağıdaki hiperparametrelerle.
Seed duyarlılığı gerçektir (random_state=seed); 5 seed sonucu ayrı kaydedilir.
"""
from sklearn.ensemble import RandomForestClassifier

MODEL_NAME = "RandomForestClassifier"
HYPERPARAMS = {
    "n_estimators": 200,
    "max_depth": 8,
    "min_samples_leaf": 50,
    "class_weight": "balanced",
    # n_jobs=1: bit-exact reproducibility (n_jobs=-1 paralel indirgemede
    # ~1e-16 dalgalanma yapar ve ayni seed farkli proba üretir — test edildi).
    # Hizdan önce determinizm; compute tercihi, model seçimi değil.
    "n_jobs": 1,
}
SIGNAL_THRESHOLD = 0.5  # proba >= 0.5 -> long sinyali


def make_model(seed: int) -> RandomForestClassifier:
    return RandomForestClassifier(random_state=seed, **HYPERPARAMS)


def predict_proba(model: RandomForestClassifier, X) -> list:
    return [float(p[1]) for p in model.predict_proba(X)]


def proba_to_signal(probas: list, threshold: float = SIGNAL_THRESHOLD) -> list:
    return [1 if p >= threshold else 0 for p in probas]
