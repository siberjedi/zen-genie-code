# PHASE 18A — M.20 FINAL_B HOLDOUT ASSIGNMENT

**Statü:** ASSIGNMENT METADATA. Backtest YOK. Holdout tüketimi YOK.

## 1. Assignment rationale

- Phase 16 tek açık aday: long-only trend + vol-target (4H/1D, low-turnover).
- Phase 17 preregistration leakage audit PASS → holdout ataması gerekti.
- FINAL_A (2023H2) ve FINAL_P5 (2025H1) CONSUMED. Kalan rezervler:
  FINAL_B (2024H1) ve FINAL_C (2024H2) — ikisi de UNTOUCHED.
- **PRIMARY HOLDOUT = FINAL_B (2024-01-01 → 2024-06-30 23:55 UTC)** —
  VAL'den (2023H1) sonraki ilk rezerv; trend/vol rejimi 2024H1, eğitim
  dönemine (2020–2022) en yakın kullanılabilir pencere.
- **BACKUP = FINAL_C (2024-07-01 → 2024-12-31 23:55 UTC)** — yalnızca
  FINAL_B veri bütünlüğü bozulursa, önceden M.20'ye raporlanarak.
- Deney ailesi: **PHASE_17_LONG_ONLY_TREND_VOL_TARGET** — 4H/1D long-only
  trend-following + volatility targeting (Phase 17 grid: 6 aday, a priori
  sıralı; PRIMARY aday #1: 4H price-vs-SMA200).

## 2. Exact data source

- **DURUM: FINAL_B SOURCE NOT AVAILABLE.**
- Repo taraması (2026-09-10): `experiments/phase_05_ml/holdout/` yalnızca
  P5 dosyalarını içeriyor (`BTC_USDT-5m_2025H1.feather` + manifest +
  verify). 2024H1'e ait hiçbir feather/artifact repo'da yok.
- Ana veri `freqtrade/user_data/data/binance/BTC_USDT-5m.feather` fiziksel
  aralığı: 2020-01-01 → 2023-12-30 23:55 (420.014 satır); FINAL_B
  penceresindeki satır sayısı = 0.
- Protocol gereği (Phase 17 HOLDOUT_PLAN §3): **download YAPILMADI.**
  Kaynak üretimi Phase 18B'ye bırakıldı (download-then-lock, P5 emsali).

## 3. SHA256 / pin

- **PENDING.** Artifact yok → hash hesaplanamadı. Pin, Phase 18B'de
  indirme sonrası üretilecek ve registry'ye yazılacak; her okuma
  `verify_holdout_hash` benzeri pin kontrolüne tabi olacak.

## 4. Registry entry

- `experiments/phase_05_ml/holdout/HOLDOUT_REGISTRY.md` → FINAL_B bölümüne
  assignment satırı eklendi (append-only; mevcut geçmiş değişmedi).
- Statü: **UNTOUCHED** (değişmedi) · consumed = **NO** · evaluation = **NO**.
- FINAL_C: UNTOUCHED (dokunulmadı).

## 5. Guard status

- `check_not_in_protected` (p5_splits): FINAL_A/B/C/P5 erişimini engeller — aktif.
- `verify_holdout_hash`: P5 pin'ini korur — FINAL_B için pin Phase 18B'de.
- Assignment, mevcut guard'ları genişletmez/değiştirmez; eksik guard
  yoktur — yalnızca FINAL_B artifact'ı ve pin'i henüz yoktur.
- Accidental read/test koruması: mevcut guard + repo'da 2024H1 verisi
  bulunmaması (fiziksel erişim imkânsız) çift katmanlı.

## 6. Tests

- `py -m pytest tests/test_holdout_registry.py -q` → beklenti: 5/5 PASS
  (registry güncellemesi test-uyumlu: pencere kümesi, statü kümesi,
  UNTOUCHED kanıtları korundu).
- `py -m pytest tests/test_decision_log.py -q` → 6/6 PASS (beklenti).

## 7. Consumption state

- FINAL_B: **UNTOUCHED**. FINAL_C: **UNTOUCHED**. Assignment ≠ consumption.
- Bu fazda hiçbir backtest/feature/aggregation/parameter-selection
  çalıştırılmadı (backtest count = 0).

---

VERDICT: **HOLD** — assignment kaydı tamam, ancak FINAL_B kaynak artifact'ı
mevcut değil ve hash pin PENDING. Sıradaki adım: **Phase 18B — download-then-lock**
(M.20 onayıyla 2024H1 feather indirme + manifest + sha256 pin + registry
tüketim-kaydı altyapısı). Backtest başlatılmadı.