# M.20 REVIEW — 6C Lock Proposal (REVIEW, APPROVAL DEĞİL)

**Statü:** Öneri gözden geçirildi. M.20 APPROVED denmedi; final onay otoritenindir.

## 1. İnceleme notları

1. **Feature set (5):** chg_12 / z_288 / price-div / chg_1 / range_288 — scout
   YES-primitifleriyle birebir (değişim, z-score, divergence); oran-kolonları
   ve value-proxy dışlama gerekçeli. Flat-gün 0.5 kuralı disambiguation olarak
   kayıtlı (M2-duyarsız değil ama deterministik; raporda notlu).
2. **Dedup kuralı:** exact ve deterministik (erken-gün kazanır + artık-dup STOP).
3. **Train-loss kriteri:** n_train ≥200k + VAL kayıp-sıfır, aksi STOP. Splitler sabit.
4. **Fallback kilidi:** ücretli kaynak primary dışı; çöküşte STOP (otomatik ikame yok).
5. **Kapsam disiplini:** 6A/6B ile simetrik (tek familya, M2 tek, 5m/H12/L1).
6. **Koruma:** 4 pencere + indirme aralığı + 6A/6B-dosya bütünlüğü + anti-kontaminasyon.
7. **Belirsizlik kaydı:** OI başlangıç tarihi ayna-kanıtı (~2020-09-10); kesin
   teyit run-time §10-5 gate'inde. Tarih >2020-09-30 çıkarsa STOP (tasarım çökmez,
   koşu durur — doğru fail-safe).

## 2–8. Final önerilenler (kilit ifadeler §-referanslı)
- BASE: E032-verbatim (§4). Venue: BTCUSDT USDⓈ-M Vision metrics (§5).
- Feature: §6'daki 5 familya, §7 detaylarıyla. Model: M2 frozen (§14).
- Horizon: 5m → 1h primary (§12). Incremental: FULL-gate + ΔCI95 alt > 0 (§21).
- Protected: §25 aynen.

## 9. Blocker taraması
- [x] Korumalar tanımlı (4 pencere + indirme aralığı)
- [x] Yeni eşik yok (tek yeni sayı: n_train ≥200k kabul kriteri — eşik değil, STOP gate'i)
- [x] Deney/indirme/fit/backtest çalıştırılmadı
- [x] 6A/6B dosyaları değişmedi (git'te teyit edilecek)
- [x] Commit/push yok
- [ ] **Final M.20 onayı (otoritede)** — tek bekleyen adım

Blocker YOK. Onay gelmeden 6C'ye ait hiçbir adım çalıştırılamaz.

**READY FOR FINAL M.20 APPROVAL**
