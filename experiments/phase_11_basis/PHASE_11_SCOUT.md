# PHASE 11 — SCOUT (quarterly tarihçe doğrulaması; carry HESABI YOK, backtest YOK)

**Kapsam:** Veri yeterliliği. 7 dosya indirildi (checksum-verified) + HEAD
taraması (336 probe). Carry P&L hesaplanmadı. Holdout kapalı. Commit yok.

## 1. Coverage (14-çeyrek iddiası DÜZELTİLDİ)

- **COIN-M (BTCUSD_YYMMDD): 12 çeyrek** (2020Q3–2023Q2). Sözleşme vadesinden
  ~6-7 ay önce listelenir (2-çeyrek rolling); dosyalar listing→vade ARALIKSIZ
  (n == ay-aralığı her sözleşmede). 2020Q1–Q2 hiçbir venue'de YOK.
- **USDⓈ-M (BTCUSDT_YYMMDD): ~9 tam çeyrek** (2021Q2+; Mar21 kısmi — listeleme
  Mar-16). Sözleşme ~3-4 ay önce listelenir (1-çeyrek rolling).
- **Birincil öneri: COIN-M** (kapsama + n; ters-marjin muhasebesi lock'ta
  modellenir). UM yedek/elenen alternatif (geç başlangıç).

## 2. Kontrat sayısı

Kilitli tasarım için kullanılabilir n = **12 (CM)**. UM ile 9. "14" YOK —
güç hesabı buna göre revize edilmeli (aşağıda).

## 3. Veri kalitesi

- Checksum %100 (7/7 dosya). Grid sürekliliği: vade-ayı dosyaları vade
  saatine kadar TAM (CM Mar21: 609/609 bar → 26-Mar 08:00'de KESİLİR —
  settlement'te temiz terminasyon, ölü-sözleşme çöpü YOK).
- UM Mar21 ilk dosya kısmi (listeleme Mar-16 — beklendiği gibi, gap DEĞİL).
- Hizalama: UM/CM[T] ↔ spot[T+55dk] (corr(diff) 0.966–0.998; erken-dönem
  düşük değerler likidite-kaynaklı, hizalama-dışı değil).
- Anomaliler AÇIKLANDI (aşağıda); integrity STOP koşulu oluşmadı.

## 4. Basis veri yeterliliği + settlement mekanizması

- **Sözleşmesel yakınsama DOĞRULANDI:** vade-son bar basis: CM Ara22 −4.4bp,
  CM Haz23 −1.6bp, UM Ara22 +5.3bp, UM Haz23 −2.3bp (hepsi ±5bp bandında).
- CM Mar21 −68bp: settlement-SONRASI spot drift'i (08:00 settlement barı vs
  08:55 spot) + vade-sabahı volatilitesi — settlement BAŞARISIZLIĞI DEĞİL
  (dosya settlement saatinde temiz biter). Lock'a vade-günü çıkış kuralı
  notu düşüldü (settlement'ta çık, sonrasında ölçme).
- UM Mar21 +828bp: vade-SONU değil, Mar-31 ara-bar (3-ay vadeye %8 prim ≈
  %32 yıllık — 2021-boğa rejiminde GERÇEK, trade-edilebilir prim; carry
  ekonomisinin varlık kanıtı, sinyal DEĞİL).
- Fee girdileri mevcut (spot taker %0.10; CM taker %0.05, maker %0.01 —
  lock'ta belgelenecek).

## 5. Kritik risk (güç + ters-marjin)

- **Güç:** n=12, d=0.30'da güç ~0.27 → kilitli d≥0.30/power≥0.80 gate'i
  KARŞILANAMAZ. Çözüm yolu (lock'a, M.20 sahipliğinde): carry ekonomisi
  gereği minimum-ilginç etki BÜYÜKTÜR (prim, maliyet+teminat-sürüklenmesini
  katlamazsa yatırım yapılamaz) → testi d≈0.8 bandında güçlendirmek
  (n=12'de ~0.87) İLKESEL olarak savunulabilir; değilse STOP.
- **Ters-marjin:** CM short teminatı/marjin BTC-cinsinden; USD muhasebe
  dönüşümü deterministik modellenmeli (lock işi).
- **Vade-günü:** çıkış settlement'ta (sonrası ölçülmez).

## 6. Karar: GO (lock-önerisine; koşula bağlı)

Veri YETERLİ (12 çeyrek kesintisiz, yakınsama ampirik, hizalama kanıtlı).
Koşul: lock, güç-engeline açık cevap vermeli (büyük-etki hedeflemesi M.20
onaylı + ters-marjin muhasebesi + vade-günü kuralı); aksi halde o aşamada STOP.

*Kod: scripts/phase11_discover.py, scripts/phase11_verify.py. Veri: data/
(keşif manifesti + 7 dosyalık verify seti + verify_quarterly.json).
Carry P&L hesaplanmadı. Holdout kapalı. Commit yok.*
