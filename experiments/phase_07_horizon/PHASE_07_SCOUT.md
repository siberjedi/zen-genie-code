# PHASE 7 — HORIZON SCOUT (tasarım; deney/fit/backtest YOK)

**Statü:** SCOUT. M.20 değişikliği yok, onay yok, holdout kapalı, commit yok.
**Tez:** kısa-vadeli tahmin edilebilirlik 5m/~30bp altında ekonomik değil;
edge daha uzun tahmin/tutuş ufuklarında + düşük turnover ile ekonomikleşebilir.

## 1. Horizon–cost kanıtı (Phase 5/6, kayıtlı sonuçlar)

Üç bağımsız koşuda aynı monoton gradyan (FULL-L1 skorları, keşifsel, refit yok):

| h (5m bar) | 6A edge | 6B edge | 6C edge |
|------------|---------|---------|---------|
| 3 (15dk) | −0.924 | −0.928 | −0.932 |
| 12 (1h) | −0.720 | −0.721 | −0.725 |
| 36 (3h) | −0.108 | −0.135 | −0.142 |
| 72 (6h) | +0.350 | +0.320 | +0.274 |

Okuma: brüt hamleler ufukla büyürken gürültü daha yavaş büyüyor; maliyet sabit
(30bp). h=72 henüz gate-altı (+0.35 < 1.2) ama işaret değişimi üç koşuda da
aynı. Phase 4.18 eğrisi de uzun ufukta drift-yönlü pozitife dönüyordu (farklı
metodoloji, destekleyici bağlam). **Bu tablo seçim gerekçesi DEĞİL, tutarlılık
notudur** (aşağıda fishing-koruması var).

## 2. Ufuk değerlendirmesi (1h / 4h / 12h / 24h)

- **1h (H=12):** status quo; test edildi, kapandı. Yeni soru üretmez.
- **4h (H=48) — ÖNERİLEN:** (a) feature-ölçek uyumu: B0 ret_36/ret_72 zaten
  3–6h bağlam görür; hedef, feature'ların ana dilindedir; (b) funding-yarım
  döngüsü (8h/2) — yerleşim-arası birikim için ekonomik mikro-hikaye, funding
  feature'ı gerektirmez; (c) H=12'ye en yakın geçerli aday (en küçük ekstrapolasyon);
  (d) 71/72'ye göre hafifçe daha iyi efektif bağımsızlık.
- **12h (H=144):** settlement + seans-devir mekanizmaları gerekir → mevcut
  frozen feature'larla temsil edilmez → §6 sıralamasını bozar (önce feature,
  sonra ufuk — tersi yasak). Ertelendi.
- **24h (H=288):** günlük-döngü hikayesi feature setinde YOK; rank-IC çürümesi
  en sert burada beklenir; aynı sıralama-ihlali. Ertelendi.
- **Neden 72 değil (kilit nokta):** keşifsel tepe 72'de; 72'yi seçmek ipucuna
  uymak olurdu. 48, ipucun YANINDA ama üstünde değil — seçimin mekanizma-odaklı
  olduğunun kanıtı. **Tek ufuk: H=48. Fallback YOK.**

## 3. Prediction vs holding horizon (karıştırmama kaydı)

PSS çerçevesi gereği değerlendirme = "top-decile'ı al, H tut, bir round-trip
öde" — tahmin ufku ile tutuş ufku deneyde ÖZDEŞTİR (H=48 ikisi birden).
Strateji-katmanı tutuş politikası (rotasyon, yeniden-giriş) bu deneyin dışıdır;
sinyal churn/otokorelasyon yalnızca betimsel raporlanır, gate üretmez.

## 4. Turnover / fee-drag

Per-trade maliyet sabit (C=0.003); fayda, işlem-başı brüt hamlelerin büyümesinden
gelir (maliyet indirimi varsayılmaz). Turnover-azalması ÖNSAYILMAZ — churn
ölçülür ve raporlanır; hipotez "daha büyük hamle, aynı maliyet" üzerinedir.

## 5. Slippage/fee (uzun ufuk)

C=0.003 aynen kilitli (muhafazakar; indirim M.20'siz YOK). Sinyal-seviyesi
testte fill-aciliyeti yoktur; haber-çarpanı uygulanmaz (haber verisi yok).

## 6. Aynı feature setle başlama (metodolojik avantaj)

B3 frozen ile ufuk sorusu izole edilir (yeni-bilgi karıştırıcısı yok).
H48 FAIL → null temizdir ("yanlış feature" bahanesi yok).
H48 PASS → atıf ufka aittir (fishing değil). Yeni feature SADECE H48
sonucundan SONRA, ayrı kararla gündeme gelir.

## 7. BASE yeniden-tanımı (preregistered, değişiklik değil)

BASE-7 = B3 + L1@H48 + M2 + seed 42 + aynı splitler (yeni deneyin referansı;
Phase-5 E032'ye dokunulmaz). Tek primary test hücresi (FDR familyası =
1 test; BH trivial).

## 8. Preregistrasyon paketi (M.20 lock'a girecekler)

Label H=48 (off-by-one/label-bound aynen; son VAL satırı 2023-06-29 23:55,
etiketler 2023-06-30 23:55'i aşmaz — korumalı veri gerekmez); execution =
close'ta sinyal, hold-H realizasyonu; cost C; metrik/gate zinciri aynen;
3-seed + WF koşullu; **blok-bootstrap (48-bar blok) CI önerisi** (örtüşen
etiket otokorelasyonu; i.i.d. bootstrap CI'yı daraltır — yön: muhafazakar;
makine-değişikliği M.20'ye ait).

## 9. Tek primary horizon

H=48. "Birkaç ufuk deneyip en iyisini seçmek" YOK. H48 FAIL → ufuk hattı
KAPANIR (12h/24h retry, taze gerekçesiz açılamaz).

## 10–11. Split/holdout

TRAIN/VAL aynen; P5/B/C/A kapalı. VAL kaybı ~36 satır (bound), ihmal edilebilir.

## 12. Başarı kriterleri (protokol-uyumlu)

Gate zinciri aynen (PSS>0, edge≥1.2, destek, d/power, q, WF) + 3-seed; güç
n_top≈5.1k ile korunur (blok-bootstrap altında yeniden hesaplanır).

## Yeni soru mu, retry mi? (net cevap)

İKİ ÖGE DE VAR — ama yeni-soru niteliği ağır basar: farklı estimand (4h-swing
öngörülebilirliği ≠ 1h-mikroyapı), mekanizma-güdümlü seçim (ücret-amortismanı +
özellik-ölçek uyumu), tek-atış taahhüdüyle yanlışlanabilir (H48 fail = hat
kapanır). Fishing-koruması: ipucu-tepe (72) seçilmedi + fallback yok + blok
itirafı yukarıda. M.20 bunu bilerek onaylar/onaylamaz.

## Karar

**A) PHASE 7 EXPERIMENT JUSTIFIED** — tekil H=48 deneyi, yukarıdaki
koşullarla (aynı feature, aynı cost, aynı gate'ler, blok-bootstrap CI,
no-fallback, holdout'lar kilitli).

**READY FOR M.20 DESIGN**
