"""Faz 3 — Kilitli label tanımı (sonuç öncesi kilitli, 2026-09-04).

- Horizon H = 12 mum (5m -> ~1 saat).
- Threshold = 0.002 (%0.2) = round-trip maliyet (fee_taker 0.001 x 2).
  Gerekçe: maliyetin üstündeki hareketler "işe yarar sinyal" sayılır.
- label[t] = 1 eğer close[t+H]/close[t]-1 > 0.002, yoksa 0.
- Future return SADECE label için kullanılır; feature'lara sızmaz
  (feature'lar `features.build_features` ile label'dan bağımsız üretilir).
- Son H satırın label'ı tanımsızdır (NaN) ve ATILIR — kural mekanik,
  sonuçlara göre değiştirilemez.
"""
import pandas as pd

LABEL_HORIZON = 12
LABEL_THRESHOLD = 0.002
LABEL_COL = "label"


def build_labels(df: pd.DataFrame,
                 horizon: int = LABEL_HORIZON,
                 threshold: float = LABEL_THRESHOLD) -> pd.Series:
    """close serisinden ikili label. Index korunur; son `horizon` satır NaN."""
    close = df["close"].astype(float)
    fwd = close.shift(-horizon) / close - 1
    labels = (fwd > threshold).astype(float)
    labels[fwd.isna()] = float("nan")
    labels.name = LABEL_COL
    return labels


def build_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Feature + label birleşimi, NaN satırlar atılmış (warmup + kuyruk).

    Dönüş kolonları: FEATURES + [label]. Tarih kolonu varsa korunur.
    """
    from .features import build_features
    feat = build_features(df)
    lab = build_labels(df)
    data = feat.join(lab)
    data = data.dropna().reset_index(drop=True)
    # tarih izlenebilirliği için: girdi sırası korunduğu için konumsal eşleme
    return data


def expected_dropped(n_rows: int) -> int:
    """Mekanik kayıp: warmup (199) + kuyruk (12)."""
    from .features import WARMUP_ROWS
    return WARMUP_ROWS + LABEL_HORIZON
