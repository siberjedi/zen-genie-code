# NEXT PHASE DESIGN — Phase 11: Dated-Futures Basis Convergence (tasarım; ONAY/koşu YOK)

**Statü:** TASLAK v3 (v1 funding-carry → phase_09_funding_basis frozen;
v2 calendar → phase_10_calendar CLOSED). Backtest/fit/onay/commit YOK.
H48, carry, calendar hatları KAPALI; rescue YOK.

## 1. Hipotez

Vâdeli (quarterly) BTC futures kontratları vade-sonunda spot'a YAKINSAR
(sözleşmesel); vadeye kalan sürede gözlenen prim (basis), tüm maliyetler
(fee/spread/slip + teminat-sürüklenmesi) düşüldükten sonra pozitif
cash-and-carry getirisi bırakır. Getiri kaynağı tahmin DEĞİL, sözleşmesel
yakınsama + giriş-primidir.

## 2. Mekanizma (neden farklı?)

- Yön-tahmini YOK (H48/6A/6B/6C/10'dan ayrışır); ML/skor/eşik YOK.
- Açık-uçlu prim bahsi DEĞİL (Phase 9'dan ayrışır): perp funding hiç
  yakınsamayabilir; quarterly basis vade-gününde SIFIRLANIR (matematiksel).
  Risk profili farklıdır (süre-sınırlı maruziyet vs açık-uçlu taşıma).
- Ortak probleme doğrudan cevap: tahmin→ticaret dönüşümü GEREKMEZ —
  edge, girişte GÖZLENEBİLİR prim − kilitli maliyetler Call sidesidir;
  turnover çeyreklik roll ile sınırlıdır (yılda ~4).

## 3. Veri (feasibility-gate'li)

Mevcut: spot 5m. Gereken (henüz indirilmedi): Vision quarterly klines
(USDⓈ-M BTCUSDT quarterly + COIN-M BTCUSD quarterly, 2020–2023H1) +
settlement kuralları. **Scout STOP koşulu:** çeyreklik tarihçe kesintisiz
değilse (sembol değişimi/boşluk) STOP — ikame YOK.

## 4. Feature/sinyal

Sinyal YOK. Kural: her çeyrek başında (likidite eşiğiyle: ilk 5 işlem günü
içi, preregistered) eğer yıllıklandırılmış prim > maliyet+marj ise gir
(değilse O ÇEYREK PAS GEÇ — bu bir threshold DEĞİL, muhasebe kararı;
eşik değeri scout'ta değil lock'ta kilitlenir, M.20 ile).

## 5. Horizon

Tutuş = vadeye kadar (≤3 ay); değerlendirme çeyrek-bazında realize getiri.
Bar-H YOK.

## 6. Execution/cost modeli

4 fill (spot in/out, futures in/out; taker tarifeler dönem-belgeli) + slip
nominal + teminat-maliyeti (fırsat-maliyeti raporlu, getiri teminat-tabanına
bölünür). Rollover maliyeti ayrı kalem. Sayılar lock'ta kilitlenir.

## 7. Train/validation/final-test planı

Parametre YOK → validation-split GEREKMEZ: test penceresi tam 2020–2023H1
(çeyrek sayısı ~14 → güç hesabı lock'ta; zayıfsa STOP). Holdout'lara
DOKUNULMAZ; final-confirmation ayrı M.20 ister. A/B/C kapalı.

## 8. Primary metric

Çeyrek net carry (maliyet-dahil, teminat-tabanlı getiri) + yıllıklandırılmış
ortanca; MaxDD (çeyrek-eşdeğer eğri); CI (çeyrek-blok bootstrap — n küçük,
geniş CI beklenir, dürüst raporlanır).

## 9. Economic gates (mevcut sayılar)

net>0 ∧ Sharpe-türü CI-alt>0 ∧ MaxDD≤0.20 ∧ power≥0.80 ∧ tek-test q<0.05.
n=14 ile güç KRİTİK engeldir (d=0.30'da yetersiz kalırsa STOP — FAIL değil).
Yeni threshold YOK.

## 10. Stop koşulları

Çeyreklik tarihçe eksik · basis verisi bütün değil · güç yetersiz ·
leakage (vade-dışı bilgi) · contamination · reprodüksiyon (deterministik
muhasebe: bit-exact) · net≤0 (FAIL, ayrı).

## 11. Leakage kontrolleri

Kararlar yalnızca t−vadesi-bilgisiyle (prim o anda GÖZLENEBİLİR — lookahead
yok); settlement/vade takvimi kamusal; causality probe; ileri-fill YOK.

## 12. Multiple-testing planı

Tek primary (tüm-çeyrek havuzu). Vade-bazında alt-test YOK (FDR-dışı bile
raporlanmaz — n=14'te dilimleme fishing'dir). Sembol-seçimi (UM vs CM)
önceden TEK'e indirilir (likiditeye göre, scout'ta belgeli).

## 13. Başarılı olursa sonraki adım

Forward paper (vade-takvimi gereği min 2 çeyrek gözlem) → ayrı M.20'ler →
gerçek para EN SON. Başarısızlıkta hat KAPANIR (çeyreklik uzay sabittir).

---
*Tasarım donduruldu; scout-onay/koşu ayrı M.20 ister. Commit yok. Önceki
hatların kapalı durumları değişmedi.*
