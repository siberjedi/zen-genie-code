# Faz 3 — Kilitli Feature Set (2026-09-04, sonuç öncesi kilitli)

Kaynak: `src/freqai/features.py:1`. Değişiklik = yeni Final Test gerekir (Anayasa Madde 4, 20).

| # | Feature | Tanım | Pencere | Nedensel |
|---|---------|-------|---------|----------|
| 1 | `ret_1` | `close.pct_change(1)` | 1 mum | Evet (t-1→t) |
| 2 | `ret_12` | `close.pct_change(12)` (~1s momentum) | 12 mum | Evet |
| 3 | `rsi14` | Wilder RSI(14), TA-Lib ile aynı matematik | 14 mum | Evet (`ewm`, ileriye bakmaz) |
| 4 | `sma50_ratio` | `close/SMA50-1` | 50 mum | Evet |
| 5 | `sma200_ratio` | `close/SMA200-1` | 200 mum | Evet |
| 6 | `sma_trend` | `SMA50>SMA200 ? 1:0` (Baseline girişiyle aynı koşul, feature olarak) | 200 mum | Evet |
| 7 | `atr14_ratio` | `ATR(14)/close` (Wilder) | 14 mum | Evet |
| 8 | `vol_z` | `volume/ort24-1` | 24 mum | Evet |

Yasaklar:
- `.shift(-n)`, ileriye dönük rolling, gelecek mum kullanımı YOK (test: `test_feature_leakage`).
- Doldurma YOK: warmup satırları atılır. Kayıp = ilk 199 satır/pair (SMA200 belirler) + label kuyruğu 12 = 211.
- Normalizasyon/scaler YOK (ağaç modeli; scaler eklemek = tanım değişikliği).
- Pair bilgisi feature DEĞİL (oran-tabanlı, pair-agnostik; pooled eğitim).

Doğrulama: `tests/test_freqai_readiness.py::test_feature_leakage`, `test_nan_handling` — PASS.
