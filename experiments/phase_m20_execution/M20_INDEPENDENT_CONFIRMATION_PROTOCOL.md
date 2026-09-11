# M.20 INDEPENDENT CONFIRMATION PROTOCOL (tasarım; ONAY yok, koşu yok)

**Statü:** PROTOKOL TASLAĞI. Backtest/fit/download/onay/commit YOK.
**Amaç:** M.20'deki pozitif sonucun (event net +0.4435%, θ +8.75) tekrar
üretilebilir bir execution-regime edge olup olmadığını BAĞIMSIZ olarak sınamak.
Phase 7 ve M.20 frozen kalır; bu protokol onlara yazmaz.

## 1. Bağımsız veri dönemi (seçim-korumalı)

- **Primary confirmation window: 2025H1 (2025-01-01 → 2025-06-30).**
  Gerekçe: M.20'den ÖNCE belirlenmiş standing final penceresi olduğu için
  seçimi sonuç-odaklı DEĞİLDİR (tarihsel öncelik kanıtı: M20 formalization).
  Mevcut sonuçlara bakılarak A/B/C arasından seçilmedi, seçilemez.
- **Sonuç:** pencere bu amaçla TÜKETİLİR (Madde 3/4) → sonrasında yeni final
  test belirlenir (ayrı M.20; örn. 2025H2 veri birikince).
- **Alternatif kol (gecikmeli):** forward paper-trading (canlı execution
  rejiminin ta kendisi; bekleme gerektirir). Tarihsel confirmation'a ALTERNATİF
  değil TAMAMLAYICIDIR (madde 12).

## 2. Train / validation / final-confirmation ayrımı

- **Train (2020–2022):** model zaten fit; TEKRAR FIT YOK. Deterministik
  türetme + bit-exact teyit (§3) dışında dokunulmaz.
- **Validation (2023H1):** donduruldu; karar için TEKRAR KULLANILMAZ.
- **Final confirmation (2025H1):** tek değerlendirme penceresi. Etiketler
  son 48 barı keser (bound); 2025-06-30 23:55 sonrası veri YÜKLENMEZ.

## 3. Frozen artifact taşıma (refit YOK)

1. B3 feature tanımları (phase501, dosya-hash'li manifest).
2. M2 config + seed 42 + TRAIN verisi → model DETERMİNİSTİK türetilir;
   Phase-7 TRAIN skorlarıyla bit-exact (tol 1e-9) eşleşmeden confirmation
   verisine DOKUNULMAZ (reproducibility gate).
3. Eşik q90_TRAIN = 0.592775 (kayıtlı değer; yeniden-hesap eşitliği tol 1e-12).
4. Cost bileşenleri §4; funding arşivi confirmation penceresine uzatılır
   (execution-time indirme, pencere-assert'li; oranlar aynı endpoint'ten).

## 4. Frozen cost modeli

C_FIX = fee taker%0.04×2 + spread 1bp + slip 2bp/side (0.0013) + event-başı
gerçekleşmiş funding (LONG, arşivden). Venue tarife değişikliği sessizce
uygulanmaz: belgelenir, anomali sayılır; sayı değişikliği M.20 ister.

## 5. Primary metric

Yıllıklandırılmış net per-trade Sharpe θ (event-block bootstrap CI ile),
confirmation eventlerinde. Formül §7-Phase-7 ile BİREBİR aynı (λ confirmation
event hızından: N×365/181, formül sabit değer değil).

## 6. Economic gates (hepsi — tek eksik FAIL)

PSS>0 ∧ edge/cost≥1.2 (decile VE event) · AUC≥0.55 · rank-IC≥0.01 · tau>0 ·
d≥0.30 · power≥0.80 · q<0.05 (tek-test) · θ CI-alt>0 · MaxDD≤0.20 · WF≥0.60 ·
seed≥2/3 (7/123 tohumlu modeller TRAIN'de fit edilir — confirmation-verisinde
fit YOK — ve confirmation'a uygulanır).

## 7. MaxDD gate (M.20 bayrağına doğrudan cevap)

MaxDD ≤ 0.20, confirmation event-eşdeğer eğrisinde ZORUNLU gate'tir (muafiyet
yok). M.20'deki %90.1 profili bu gate ile elenirdi; confirmation'da tekrarı
otomatik FAIL üretir. Ek zorunlu rapor (gate-dışı ama yayın-dahil):
top-%1 event P&L payı (>%50 ise raporda KRIRILGANLIK bayrağı — PASS olsa bile).

## 8. Bootstrap / CI (aynen)

Event-indexed moving-block, K=500, 10k resample, seed 42, λ dondurulmuş.
n < 500 → validity STOP (mevcut assert). Unannualized per-trade Sharpe +
event dağılımı (skew/kurtosis) zorunlu rapor kalemidir (annualizationın
kuyruğu gizlemesi engellenir).

## 9. Multiple-testing kontrolü

Tek primary test (confirmation θ). θ_12 karşılaştırıcı TEKRARLANMAZ
(betimsel işi bitti; tekrarı test sayısını artırırdı). Horizon/feature
varyasyonu YASAK. Familya = 1.

## 10. Karar ağacı

STOP-koşulu (integrity/leakage/contamination/repro/power<0.80/n<500) →
**STOP** · tüm gate'ler PASS → **CONFIRMED** (replikasyon adayı statüsünden
çıkar; AMA §12 zinciri ayrıca gerekir) · herhangi gate FAIL → **NOT
CONFIRMED** (M.20 pozitifi replike olmadı; H48 hattı kapanır, retry için
taze M.20 gerekir).

## 11. Leakage kontrolleri

Causality probe · label-bound (son 48 bar kesimi) · threshold/skorların
yalnızca frozen artefakt + confirmation-barlarından gelmesi · funding arşiv
pencere-assert'i · confirmation-öncesi P5'e erken-bakış YOK (kilit zaten
kapalıydı; açılış bu protokolün M.20 onayıyla ve SADECE confirmation için).

## 12. Gerçek-para yeterliliği (açık HAYIR)

Confirmation, NECESSARY-not-sufficient koşuldur. Gerçek para için ek zincir:
CONFIRMED → forward paper-trading (Phase-10 mantığı: min süre/gözlem,
backtest/live gap, spread/latency/slippage incelemesi) → ayrı M.20'ler →
gerçek para EN SON (Madde 19). Bu protokol tek başına işlem yetkisi ÜRETMEZ.

---
*Onaylanmadan uygulanamaz. Commit/push yok.*
