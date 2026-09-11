# PHASE 5 — FINAL_TEST_P5 (2025H1) HOLDOUT LOCK / MANIFEST
## Tarih: 2026-09-07 · Statü: RESERVED + PINNED (M.20 formalization)

## 1. Rezervasyon özeti
- **FINAL_TEST_P5 = BTC/USDT 5m, 2025-01-01 00:00 UTC → 2025-06-30 23:55 UTC**
- Role: Phase 5'in TEK, korumalı final holdout'u. Yalnızca önceden kilitlenmiş
  nihai adayın TEK KEZ değerlendirmesi için (tuning/seçim/eğitim YASAK).
- Kaynak: Binance REST `/api/v3/klines` (200 OK doğrulandı, 5m, 1000-adet paginated).
- İndirme kapsamı: YALNIZCA 2025H1. Final B (2024H1), 2024H2 erişilmedi.

## 2. Dosyalar
| Dosya | Boyut | SHA256 |
|---|---|---|
| `experiments/phase_05_ml/holdout/BTC_USDT-5m_2025H1.feather` | ~1.67 MB | `2441bf175f86b3f6d52246d482bb9263a49684831387bfed504b91a9fab5389c` |
| `experiments/phase_05_ml/holdout/manifest_2025H1.json` | - | (içerik hash'i rapora yansır) |
| `experiments/phase_05_ml/holdout/verify_2025H1.json` | - | bağımsız doğrulama çıktısı |

## 3. Integrity sonuçları (bağımsız verify + test kanıtlı)
- row_count: **52,128** (= beklenti 52,128, %100 dolu pencere)
- date_first: **2025-01-01 00:00:00+00:00** (UTC)
- date_last: **2025-06-30 23:55:00+00:00** (UTC)
- duplicates: **0** · nulls: **0** · ordering: monotonik artan
- missing_interval: **0** (tam 5m grid farkı 0)
- fiyat_pozitif: **0 ihlal** · OHLC ilişki (high≥max, low≤min): **0 ihlal**
- schema: `[date, open, high, low, close, volume]` — mevcut feather ile BİREBİR
- integrity_pass: **True**

## 4. Guard (pipeline koruması)
- `src/freqai/p5_splits.py` — rezervasyon sabitleri + `check_not_in_protected`
  (FINAL_A/B/C/P5 sızıntıya ABORT), `split_train_val_p5` (seçim hattı), 
  `load_holdout` (yalnızca FINAL değerlendirme; hash pin + pencere abartı),
  `verify_holdout_hash` (pin değişirse ABORT).
- Pin: `HOLDOUT_SHA256 = 2441bf175f86b3f6d52246d482bb9263a49684831387bfed504b91a9fab5389c`
- Testler: `tests/test_phase500.py` — **19/19 PASS** (her korunan pencere probe-ABORT,
  split sınırı, holdout yükleyici, bozuk-hash reddi, sabit teyidi).
- Bağımsız verify: `scripts/phase500_holdout_verify.py` — **ALL PASS**.

## 5. Dokunulmazlık teyidi
- **Final Test B (2024H1): UNTOUCHED** — indirme kapsamı dışı; koruma probe'u ABORT.
- **2024H2 (Final C): UNTOUCHED** — indirme kapsamı dışı; koruma probe'u ABORT.
- **Mevcut 2020-2023 dataset:** DOKUNULMADI — `BTC_USDT-5m.feather` değişmedi
  (420,014 satır, max 2023-12-30 23:55; yapılan check teyit etti).
- **Final Test A (2023H2):** FreqAI'ye ait (tüketildi); Phase 5 kullanmaz.

## 6. Kalanlar (pipeline KAPALI)
- Eğitim/feature/model/threshold/tuning: YOK.
- Deney pipeline'ı ancak resmî M.20 onayı + bu holdout'un serbest bırakılması
  (ADVANCE-to-IMPLEMENTATION) sonrası çalışır.

---
**HOLDOUT LOCKED (RESERVED). READY FOR PHASE 5 IMPLEMENTATION APPROVAL**