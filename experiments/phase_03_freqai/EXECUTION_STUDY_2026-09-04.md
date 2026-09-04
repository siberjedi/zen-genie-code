# Phase 3.6 Execution Study — 2026-09-04 (DIAGNOSTIC ONLY)

> Dondurulmuş rf_seed2026 + validation penceresi (2023-01-01→2023-06-29, 181 gün).
> Eğitim YOK, Final Test A YOK (okuma bile yok), Phase 3 sonucu OVERWRITE YOK,
> protokol/threshold/baseline YOK. Hiçbir variant "strateji" değildir;
> umut verici görünen Final A'ya UYGULANMADI (candidate hypothesis olarak raporlandı).

## A. Baseline frozen prediction
Variant A (0.50/0.50, kısıtsız) frozen sonucu bit-identik üretti
(REPRO PASS: 15603 trade, net -99.975) — harness doğrulandı.
Fee break-even: işlem-başı gross ≥ **0.002 stake oranı** (%0.2 round-trip).

## B. H1 hysteresis results
| variant | trades | trades/gün | gross | fee | net | sharpe | maxdd | med hold |
|---|---|---|---|---|---|---|---|---|
| A 50/50 | 15603 | 86.20 | +47.18 | 147.16 | -99.975 | -24.186 | -0.9997 | 5dk |
| B 55/45 | 2173 | 12.01 | +31.46 | 104.13 | -72.666 | -3.205 | -0.8146 | 125dk |
| C 60/40 | 702 | 3.88 | +2.13 | 47.76 | -45.633 | -1.316 | -0.6872 | 290dk |
Bant churn'ü 22x kesiyor, Sharpe -24→-1.3, ama gross da eriyor (+47→+2): bant
sadece gürültüyü değil, zayıf sinyali de eliyor. WR 0.34→0.78 yükseliyor
(seçicilik artıyor) fakat net hâlâ derinden negatif.

## C. H2 min-hold results (sinyal çıkışı bloklu; SL/ROI her zaman aktif)
| variant | trades | gross | fee | net | sharpe | med hold |
|---|---|---|---|---|---|---|
| hold_05 | 15603 | +47.18 | 147.16 | -99.975 | -24.186 | 5dk |
| hold_15 | 12005 | +62.35 | 162.14 | -99.786 | -17.325 | 15dk |
| hold_30 | 9314 | +57.87 | 157.10 | -99.237 | -13.551 | 30dk |
| hold_60 | 6831 | +72.11 | 169.14 | -97.030 | -9.181 | 60dk |
Uzun hold gross'u KORUYOR/artırıyor (+47→+72, tüm variantların en yükseği) —
label-horizon uyumsuzluğu tezini destekler. Ama fee de büyüyor (cüzdan daha uzun
yaşadığı için stake'ler büyük kalıyor) → net ≈ -99 sabit. WR 0.34→0.46.

## D. H2 cooldown results
| variant | trades | gross | fee | net | sharpe |
|---|---|---|---|---|---|
| cool_00 | 15603 | +47.18 | 147.16 | -99.975 | -24.186 |
| cool_15 | 14136 | +34.79 | 134.75 | -99.956 | -22.977 |
| cool_30 | 12771 | +33.68 | 133.59 | -99.907 | -21.360 |
| cool_60 | 11216 | +36.45 | 136.20 | -99.748 | -18.947 |
Etki ihmal edilebilir düzeyde (net Δ<0.3). Cooldown, problemin faili değil.

## E. H5 re-entry results
| variant | trades | gross | fee | net | sharpe |
|---|---|---|---|---|---|
| baseline (quirk açık) | 15603 | +47.18 | 147.16 | -99.975 | -24.186 |
| reentry_off | 15639 | +43.21 | 143.19 | -99.978 | -24.092 |
Fark ≈ 0 (Δnet -0.003). Quirk GERÇEK (kodda var) ama P&L sürücüsü DEĞİL —
H5 reddedildi (etki değil, varlık doğrulandı).

## F. Fee economics
Break-even: 0.002 stake oranı. Variant bazında (actual vs gerekli):
- A: 0.0030 gross число? Hayır — oran cinsinden: fee_per_trade/stake ≈ 0.002 her
  variantta (sabit); gerekli gross oranı 0.002.
- En iyi gross/fee oranı: hold_60 (0.426), ardından hold_30 (0.368), B (0.302).
  Hiçbiri 1.0'a yaklaşamıyor: fee'yi YARIYA indirsek bile en iyi variant
  (0.426×2=0.85) kurtulmaz. Maliyet yapısı, bu sinyal kalitesinde aşılamaz.

## G. Trade-frequency vs profitability
trades/gün → net: 86.2→-100.0, 12.0→-72.7, 3.9→-45.6, 37.7→-97.0, 62.0→-99.7.
Frekans 22x düşünce net -100→-46: iyileşme var ama asimptot HÂLÂ negatif;
eğri sıfıra yaklaşmıyor, -45'te takılıyor (C'nin gross'u tükeniyor).
Yani: frekans etkisi GERÇEK ama tek başına kurtarıcı DEĞİL.

## H. En iyi execution variant
- Net'e göre: **C_60_40** (-45.633, Sharpe -1.316).
- Gross'a ve gross/fee oranına göre: **hold_60** (+72.11, oran 0.426).
- İkisi de derinden negatif. "En iyi" = en az kötü; hiçbiri viable değil.

## I. En kötü execution variant
- **A_base / hold_05 / cool_00** (aynı davranış): 15.6k trade, Sharpe ≈ -24,
  fee 147. En yüksek churn, en kötü risk-ayarlı sonuç.

## J. Model edge vs execution-cost ayrımı
- İstatistiksel edge VAR (zayıf): AUC 0.61, monoton kalibrasyon, fee-öncesi +47.
- Ekonomik edge YOK: en iyi gross/fee 0.43 < 1.0; fee sıfırlansa bile en iyi
  gross (+72/181gün) anlamsız; threshold == fee sıfır-marjlı tasarım.
- Baseline ile aynı dilden: baseline işlem-başı gross 2.7x üstün (0.0082 vs
  0.0030) ve 22x seyrek — kalite farkı gerçek, Sharpe farkını büyüten çarpan
  turnover. Model gürültülü, execution affetmiyor.

## K. Sonuç (sınıflandırma)
1. Execution filtering ile anlamlı iyileşme? Sharpe/DD sayısal iyileşiyor
   (-24→-1.3) AMA net -100→-46: anlamlı (viable) DEĞİL.
2. Fee problemi çözülünce edge mevcut mu? HAYIR — en iyi gross/fee 0.43;
   fee yarılansa bile yetmez; threshold == fee yapısal tavan.
3. Sharpe/MaxDD iyileşmesi sadece trade azaltmaktan mı? BÜYÜK ÖLÇÜDE EVET
   (varyans çöküşü) + kısmen seçicilik (WR 0.34→0.78); pozitif edge doğmuyor.
4. Hipotezler: H1 churn-azaltıcı olarak DESTEKLENDİ, kurtarıcı olarak REDDEDİLDİ.
   H2-minhold KISMEN (gross'u korur, net'i kurtarmaz). H2-cooldown REDDEDİLDİ.
   H5 sürücü olarak REDDEDİLDİ (quirk varlığı doğrulandı, etkisi ~0).

Ham tablo: `results/exec_study.csv` (12 variant). Harness: `scripts/phase36_exec_study.py`.
REPRO frozen==A: PASS (bit-identik). Final Test A'ya DOKUNULMADI.
