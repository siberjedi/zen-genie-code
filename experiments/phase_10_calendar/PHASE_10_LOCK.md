# PHASE 10 — LOCK / PREFLIGHT (kilit + doğrulama; backtest YOK)

**Statü:** LOCKED SPEC + executable verification tamamlandı. Getiri/P&L/
Sharpe/gate-değerlendirme YOK (onlar backtest). Tuning/threshold yok.
Holdout kapalı. Commit yok.

## Frozen kurallar (değişmez)

- **E1 weekend-long:** Cuma 23:55 giriş → Pazar 23:55 flat (long).
- **E2 overnight-long:** her gün 00:00 → 08:00 UTC (long).
- **E3 post-settlement-fade short:** T → T+3h, T ∈ {00,08,16} UTC (short).
- Çıkış barı yoksa event DÜŞER (deterministik; örn. son Cuma).
- **Overlap (kilitli):** kurallar BAĞIMSIZ portföyler; çapraz-netting YOK;
  kural-içi max-concurrent == 1 (assert'li).
- **Cost:** hold başına C=0.003 round-trip (spot taker varsayımı, kilitli).

## Verification sonuçları (PREFLIGHT10.json + events10.parquet, 5.274 event)

- Takvim-only üretim (causality probe PASS; fiyat girdisi YOK — date kolonu hariç).
- Grid: 367.023 bar, 2020-01-01 → 2023-06-30 00:00 (kilitli VAL_END; varsayım düzeltildi, raporlu).
- Event sayıları: E1=182, E2=1274, E3=3818 (kenar-kayıplar deterministik).
- Kural-içi concurrency: 1/1/1 (assert PASS). Çapraz: 363 E2 girişi E1-hold içinde (bağımsız kol).
- Settlement çapraz-kontrol: arşiv 3.831 ↔ E3 3.818 (fark kenar-kayıp; grid 8h doğrulamalı).
- Güç (d=0.30, tek-yönlü): E1 0.9915, E2/E3 1.0000 → hepsi ≥0.80 (yeterli).
- FDR-3 yapısı kilitli (BH, 3 kural). Primary θ (hafta-blok bootstrap) + gate zinciri (net>0, edge≥1.2, MaxDD≤0.20, d/power, q) backtest'te uygulanacak.

## Kritik metodolojik risk

Kurallar fiyat-görmeden donduruldu (güçlü taraf); zayıf taraf öncüllerin
zayıflığıdır (özellikle E3 yönü) — gate'ler ve FDR bunu yönetir, tasarım
güzellemez. Çapraz-overlap (E1∩E2) sleeve-bağımsızlığı varsayar; raporlanır.

## Verdict: BACKTEST GO

Preflight STOP koşulu tetiklenmedi (sayılar/tutarlık/coverage/güç/grid hepsi
PASS). Backtest, bu kilit aynen uygulanarak koşulabilir (ayrı M.20 ile).

*Kod: scripts/phase10_preflight.py. Veri: mevcut feather (tarih-only okuma) +
6B manifest referansı. Holdout kapalı. Commit yok.*
