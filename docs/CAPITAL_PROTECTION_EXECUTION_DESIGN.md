# Capital Protection Execution — Tasarım (Kod Yok)

> **Durum:** Sadece tasarım. `src/risk/capital.py` ve `config/capital.json` şu an yalnızca muhasebesel rezerv tutar; hiçbir `sell`/`withdraw`/`transfer` yapmaz. Bu doküman, gerçek trading aşamasında korunan kârın **fiilen trading riskinden çıkarılması** için yürütme katmanının nasıl çalışacağını tanımlar. Henüz emir/withdrawal kodu yazılmaz.

## 1. Amaç ve Kapsam

- **Amaç:** `CORE CAPITAL` (örn. 100 USDT, `config/capital.json:2` kilitli) asla risk altında kalmasın. `Equity = CORE + realized + unrealized` `CORE` üzerine çıktıkça `principal-protection threshold` oluşsun, yükseldikçe trailing ile yukarı taşınsın. Eşiğin üzerindeki kısım trading'de kalmaya devam etsin, altındaki kilitli kısım USDT rezerv olarak ayrışsın. Sistem sonunda `total_equity > CORE` net pozitif hedeflesin.
- **Kapsam dışı:** Sinyal/strateji (`BaselineStrategy.py` RSI/SMA), `VolumePairList` evren, `max_open_trades` risk limiti aynı kalır. Bu katman strateji bağımsızdır — sadece kâr muhasebesi ve bakiye ayrıştırması yapar.
- **Dry-run vs Live:** Şu an dry-run sanal; bu tasarım live `trading_mode: spot` için yürütme kurallarını tanımlar, ancak henüz uygulanmaz.

## 2. Mevcut Durum (Muhasebesel)

- `src/risk/capital.py:257` `compute_capital_view()` → `equity = core + realized + unrealized` (`_get_realized_from_db` `SELECT SUM(close_profit_abs)`, `_get_unrealized_from_db` bulk `ticker/24hr`), `HWM = max(HWM, equity)`, `locked = (HWM-CORE)*lock_ratio(0.5)`, `threshold = CORE+locked`, `reserve = locked` (trailing, asla azalmaz), `protection_history` ve `harvest_history` `data/capital_state.json` (writable `docker-compose.yml:22` `./data:/app/data`) içinde.
- `POST /api/capital/harvest` `app.py:629` sadece `state` günceller: `reserve_balance`, `total_harvested`, `last_harvest_*`. Hiçbir `ccxt.createOrder`/`withdraw` yok. `grep -r withdraw src/risk/` boş.
- Dashboard `App.tsx:261` `CORE/PROTECTION/LOCKED/RESERVE` kartı bu muhasebesel değerleri gösterir.

## 3. Kavramlar

| Kavram | Tanım | Kaynak |
|---|---|---|
| **CORE CAPITAL** | Kilitli başlangıç sermayesi, örn. 100 USDT | `config/capital.json` `core_capital`, `core_locked_at` |
| **Realized Profit** | Kümülatif `close_profit_abs` (is_open=0) | DB |
| **Unrealized PnL** | Açık pozisyonlar ` (current-open)*amount` bulk ticker | DB + Binance |
| **Equity** | `CORE + Realized + Unrealized` | Hesap |
| **HighWaterMark (HWM)** | `max(önceki HWM, Equity)` | `capital_state.json` |
| **Locked Profit** | `(HWM-CORE)*lock_ratio` trailing, asla düşmez | `capital.py` |
| **Protection Threshold** | `CORE + LockedProfit` (buffer varsa `*(1-buffer%)`) | Risk zemini |
| **Reserve Balance** | Ayrıştırılmış USDT, `LockedProfit` ile senkron | `capital_state.json` `reserve_balance` |
| **Trading Capital** | `CORE + (Realized - Reserve)` + açık pozisyonlar için kullanılabilir | Muhasebe |
| **Total Equity** | `CORE + Realized + Unrealized` | Gerçek özkaynak |

