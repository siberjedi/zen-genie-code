# PHASE 19 — STOP / CONTINUE DECISION

**Statü:** READ-ONLY KARAR. Backtest yok. FINAL_C erişimi yok.

## 1. Research ROI (0–5) — kalan adaylar

Kriterler: Expected alpha · Data accessibility · PIT safety · Execution realism
· Novelty · Research cost (inverse) · Chance of surviving 30bp · Information value.

| Aday | α | Data | PIT | Exec | Novelty | Maliyet⁻¹ | 30bp şans | Bilgi | **TOPLAM** |
|------|---|------|-----|------|---------|-----------|-----------|-------|-----------|
| **Haftalık cross-sectional long-only (top-k)** | 3 | 3 | 4 | 3 | 3 | 4 | 3 | 4 | **27** |
| Maker execution (maliyet-indirimi) | 1 | 1 | 3 | 5 | 2 | 3 | 4 | 2 | 21 |
| L2/order-book (BTC) | 2 | 1 | 3 | 2 | 4 | 2 | 2 | 3 | 19 |
| Options vol yüzeyi | 2 | 2 | 2 | 2 | 4 | 1 | 2 | 3 | 18 |
| Cross-exchange arb | 2 | 2 | 3 | 1 | 4 | 1 | 2 | 3 | 18 |
| On-chain PIT | 2 | 1 | 1 | 3 | 4 | 2 | 2 | 2 | 17 |

En yüksek: **haftalık cross-sectional (27/40)** — diğerleri ya veri-bloklu ya
düşük bilgi değeri. 27/40 = "test etmek rasyonel olabilir" eşiği civarında,
"kesin test et" değil.

## 2. CONTINUE/STOP kriterleri kontrolü

1. **Tüm kolay/ucuz alpha aileleri falsifiye:** EVET — 16 testli hat, 0 survivor
   (P2–P18C; tek "ucuz" kalan: weekly cross-sectional, verisi coldstorage'de).
2. **Kalan adayların çoğu veri bloklu:** EVET — 6/7 (L2, maker, on-chain,
   options, arb, ETF); yalnızca weekly cross-sectional veri-feasible.
3. **Beklenen edge 30bp altında:** PARTİYEL — dış literatür 4–10bp maliyetle
   çalışıyor; bizim C=0.003 3–7× üstünde. Cross-sectional alpha'nın literatürdeki
   kaynağı küçük/likit-olmayan coin'ler — bizim evren 7 MAJÖR (alpha'nın en zayıf
   olduğu dilim). "Survive 30bp" olasılığı düşük.
4. **Yeni holdout maliyeti yüksek:** ORTA — FINAL_C (2024H2) son rezerv; tek
   şans; download-then-lock + M.20 onayı gerekir. Harcanırsa projenin hiç
   holdout'u kalmaz.
5. **Mevcut evidence alpha yokluğuna işaret ediyor:** EVET — 13 family
   FALSIFIED + 3 economic fail; iki bağımsız holdout (P5, FINAL_B) doğrulanan
   hiçbir sinyal üretmedi; kalan tek adayın universe-cost uyumsuzluğu var.

## 3. Karar

**RECOMMENDATION: A) RESEARCH STOP**

Gerekçe (quantitative):
- 16/16 testli hipotez-ailesi karar-verici gate'lerde başarısız; survivor 0.
- FINAL-test pencereleri (FINAL_A/B/C) içinden 2'si tüketildi: FINAL_A (P3)
  ve FINAL_B (18C). FINAL_P5 ayrı bir M.20-confirmation kategorisidir (o da
  tüketildi). **FINAL_C = araştırmanın son dokunulmamış rezervi.** En güçlü tek
  sonuç bile (18C: Sharpe 2,15) FDR q>0.10 — 6 aylık pencerelerde Sharpe SE ~2,4;
  yeni bir deneyin istatistiksel kesinlik kazanması için çok daha uzun OOS
  gerekir ki mevcut veri/rezerv yapısında yok.
- Kalan tek veri-feasible aday (weekly cross-sectional) için: dış kanıt güçlü
  (weekly flow Sharpe 1.93; long-only ranking Sharpe 1.01) AMA (a) literatür
  30–3000 coin kullanıyor, alpha küçük/illikit coin'lerde; bizim 7 majör +
  30bp'de beklenen edge ince; (b) 6A zaten cross-asset bilgiyi 5m'de
  falsifiye etti (farklı estimand ama aynı bilgi alanı); (c) FINAL_C'nin bu
  uzun-şans adaya harcanması, marjinal bilgi değerini (≤27/40 ROI) son-holdout
  maliyetinin altına iter.
- Her yeni backtestin beklenen bilgi kazancı, harcanan son rezerv + araştırma
  maliyetinden küçüktür. "Test edilmemiş" ≠ "ümit verici" (Phase 19
  postmortem §4): kalan uzayın tamamı ya veri-bloklu ya düşük-ROI.

B (ONE FINAL EXPERIMENT) seçilseydi tek aday: **haftalık cross-sectional
long-only top-k (7 majör) + FINAL_C assignment** — ancak yukarıdaki
universe-cost uyumsuzluğu nedeniyle önerilmiyor.

C (EXPAND DATA) önerilmiyor: tek veri-boşluğu (L2/on-chain) ücretli ve
PIT-sorunlu; genişletilmiş veriyle bile 30bp duvarı aynı kalıyor.

## 4. M.20 RETRY RULE

- Phase 18C family-level FAIL → aynı hipotez ailesi (long-only trend +
  vol-target) FINAL_B üzerinde RETRY EDİLEMEZ.
- Yeni deney için: taze hipotez + taze holdout (FINAL_C) + M.20 assignment
  gerekir. Bu kararda yeni deney önerilmediği için retry kuralı geçerli
  kalır (kapalı aile listesi: P2–P18C tüm aileleri).

## 5. Holdout state

- FINAL_A = CONSUMED (P3) · FINAL_P5 = CONSUMED (M.20) · FINAL_B = CONSUMED
  (18C) · **FINAL_C = UNTOUCHED** (registry metadata doğrulandı; verisi
  okunmadı/indirilmedi — 2024H2 artifact'ı repo'da yok).
- FINAL_B retry: yasak. FINAL_C: rezervde.

## 6. Araştırma devamı koşulları (gelecekte)

Araştırma yalnızca şu koşullardan biri sağlanırsa yeniden açılmalı:
1. 30bp altı maliyet kanıtı (maker/indirim/venue değişimi) — C duvarı düşerse
   brüt-pozitif sinyallerin (P11, 18C trend, mikro-flow) yeniden değerlendirmesi
   anlamlı olur.
2. PIT-uyumlu on-chain/L2 tarihçesi (2020–2023) — veri boşluğu kapanırsa
   DATA BLOCKED aileleri test edilebilir.
3. 2025H2+ dönemi olgunlaşınca yeni holdout ataması (M.20) — yeni dönemde
   yeni yapısal değişiklik varsa.

VERDICT: **RESEARCH STOP** (A) — mevcut maliyet/veri/holdout kısıtları altında
yeni backtestin beklenen bilgi değeri maliyetinin altındadır.