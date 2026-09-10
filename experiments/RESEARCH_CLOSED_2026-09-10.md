# RESEARCH CLOSED — 2026-09-10

**Resmi kapanış:** 2026-09-10. Alfa arama programı, Phase 19 kararı
(RESEARCH STOP) esas alınarak KAPATILDI. Bu dosya kapanışın tek resmi
tutanak kaydıdır.

## Özet

- **Toplam test edilen alpha ailesi:** 22 aile incelendi; 16'sı karar-verici
  testle hükme bağlandı (P2–P18C), survivor = **0**.
- **FALSIFIED (13):** OHLCV (P2) · ML prediction 5m–15m (P3, P5) · RL
  decision (P4) · cross-asset features (6A) · funding sinyali (6B) · open
  interest (6C) · 4h event swing (P7 + M.20-confirm) · calendar/session (P10)
  · micro trade-flow (P14) · long-only trend + vol-target (18C).
- **ECONOMICALLY FAILED (3):** futures basis (P11) · carry/delta-neutral
  (P9) · long-only trend benchmark testi (18C — yüksek Sharpe, benchmark
  excess negatif).
- **DATA BLOCKED (5):** on-chain (PIT-tarihçe yok) · L2/order-book (ücretli)
  · maker execution (fill verisi yok) · news/X (arşiv yok) · liquidations
  flow (ücretli+seyrek). Hüküm YOKTUR.
- **PARTIALLY TESTED (1):** sistematik mean-reversion (yalnızca P10 fade
  formu test edildi — FAIL).
- **UNTESTED (4):** options vol yüzeyi · cross-exchange arb · ETF/makro
  akışları (üçü fizibilite-öncesi elendi) · **weekly cross-sectional
  long-only — UNTESTED / DATA-FEASIBLE BUT CURRENTLY NON-VIABLE** (en
  yüksek ROI 27/40; veri mevcut; ancak evren 7 majör + 30bp maliyet,
  literatürdeki avantajlar geniş evren + düşük maliyetle ilişkili →
  mevcut koşullarda edge'in 30bp'yi aşacağına dair yeterli gerekçe yok;
  bu bir falsification DEĞİLDİR).

## Phase 18C sonucu

6 aday (4H/1D long-only trend + vol-target, FINAL_B 2024H1): tümü
preregistered gate'leri geçemedi — G4 benchmark excess (hepsi negatif),
G5 aylık stabilite (3/6), FDR q>0.10. FINAL_B tek değerlendirmeyle
tüketildi; retry yasak. Yüksek nokta Sharpe'ları (0.73–2.15) ekonomik
alpha değildir.

## M.20 sonucu

FINAL_P5 (2025H1) independent confirmation: NOT-CONFIRMED (θ=−10.22,
AUC 0.5482). FINAL_P5 tüketildi.

## Holdout durumu (registry, 2026-09-10)

- **FINAL_A = CONSUMED** (P3)
- **FINAL_B = CONSUMED** (Phase 18C)
- **FINAL_C = UNTOUCHED** — araştırmanın son dokunulmamış rezervi
- FINAL_P5 = CONSUMED (M.20-confirmation kategorisi; FINAL-test penceresi
  sayılmaz — FINAL-test tüketimi: A + B = 2)

**FINAL_C neden korundu:** tüm erişilebilir alpha aileleri karar-verici
marjlarla falsifiye edildi; kalan tek veri-feasible adayın mevcut
universe/cost koşullarında 30bp'yi aşma gerekçesi yok; son rezervin
düşük-bilgi-değerli bir uzun-şansa harcanması yanlış olur.

## Yeniden açılma koşulları (yalnızca biri sağlanırsa)

- **A)** Daha düşük ve savunulabilir gerçek işlem maliyeti (maker/indirim/
  venue değişimi — C duvarı düşerse brüt-pozitif sinyaller yeniden
  değerlendirilebilir)
- **B)** PIT-correct yeni veri kaynakları (2020–2023 on-chain/L2 tarihçesi)
- **C)** Daha geniş ve likit cross-sectional universe
- **D)** Yeni bağımsız hipotez + yeni holdout assignment
- **E)** Gerçek maker/L2/fill-quality verisi
- **F)** Yeni dönem M.20 confirmation assignment

**Retry kuralı:** Aynı hipotezin FINAL_B üzerinde retry'i YASAKTIR (18C
family-level FAIL). FINAL_C yalnızca taze hipotez + M.20 assignment ile
kullanılabilir.

## Karar

**No further alpha search under current protocol.** Altyapı (guard'lar,
holdout protokolü, convention testleri, to_ms) ve FINAL_C rezervi yerinde
duruyor; araştırma yukarıdaki koşullardan biri gerçekleşmeden
yeniden açılmayacak.

Referanslar: experiments/phase_19/PHASE_19_FINAL_POSTMORTEM.md ·
PHASE_19_ALPHA_EVIDENCE_MATRIX.md · PHASE_19_STOP_CONTINUE_DECISION.md ·
experiments/phase_15/ (master audit, coverage matrix) ·
experiments/phase_17/ (preregistration, holdout plan) ·
experiments/phase_18/ (18C sonuçları).