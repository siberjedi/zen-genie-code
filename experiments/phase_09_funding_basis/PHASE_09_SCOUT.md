# PHASE 9 — SCOUT (funding/basis carry; karar YOK, işlem YOK)

**Kapsam:** Tanımlayıcı muhasebe (ML/tuning/threshold YOK). 1 BTC çifti,
long-spot + short-perp, giriş 2020-01-01, çıkış 2023-06-30, always-on.
Veri: spot 5m (mevcut) + UM 1h (42 dosya, sha-verified) + 6B funding arşivi.
Holdout kapalı.

## 1. Veri coverage
UM 30.648 bar (2020-01-01 → 2023-06-30 23:00); spot-grid hizalama %99.79
(30.585/30.648; 63 dağınık eşleşmeme, iki tarafta da sistematik boşluk yok).
Funding 3.831 settlement tam. STOP koşulu oluşmadı.

## 2. Ortalama funding
+1.45bp/8h (medyan ~2.9bp/gün değil — günlük ort ~4.35bp; dağılım sağa çarpık,
min −285bp/gün, maks +409bp/gün). Pozitif gün oranı ~%86. Yıllık funding
nakdi/BTC: 2020 ~$2.2k, 2021 ~$15.3k, 2022 ~$1.3k, 2023H1 ~$0.9k.

## 3. Basis davranışı
Başlangıç −$8.2, bitiş −$18.7, ortalama +$3.6; dönem basis P&L'i −$10.5
(taşınan 1 BTC başına — ihmal edilebilir mertebe, işaret stabil değil).

## 4. Tahmini net carry (1 BTC çifti, 3.5 yıl)
Funding +$19.745 − basis −$10 − fee $52.7 − slip $15.1 = **+$19.667**.
Yıllıklandırma NOTU: defterdeki %78.4 giriş-notionaline bölünmüş şişkin
orandır; dürüst ölçü dağıtılmış-ortalama notional (~$28.4k) ile **~+%19.9/yıl**
(fee/slip sonrası, margin-öncesi). Funding-only maxDD ~$138/BTC
(basis-MTM hariç; defter maxDD $3.001).

## 5. Ana riskler
- **Margin/likidasyon:** short bacak 2020→2021 ~10× spike'ında devasa teminat
  ister; getiri teminat-tabana bölünür; squeeze kuyruğu primin bedelidir.
- **Rejim:** 2022 ayı-funding'i (+$1.3k/yıl) primin garanti olmadığını gösterir.
- **Venue:** borsa/karsi-taraf riski (FTX-Kas-2022 emsali), halt/depeg kuralları lock ister.
- **Geçmiş-performans:** tanımlayıcıdır, tahmin değildir; prim sıkışabilir.
- Marjinal not: UM-son-23-bar spot eşleşmemesi (son gün kısmi) sonucu değiştirmez.

## 6. Karar: GO (lock-önerisine devam; işleme DEĞİL)

Veri tam, net carry maliyet-sonrası güçlü pozitif, riskler lock'lanabilir
nitelikte (margin/halt/venue kuralları). STOP koşulu (eksik veri / net≤0 /
yönetilemez risk) oluşmadı.

**READY FOR M.20 LOCK PROPOSAL**