`lock_ratio=0.5` → HWM 120, CORE 100 ise `locked=10`, `threshold=110`. Equity 110→130 olursa `locked=15`, `threshold=115` yukarı taşınır.

## 4. Yürütme Modelleri — Aynı Hesap İçi Rezerv vs Ayrı Cüzdan

### 4.1 Aynı Hesap İçinde Sanal Rezerv (Önerilen İlk Aşama)
- **Nasıl:** Aynı Binance spot hesabı içinde, `freed` bakiye muhasebesel olarak ikiye ayrılır: `trading_available = wallet * tradable_ratio - reserve`. Freqtrade'e `available_capital = TRADING_CAPITAL` gibi gösterilir; reserve kısmı `stake_amount` hesabından düşülür. Hiçbir zincir üstü transfer yok, sadece `capital_state.json` + `available` limiti.
- **Artı:** Hızlı, fee yok, açık pozisyon varken bile uygulanabilir, geri alınabilirlik kolay (`reserve → trading` tek satır state değişimi).
- **Eksi:** Gerçek borsa bakiyesi hâlâ tek cüzdanda; borsa iflası/ API hatası tümünü etkiler.
- **Uygun:** Faz 10 paper → Faz 11 küçük gerçek para geçişi için ideal.

### 4.2 Ayrı Cüzdan / Alt Hesap (Gelecek, Daha Güvenli)
- **Nasıl:** `reserve_currency: USDT` ayrı bir Binance sub-account, funding wallet veya soğuk cüzdana `withdraw`/`transfer` ( `POST /api/v3/capital/withdraw` veya `sapi/v1/capital/transfer` ). `harvest()` içinde `ccxt.withdraw()` veya `ccxt.sapiPostCapitalTransfer`.
- **Artı:** Gerçek risk ayrışması, borsa içi riskten izole, muhasebe + zincir üstü mutabakat.
- **Eksi:** Fee, minimum withdraw limiti, açık pozisyon varken USDT çekmek marjin/teminat sıkıntısı, transfer geri alımı gecikmeli, ek KYC/API izni (`withdraw` yetkisi) güvenlik riski.
- **Uygun:** Faz 11 sonrası, kâr istikrarlı ve `Equity >> CORE` olduğunda.

**Karar:** İlk canlı fazda **4.1 Sanal Rezerv** ile başla, `reserve` sadece `available` limiti olarak çalışsın. `4.2` için `config/capital.json` içinde `execution.mode: "virtual"|"sub_account"` bayrağı ekle, kod henüz yazılmasın.

## 5. Ne Zaman Ne Kadar Ayrılır?

### 5.1 Koşul (Tetikleyici)
- **Equity tabanlı trailing (önerilen):** `Equity > HWM` → yeni HWM → `new_locked = (HWM-CORE)*lock_ratio` → `incremental_locked = new_locked - prev_locked` > `dust` (örn. 0.10 USDT) ise ayrıştır.
- **Alternatif gerçekleşmiş tabanlı:** Sadece `Realized` arttığında (kapalı trade) ve `period` (`daily`/`weekly`) dolduğunda `pending = (Realized - last_harvest_realized)*ratio`. Daha muhafazakâr, unrealized balonunu rezerve almaz.
- **Seçilen:** **Equity HWM** (user isteği: equity üzerine çıktıkça threshold oluşsun). `unrealized` dahil olduğu için açık pozisyon kârı da koruma hesabına girer, ama fee/slippage riski için `buffer_pct` (örn. 1-2%) veya `lock_ratio <1` kullanılır.

