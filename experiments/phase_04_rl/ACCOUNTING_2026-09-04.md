# Phase 4.9 RL Accounting / Metric Integrity Fix — 2026-09-04

> Kapsam: kayıt doğruluğu + raporlama etiketleri. Davranış DEĞİŞMEDİ
> (env, reward, fee/slippage, split, chunking aynı). Tuning YOK, Final B YOK.

## A) Forced exit bug düzeltildi mi?
- EVET (kayıt katmanı): 4 recorder (`phase04_tuning` → tuning/curves/smoke
  ortak fonksiyon + `phase47_tuning` + `phase04_repro_probe` + smoke-local),
  forced kapanışta SON mumu kaydediyor (`exit_reason: forced_close`).
- Kanıt: 7 yeni test (mum/index/fiyat exact) + mevcut 24 test yeşil.
- Phase 4.8 `replay` zaten doğruydu (değişmedi); E1 partition sonuçları geçerli.

## B) Equity/reward değişti mi?
- HAYIR. Env'e dokunulmadı; düzeltme SADECE trade-kayıt sözlüğünde.
  Ledger↔equity ve reward↔equity telescoping testleri (tolerans 0.05 / 1e-9)
  geçiyor. Geçmiş sonuç dosyaları OVERWRITE EDİLMEDİ (1-mumluk forced
  fiyat farkı yalnızca gelecek kayıtları etkiler; eski metriklerdeki etki
  <1 mumluk%-değişim mertebesinde ve raporlanıyor, düzeltilmiyor).

## C) Invalid action gerçek oranı nedir?
- E1/42: %68.7 (29,575 SELL-flat + 6,006 BUY-long; valid: 16,133 HOLD + 40/40).
- E1/123: %87.6 (79 SELL-flat + 45,303 BUY-long; valid: 6,179 HOLD + 117/116).
- E1/999: %25.2 (274 SELL-flat + 12,778 BUY-long; valid: 38,721 HOLD + 11/10).
- Örüntü: seed'ler zıt spam rejiminde (42 SELL-spam, 123/999 BUY-spam).
  Ekonomik etki SIFIR (no-op); kalibrasyon sinyali olarak raporlanır,
  maskelenmez/cezalandırılmaz.

## D) E1 pozitif sonuçlarının forced exit bağımlılığı nedir?
| seed | n | net | nonforced (n/net) | forced (n/net) | top3 payı | flag |
|------|---|-----|-------------------|----------------|-----------|------|
| 42 | 40 | +37.50 | 40/+37.50 | 0/— | 1.239 | SMALL-N |
| 123 | 117 | +18.75 | 116/+21.60 | 1/−2.85 | 1.946 | normal* |
| 999 | 11 | +80.80 | 10/+58.82 | 1/+21.98 | 1.016 | VERY SMALL-N |
- 999'un net'inin %27'si TEK forced trade (+21.98, ~99 gün hold).
- top3 payı ≥1.0 her yerde: kazançlar birkaç trade'de, kaybedenler offsetliyor.
- *123 "normal" (n=117) ama top3=1.946 ile en konsantre olanı.

## E) E1'in 42/123/999 sonuçları replay ile doğrulanıyor mu?
- EVET: replay trade sayısı (40/117/11) + net (±0.01) + env-equity eşleşmesi
  (5/5 True) kayıtlarla birebir. Trade listeleri `partition_E1.json`'da.

## F) Yeni bir protocol change gerekiyor mu?
- HAYIR. Değişiklikler kayıt/raporlama altyapısında kaldı (forced fiyatı,
  exit etiketi, breakdown/flag helper'ları). Reward, fee/slippage, split,
  chunking, threshold'lar, budget aynen. Davranış değiştiren hiçbir şey yok.

## SON KARAR
ACCOUNTING CLEAN — SAFE TO DESIGN NEXT EXPERIMENT
- Repro probe: 7/7 PASS (model/action/equity/reward/trade/bounds/val-range).
- Suitler: 7 (yeni) + 12 + 12 PASS. Final B'ye temas yok. Tuning YOK.
