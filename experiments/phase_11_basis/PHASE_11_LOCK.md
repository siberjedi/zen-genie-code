# PHASE 11 — LOCK / PREFLIGHT (kilit + doğrulama; backtest YOK)

**Statü:** LOCKED SPEC + executable verification tamamlandı. Carry P&L,
Sharpe, gate SONUÇLARI hesaplanmadı (backtest işi). Tuning/threshold yok.
Holdout kapalı. Commit yok.

## Kilitli liste (12, deterministik, değişmez)

BTCUSD_200925/201225/210326/210625/210924/211231/220325/220624/220930/
221230/230331/230630 — COIN-M quarterly, vade = ilgili Cuma 08:00 UTC.
UM yedek/elenmiş alternatif (geç başlangıç); primary'e alınmaz.

## Kilitli kurallar

- **Giriş:** çeyrek-başlangıç tarihinde/doğan ilk mevcut barın close'u
  (deterministik; likidite filtresi YOK — limitations'da kayıtlı).
- **Çıkış:** settlement SAATİNDE (vade Cuma 08:00); `open_time ≥ settlement`
  barlar KESİLİR (ölü-feed); settlement-sonrası drift carry'ye YAZILMAZ.
- **Rollover:** çeyrek-sonu çıkış + yeni giriş (ücretli); eşzamanlı pozisyon
  YOK (tek kontrat).
- **Marjin:** izole, W0 = %1000 short-notional (10× mühendislik marjı, round
  sayı, gerekçeli); MMR %0.5; breach → likidasyon (kurtarma YOK).
- **Maliyet:** spot in/out taker %0.10 + perp in/out taker %0.05 (dönem
  tarifesi, belgeli) + slip nominal 2bp/fill/bacak — AYRI kalemler.
- **Muhasebe:** ters-marjin (BTC-cinsinden marjin/P&L, spot-kurla USD rapor;
  formüller sentetik-doğrulamalı).

## Verification sonuçları (PREFLIGHT11.json, 80 dosya SHA-verified)

- Süreklilik: 12/12 kontratta max gap 1.0h (kesinti YOK).
- Hizalama: UM/CM[T] ↔ spot[T+55dk] (0.89–1.00; düşük değerler erken-dönem
  likiditesizliği + ölü-kuyruk gürültüsü — ~0.09 hizasızlık-null'u reddedilir).
- Terminasyon: 8/12 settlement saatinde temiz biter; 4 dosyada ölü-kuyruk
  (uzunluğu 1h–6gün; std=0.0 DONMUŞ feed — örn. 200925: 136 bar sabit
  10687.6) → kesme kuralıyla deterministik elenir.
- Yakınsama: vade-son bar basis ±5bp (4/4 test dosyası) → mekanizma AMPİRİK.
- Marjin modeli: sentetik 2×/5×/9.58×/10× şoklarında formül-doğru
  (k=%1000 hepsinde sağkalır; oranlar monoton-azalan, beklendiği gibi).

## Uygulanabilir gate seti (önceden kilitli)

net>0 · edge/cost≥1.2 · Sharpe CI-alt>0 (çeyrek-blok bootstrap) · MaxDD≤0.20 ·
q<0.05 (tek pooled t-testi, 12 çeyrek) · power≥0.80 @ d=0.80 (carry
ekonomisi büyük-etki gerektirir — M.20-görünür gerekçe; d=0.30 gate'i
n=12'de KULLANILAMAZ ~0.25). Seed/WF: YOK (model/fold nesnesi yok —
gerekçeli N/A). AUC/IC/tau: YOK (skor yok).

## Kritik risk

Güç (n=12; yalnızca büyük-etki rejiminde karar üretir) + ters-marjin
gerçek-yol sürprizleri (sentetik-dışı likidite/teminat dinamiği) +
vade-günü yürütme (settlement penceresi kayması).

## Verdict: BACKTEST GO

Preflight STOP koşulu tetiklenmedi (kapsama/süreklilik/hizalama/terminasyon/
marjin-formülleri/gate-tanımları hepsi PASS). Backtest, bu kilit aynen
uygulanarak koşulabilir (ayrı M.20 ile).

*Kod: scripts/phase11_discover.py, scripts/phase11_verify.py,
scripts/phase11_preflight.py. Veri: data/ (keşif + 7 dosyalık verify seti +
80 dosyalık craw + manifestler). Carry P&L hesaplanmadı. Holdout kapalı.
Commit yok.*
