# HOLDOUT REGISTRY (merkezi holdout kaydı — salt-konsolidasyon, değişiklik YOK)

**Konum gerekçesi:** mevcut convention `experiments/phase_05_ml/holdout/` dizinidir
(feather + manifest + verify); registry buraya konuldu, dosya taşınmadı.
**Kural:** Bu dosya SADECE kayıt tutar; statü değişikliği ayrı M.20 kararı ister.
Emin olunmayan alanlar UNKNOWN işaretlidir (tahmin YOK).

## FINAL_P5 — 2025H1 (2025-01-01 → 2025-06-30 23:55 UTC)
- Ayrıldığı deney: Phase 5 final testi (M20 formalization 2026-09-07).
- Durum: **CONSUMED** — M.20 independent-confirmation koşusu (bu oturum;
  RESULTS_CONFIRM.json, decision FAIL→NOT-CONFIRMED).
- Guard: `verify_holdout_hash()` + HOLDOUT_SHA256 `2441bf17…` + `check_not_in_protected`.
- Artifact/hash: `holdout/BTC_USDT-5m_2025H1.feather` + `manifest_2025H1.json` + `verify_2025H1.json`.
- Açık kalem: yerine yeni final test belirlenmedi (M.20 kararı bekliyor).

## FINAL_A — 2023H2 (2023-07-01 → 2023-12-31)
- Ayrıldığı deney: Phase 3 (FreqAI) final testi.
- Durum: **CONSUMED** — Phase 3 RESULT raporunda tek değerlendirme olarak koşuldu.
- Guard: p5_splits sabitleri + split guard'ları.
- Artifact: phase_03 sonuç CSV'leri (final_test_a_trades.csv untracked mevcut).
- Not: tekrar kullanılamaz (tüketilmiş pencere kuralı).

## FINAL_B — 2024H1 (2024-01-01 → 2024-06-30)
- Ayrıldığı deney: Phase 4 (RL) final testi.
- Durum: **CONSUMED** — Phase 18C (PHASE_17_LONG_ONLY_TREND_VOL_TARGET) tek
  değerlendirmesi; kayıt: PHASE_18C_RESULTS.json + PHASE_18C_FINAL_B_CONSUMPTION.md.
- Guard: p5_splits sabitleri + `check_not_in_protected` (çağrılarda aktif).
- Lokal feather varlığı: UNKNOWN (ad-hoc 2024H1 dosyası görülmedi; per-pair feather'ların tarih aralığı bu denetimde açılmadı).
- Artifact/hash: YOK (henüz üretilmedi).
- Phase 18A assignment (2026-09-10): PHASE_17_LONG_ONLY_TREND_VOL_TARGET — 4H/1D
  long-only trend-following + vol-targeting (Phase 17 preregistration grid, 6 aday).
  PRIMARY HOLDOUT = FINAL_B · BACKUP = FINAL_C. consumed = NO · evaluation = NO.
  Bu satır yalnızca assignment metadata kaydıdır; statü DEĞİŞMEDİ (UNTOUCHED).
  Kaynak artifact: YOK — 2024H1 verisi repo'da fiziksel olarak mevcut değil
  (ana BTC_USDT-5m.feather 2023-12-30 23:55'te bitiyor; 2024H1 satırı 0).
  Hash pin: PENDING — Phase 18B download-then-lock akışıyla üretilecek
  (P5 emsali: manifest + sha256 pin + registry kaydı; M.20 onayı zorunlu).
  Assignment öncesi hiçbir kod FINAL_B aralığına erişmedi; backtest koşulmadı.
- Phase 18B lock (2026-09-10): FINAL_B artifact indirildi + doğrulandı + pin'lendi.
  ASSIGNED = YES · ARTIFACT_AVAILABLE = YES · HASH_PINNED = YES · CONSUMED = NO ·
  EVALUATED = NO. Artifact: experiments/phase_17/holdout/BTC_USDT-5m_2024H1.feather
  (1.709.898 B, 52.416 satır, 2024-01-01 00:00 UTC ile 2024-06-30 23:55 UTC).
  SHA256 pin: 28f88258b976ee88382b3e176f8ce8db9f4827bc703c71f93c7d18235d0b9387
  (iki kez hesaplanarak doğrulandı). Manifest:
  experiments/phase_17/holdout/PHASE_18B_FINAL_B_MANIFEST.json (integrity PASS).
  Kaynak: Binance REST /api/v3/klines (P5 emsali, aynı konvansiyon).
  Statü DEĞİŞMEDİ (UNTOUCHED — assignment ve lock, consumption değildir).
  No-peek korundu: yalnızca veri bütünlüğü kontrolü; alpha/Sharpe metriği
  hesaplanmadı. FINAL_C indirilmedi; FINAL_A değişmedi.
- Phase 18C consumption (2026-09-10): FINAL_B değerlendirildi — 6 aday
  (PHASE_18C_RESULTS.json, PHASE_18C_RESULTS.md, PHASE_18C_FINAL_B_CONSUMPTION.md).
  CONSUMED = YES · EVALUATED = YES. Pin 28f88258… koşum öncesi ve sonrası
  doğrulandı (hash değişmedi). Tek değerlendirme — retry yok.

## FINAL_C — 2024H2 (2024-07-01 → 2024-12-31)
- Ayrıldığı deney: final karşılaştırma.
- Durum: **UNTOUCHED** — kullanım kanıtı yok; bu oturumda açılmadı.
- Guard: p5_splits sabitleri + `check_not_in_protected`.
- Lokal feather varlığı: UNKNOWN (yukarıdaki gerekçeyle).
- Artifact/hash: YOK.

## Çalışma pencereleri (holdout DEĞİL — referans)
- TRAIN 2020-01-01 → 2022-12-31 · VAL 2023-01-01 → 2023-06-30 00:00 UTC (kilitli sabitler; tüketim kavramı uygulanmaz).