### 5.2 Miktar
- `harvest_amount = incremental_locked` (HWM farkının kilit oranı kadar). Örn. CORE 100, HWM 100→110 (+10), `lock_ratio 0.5` → `+5` rezerve.
- **Parçalı:** Tek seferde tüm incremental değil, `ratio` kadar. `ratio=1.0` tam principal protection (tüm kâr üzeri kilit), `0.5` yarısı trading'de kalır, büyüme için kullanılır (user: "üzerindeki kısım trading için kullanılmaya devam edebilsin").
- **Dust eşiği:** `incremental_locked < 0.10 USDT` ise beklet, bir sonraki HWM'de birleştir.

### 5.3 Periyot
- `protection.trailing=true` ise her yeni HWM'de anında (her `compute_capital_view()` çağrısında, 5sn poll). `harvest.period` günlük/haftalık ise sadece o periyotta `should_harvest` true olunca uygula. İlk canlıda `trailing` anında + `daily` mutabakatı birlikte.

## 6. Açık Pozisyon Varken Davranış

- **Unrealized dahil HWM:** Açık pozisyon kârı `unrealized` ile `equity` yükselirse HWM artar ve `locked` artar → rezerv artar, ancak **henüz gerçekleşmemiş** kâr rezerve alınmış olur. Bu, fiyat geri çekilirse rezerv fazla kilitlenmiş olabilir.
- **Çözüm:** İki katmanlı:
  1. **Soft lock (unrealized):** `equity` tabanlı `locked` hesaplanır, `protection_threshold` yükselir, ama `reserve` henüz **fiziken ayrılmaz**, sadece eşik olarak gösterilir. Dashboard `distance = equity - threshold` ile core'un ne kadar üstünde olunduğu görülür.
  2. **Hard reserve (realized):** Sadece `close` olup `realized` arttığında, `locked` kadar kısım **fiilen** `available`'dan düşülür ve `reserve` artar. Bu sayede açık pozisyon varken erken rezerv şişmesi önlenir.
- **Örnek:** HWM 110 (unrealized 10), `locked 5`, `threshold 105`. Henüz trade kapanmadı → `reserve` 0, `threshold` 105 olarak izlenir. Trade kapanıp `realized +10` olunca `harvest` → `reserve +5` fiili ayrışma. Eğer fiyat 105'e geri düşerse `equity 105` hala `threshold 105` üzerinde, core korunur.

**Kural:** `reserve_balance <= min(locked_profit, realized_profit * lock_ratio + buffer)` — asla `realized`'den fazla rezerve alınmaz.

## 7. Geri Alınabilirlik (Reversibility)

- **Sanal rezerv (4.1):** Tek yönlü trailing değil, **geri alma izni** config ile: `protection.reversible: false` default. `false` ise `locked` asla azalmaz, rezerv geri trading'e aktarılmaz — en muhafazakâr, `net_positive` hedefi için ideal. `true` ise drawdown'da `reserve → trading` aktarılabilir, ama core koruması delinir.
- **Önerilen:** `reversible: false` kilitli kalsın. Acil durumda manuel `POST /api/capital/unlock {amount}` (yeni endpoint, henüz kod yok) ile `reserve` azaltılıp `trading` artırılabilir, `protection_history`'de `manual_unlock` olarak loglanır, `lock_ratio` geçici düşürülür.
- **Ayrı cüzdan (4.2):** Geri alma `sub_account → spot` `transfer` ile, fee ve 1-2 blok onayı gecikmesi var, bu yüzden `reversible: false` daha da önemli.

## 8. Konfigürasyon (Öneri)

```json
// config/capital.json
{
  "core_capital": 100,
  "core_locked_at": "2026-08-31T00:00:00Z",
  "protection": {
    "lock_ratio": 0.5,
    "trailing": true,
    "mode": "equity_highwater",
    "buffer_pct": 0,
    "reversible": false
  },
  "execution": {
    "mode": "virtual", // "virtual" | "sub_account"
    "sub_account_id": null,
    "auto_withdraw": false,
    "min_harvest": 0.5,
    "note": "virtual: aynı hesap içinde available limiti düşer; sub_account: gerçek transfer"
  },
  "harvest": {
    "ratio": 0.5,
    "period": "daily",
    "threshold": 1.0,
    "auto_enabled": false
  }
}
```

