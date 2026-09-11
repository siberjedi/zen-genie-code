# M.20 REVIEW — 6B Lock Proposal (REVIEW, APPROVAL DEĞİL)

**Statü:** Öneri gözden geçirildi, tutarlılık notları düşüldü. M.20 APPROVED
denmedi; final onay otoritenindir.

## 1. İnceleme notları (madde madde)

1. **BASE:** E032-verbatim (B3/L1/M2/42), 6A ile aynı tanım; reprodüksiyon 6A'da
   bit-exact kanıtlı (diff 0.00e+00). Tutarlı — ek karar gerekmez.
2. **Kaynak tekilliği:** BTCUSDT perp USDⓈ-M kilitli; predicted-funding dışlama
   açık. Venue alternatifi yok — uygun (kapsama iddiası deneyde assert'li).
3. **Feature set (5):** rate / z_30 (settlement-endeksli) / sign / abs_chg /
   persist-8. Scout §B primitifleriyle birebir; 6A sonuçlarına göre ayar izi
   yok (anti-kontaminasyon §25). z-penceresi ve persist cap'i tanımlı.
4. **Horizon kararı:** primary 5m/H12 (tahmin hedefi 1h), ayrı 1h-candle
   pipeline yok. Gerekçe (§10) kayıtlı: tek-familya FDR + 6A karşılaştırılabilirliği.
   Final M.20'nin bilerek onaylayacağı/redirect edeceği nokta olarak işaretli.
5. **Incremental criterion:** ΔCI95 alt > 0 kilitli ifade; fallback yok. 6A ile aynı.
6. **Kapsam disiplini:** 15m/ikincil familya yok; exploratory gatesiz. 6A ile simetrik.
7. **Koruma:** 4 pencere kilitli + indirme aralığı assert'li + 6A-dosya bütünlüğü
   (bu faz 6A'ya yazmaz).

## 2. Final BASE (önerilen)
E032-verbatim: B3 + L1 + M2 + seed 42 + Phase-5 splitleri.

## 3. Final venue/sembol (önerilen)
Binance USDⓈ-M BTCUSDT perp funding (`/fapi/v1/fundingRate`).

## 4. Final feature set (önerilen)
§6'daki 5 feature, §7 detaylarıyla.

## 5. Final primary model (önerilen)
M2 frozen tek model; tuning yok.

## 6. Final horizon (önerilen)
Primary 5m → 1h (H=12, L1). Exploratory: L0/L2, ufuk 3/36/72, funding × rejim.

## 7. Final incremental criterion (önerilen)
§21: FULL gate zinciri + ΔCI95 alt > 0.

## 8. Protected test policy (önerilen)
§25 aynen: 4 pencere kapalı, 6A-kontaminasyon yasağı, P5 otomatik açılmaz.

## 9. Blocker taraması
- [x] Korumalar tanımlı (4 pencere + indirme aralığı)
- [x] Yeni eşik yok
- [x] Deney/indirme/fit/backtest çalıştırılmadı
- [x] 6A dosyaları değişmedi (bu fazda yazım yok — git'te teyit edilecek)
- [x] Commit/push yok
- [ ] **Final M.20 onayı (otoritede)** — tek bekleyen adım

Blocker YOK. Onay gelmeden 6B'ye ait hiçbir adım çalıştırılamaz.

**READY FOR FINAL M.20 APPROVAL**
