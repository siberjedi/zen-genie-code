# PHASE 06C — SCOUT REPORT (feasibility only; deney/lock YOK)

**Kapsam:** 6A (FAIL) ve 6B (FAIL) sonrası OI test edilebilirlik taraması.
İndirme/feature/fit/backtest YAPILMADI. M.20 lock YAPILMADI.

## Bulgular
1. **Intraday 5m OI ücretsiz mevcut** (S1: Vision daily/metrics, 5m snapshot'lar).
2. **Kapsama ~2020-09-10 → 2023-06-30** (ayna kanıtı; run-time teyit gate'li).
   2020-01→2020-09 aralığı YOK → FULL train ~%30 satır kaybeder; VAL tam.
3. **Daily-only 5m/1h için yetersiz** — intraday şart (mevcut).
4. **Resmi REST arşiv vermez** (30-gün cap; latest-only) — S2/S3 elendi.
5. **Ücretli fallback mevcut** (S5 poll-damgalı, S4 OHLC 1m–1w plan-kısıtlı) —
   şu an gerekmiyor.
6. **Leakage yönetilebilir:** create_time ≤ close asof-backward + deterministik
   geceyarısı dedup + doldurma yasağı.
7. **Sembol sürekliliği:** BTCUSDT perp Sept-2019+, kesinti yok.
8. **Horizon uyumu:** OI 5m gridde yaşar; 5m→1h hedefle uyumlu.

## Ekonomik not (sinyal iddiası DEĞİL)
OI akışları dakika-saat ölçeğindedir; test edilebilirlik olumlu. Sinyal gücü
deneyin sorusudur.

## Önerilen hat
6C-1 (S1 + BASE/NEW/FULL + 6A/6B makinesi). M.20 açık noktaları (4 madde)
EXPERIMENT_OPTION_6C.md'de.

## Holdout/koruma
4 pencereye dokunulmadı; indirme yapılmadı; 6A/6B dosyaları değişmedi.

## Karar

**READY FOR 6C M.20**