## 9. Durum ve Kalıcılık

- `data/capital_state.json` (writable `docker-compose.yml:22` `./data:/app/data`) — tek kaynak, diğerleri yedek:
```json
{
  "core_capital": 100,
  "high_water_mark": 110,
  "locked_profit": 5,
  "protection_threshold": 105,
  "reserve_balance": 5,
  "total_harvested": 5,
  "last_harvest_at": "2026-08-31T00:00:00Z",
  "protection_history": [{"timestamp","equity","high_water_mark","locked_profit","threshold","incremental_locked"}],
  "harvest_history": [...]
}
```
- `high_water_mark` ve `locked_profit` trailing ile sadece artar.

## 10. Yürütme Akışı (Dry-run vs Live)

**Dry-run (şu an):**
1. `GET /api/capital` → `compute_capital_view()` HWM ve threshold hesaplar, `state` günceller (sadece dosya), hiçbir emir yok.
2. Dashboard `AÇIK POZİSYONLAR` ve `CORE CAPITAL & REZERV` kartlarında `equity`, `threshold`, `distance`, `core_protected` gösterir.
3. `POST /api/capital/harvest` manuel tetik — yine sadece `capital_state.json` artar.

**Live (gelecek, kod yok):**
1. Aynı `compute` sonrası `if mode=="virtual"` → `available_capital = total_equity - reserve` gibi Freqtrade `stake_amount` hesabını sınırlayan bir `available` değeri döndürülür (Freqtrade `custom_stake_amount` hook'una bağlanabilir, ama strateji bağımsız kalması için ayrı `risk` modülü sadece `max_stake` limiti verir).
2. `if mode=="sub_account" && auto_withdraw` → `capital.py: harvest()` içinde `ccxt` `transfer`/`withdraw` çağrısı eklenir, `amount = incremental_locked`, `from=spot`, `to=sub_account`, `fee` ve `min_withdraw` kontrolü, `dry_run` ise `log only`.
3. Açık pozisyon varken `mode=="sub_account"` ise **bekle**: sadece `equity` eşiği güncellenir, gerçek transfer `realized` artana kadar ertelenir (6. bölüm kuralı).

## 11. Güvenlik ve Hata Durumları

- Borsa `withdraw` yetkisi ayrı API key, `LIVE_TRADING=DISABLED` iken asla çağrılmaz (`docker-compose` `LIVE_TRADING` env).
- `reserve` hiçbir zaman `realized`'i geçemez, `core` asla azalmaz.
- `high_water_mark` geriye gitmez — drawdown'da threshold sabit kalır, core korunur.
- Dosya yazma atomik `tmp → replace`, `STATE_PATHS_ALL` ile yedekli.

## 12. Test Planı (Kod Yok, Sadece Dry-run Simülasyon)

1. `TRADES` tablosuna sanal `close_profit_abs` ekle (örn. +10 USDT) → `GET /api/capital` → `equity 110, HWM 110, locked 5, threshold 105, reserve 5` bekle.
2. Fiyat geri çekilip `equity 106` olunca `threshold 105` sabit kalmalı, `status protected` kalmalı.
3. Yeni HWM 120 → `locked 10, threshold 110` artmalı, `reserve` 10 olmalı.
4. Zarar `equity 95` (<CORE) → `core_protected false`, `status at_risk` — alarm.
5. `reversible:false` iken manuel `unlock` denenirse reddet.

## 13. Sonraki Adım — Kod Yok

Bu doküman onaylanmadan `capital.py` içine `ccxt.withdraw` veya Freqtrade emri eklenmeyecek. Onay sonrası `execution.mode` ve `protection.reversible` bayraklarıyla implemente edilecek.
