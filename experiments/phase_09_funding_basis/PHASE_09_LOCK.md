# PHASE 9 — LOCK / PREFLIGHT (kilit + doğrulama; backtest YOK)

**Statü:** LOCKED SPEC + executable verification tamamlandı. Backtest
çalıştırılmadı; tuning/threshold yok; holdout kapalı; commit yok.

## Lock spec (L1–L9, bağlayıcı)

- **L1 delta hedge:** +1 BTC spot / −1 BTC perp (BTC-birim); beta ≡ 0 yapısal.
- **L2 funding:** settlement'te pozisyon açıksa oran uygulanır (LONG öder/alır);
  8h grid aralık-doğrulamalı (pencerede değişiklik YOK — kanıtlandı).
- **L3 basis:** giriş-çıkış farkı, funding'den AYRI kalem.
- **L4 execution:** 4 fill (spot in/out taker %0.10, perp in/out taker %0.04) +
  slip nominal 2bp/fill/bacak, AYRI kalemler.
- **L5 margin:** izole, W0 = k×notional, k ∈ {%100, %200, %500} (preregistered
  senaryolar, hepsi raporlanır — seçim YOK); funding wallet'a swept; MMR %0.5;
  breach → likidasyon (kurtarma YOK). 10x spike testi zorunlu.
- **L6 capital:** spot-nakit / futures-wallet / funding-ledger / basis /
  unrealized AYRI defterler.
- **L7 rejim:** 2020/2021/2022/2023H1 ayrı (2022 saklanmadı).
- **L8 metrik:** net carry, yıllık, vol, MaxDD, liq events, funding/basis/cost
  katkıları.
- **L9 STOP:** muhasebe-dogrulanamazsa / hedge-bozulursa / margin-modeli
  güvenilmezse / maliyet-sonrası carry ekonomik değilse STOP.
- **Hizalama kuralı:** UM[T] ↔ spot[T+55dk] (eşzamanlı close; corr(diff)~0.999
  kanıtlı; +0 kaydırma ~0.09 verir — YASAK). Assert: corr>0.99 else STOP.

## Verification sonuçları (PREFLIGHT.json, kod: phase9_preflight.py)

- Delta beta = 0.0017 (≈0) → hedge DOĞRULANDI.
- Funding grid 8h pencerede SABİT (3.829 settlement) → interval riski YOK.
- Ledger (3.5y, 1 BTC çifti): funding +$19.7k, basis −$2, fee $52.7, slip
  $15.1 → toplam **+$19.7k**. Scout defteriyle mutabık (%0.2 içinde).
- Rejimler: 2020 +$2.2k / 2021 +$15.3k / 2022 +$1.3k / 2023H1 +$0.9k.
- **Margin (kilit bulgu):** tarihsel excursion 9.58× (giriş $7.172 → tepe
  $68.715). k=%100 → likide Kas-2020 @ $15.9k; k=%200 → Ara-2020 @ $23.3k;
  k=%500 → Şub-2021 @ $48.2k. **10x spike: üç senaryoda da ÖLÜM**
  (sağkalım için k ≳ %900 gerekir).
- Günlük MaxDD $149.7 (ölü-öncesi defter).

## Verdict: backtest STOP

Kilitli STATİK tasarım (sabit teminat, top-up yok, kurtarma yok) tarihte
ölür — %500 teminat bile Şub-2021'i göremez. Ölü bir tasarımın backtest'i
bilgi üretmez; dinamik teminat kuralları ise yeni parametre = tuning alanıdır
(bu lock'ta YOK, ayrı M.20 ister). STOP koşulu ("carry ekonomik değilse"nin
ötesinde: **tasarım sağkalamıyor**) tetiklendi.

## Takip zarfı (tasarım DEĞİL, sınır-koşullar — ayrı M.20'ye)

- Statik sağkalım sınırı: k ≳ 9× + funding (tarihsel 9.58× excursion).
- Dinamik teminat yönetimi (sweep/top-up/kısmi-kapatma kuralları) yeni
  preregistrasyon gerektirir; bu belgede tasarlanmadı.
- Venue/karsi-taraf riski (FTX-Kas-2022 emsali) her tasarımda ayrı kalem kalır.

*Kod: scripts/phase9_scout.py, scripts/phase9_preflight.py. Veri: data/
(42 UM zip SHA-verified + funding arşivi). Holdout kapalı. Commit yok.*

## CLOSURE (frozen kayıt; sonuçlar değişmedi)

**Phase 9 KAPANDI (BACKTEST STOP).** Retry/tuning/varyant/rescue YOK.
Bu belge frozen kayıttır; yukarıdaki sayılara dokunulmadı.
