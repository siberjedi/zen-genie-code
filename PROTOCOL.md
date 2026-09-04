# 🤖 AI Trader — Nihai Araştırma ve Geliştirme Protokolü (LOCKED)

> **Referans sürüm:** 2026-08-27 — Parça parça revize kapalı, bu dosya tek kaynak.

## Projenin Amacı

Trading bilgisi olmayan kullanıcının yerine gerçek zamanlı piyasa verisini + gerektiğinde haber/sosyal medya bilgisini analiz eden, kendi stratejilerini deneyen, risk ölçen ve **önce sanal para ile çalışan** otonom trading sistemi.

> **İlk hedef:** Gerçek para kullanmadan, gerçek piyasa üzerinde çalışan AI trader. Gerçek para en son aşama.

---

## FAZ 0 — Deney Protokolü (LOCKED)

Model geliştirmeden önce deney kuralları kilitlenir; sonuçlar görüldükten sonra değiştirilmez.

### Veri Ayrımı
Her bağımsız deney: `Train → Validation → Final Test`
- **Train:** model öğrenir
- **Validation:** hyperparameter / feature / model / seed seçilir
- **Final Test:** nihai değerlendirme, tuning sırasında asla kullanılmaz

### Final Test Tüketim Kuralı
Her büyük fazın kendi dokunulmamış final test dönemi vardır:
```
FreqAI → Final Test A
RL     → Final Test B
Final karşılaştırma → Final Test C
```
FreqAI'nin Final Test A sonucunu görüp RL tasarımını değiştirmek **veri sızıntısıdır**. Bir final test sonucu geliştirmede kullanılırsa o test artık final değildir, yeni final test ayrılır.

### Primary Metric
Deney başlamadan tek ana metrik seçilir. Aday: **Out-of-sample Sharpe Ratio**
Secondary: Net Return, Max Drawdown, Sortino, Profit Factor, Win Rate, Turnover, Fee impact, Slippage impact. Secondary ile başarı ilan edilmez.

### Çoklu Karşılaştırma
Birden fazla hipotez için FDR / Bonferroni veya uygun düzeltme.

---

## FAZ 1 — Freqtrade Dry-Run
**Stack:** Python, Freqtrade, Binance market data, SQLite. Kendi paper-trading motoru yazılmaz.
```
Binance canlı veri → Freqtrade → $10 sanal bakiye → BUY/SELL → Komisyon+slippage → P&L
```
Amaç: AI değil, sanal altyapının çalıştığını kanıtlamak.
**Çıkış:** canlı veri/emir/bakiye/P&L/komisyon doğru, geçmiş kaydediliyor, **7 gün kesintisiz dry-run**.

## FAZ 2 — Backtest + Walk-Forward
**Teknoloji:** Freqtrade Backtesting, walk-forward (tek Train→Test yerine rolling).
Fold örtüşmesi / otokorelasyon / bağımsızlık raporlanır. 4-5 yıllık fold zorunlu değil, granular rolling değerlendirilir.
**Rejimler:** Hindsight yok. Mekanik, önceden kilitli classifier (MA, volatilite, trend). Sınıflar: Bull/Bear/Sideways/High vol/Low vol. Rejim/fold sonuçları bağımsız gibi yorumlanmaz.
**Slippage:** Backtest gerçek maliyet değildir; `haber → fiyat sıçraması → likidite düşüşü → kötü fill` ayrıca raporlanır.
**Çıkış:** Baseline'ın önceden kilitlenmiş performans referansı.

## FAZ 3 — FreqAI / Supervised ML
```
Market Data → Features → ML Model → Prediction → Trading Signal
```
Model/feature/hyperparameter/seed seçimi sadece Train+Validation, Final Test yasak.
**Çıkış (önceden kilitli):** OOS Sharpe, min Sharpe farkı X, walk-forward'ın Y%'sinde baseline'ı geçme, MaxDD ≤ sınır, seed stability ≥ sınır. X/Y sonradan değişmez.

## FAZ 4 — RL Laboratuvarı (FreqAI'den ayrı)
**Stack:** Gymnasium, Stable-Baselines3, PPO/SAC/(TD3)
```
STATE → ACTION → MARKET → REWARD → NEXT STATE
```
İlk reward: **log portfolio return** (tek, basit). Karmaşık rewardlar ayrı deneyle test edilir.
**Tuning bütçesi önceden kilitli:** max config/seed/süre. İlk kötü sonuçta elenmez.
İzolasyon: `Train → Validation → RL tuning → En iyi config → 🔒 FINAL TEST`

## FAZ 5 — Baseline vs FreqAI vs RL
Birden fazla walk-forward window + rejim + seed, ama bağımsız sayılmaz. Primary: OOS Sharpe. Multiple comparison düzeltmesi. Çıkış eşikleri önceden kilitli (Sharpe avantajı, MaxDD, WF başarı oranı, seed stability, anlamlılık/effect size).

## FAZ 6 — X / Haber Veri Katmanı
**Stack:** Playwright + Chromium + lokal X hesabı + lokal LLM. Başta X API yok.
İzolasyon: X otomasyonu rate limit/challenge/kısıtlama riski taşır → X hesabı trader altyapısından izole, kapanırsa geri kalan çalışır.

## FAZ 7 — X / Haber Predictive Power
Önce sinyal işe yarıyor mu ölçülür: `t=0 → 1dk/5dk/15dk/1sa` piyasa davranışı.
Metrikler: Event study, IC, Precision/Recall, signal decay, detection latency, cost-adjusted return.
Predictive power ≠ trading kârı, ayrı ölçülür. Eşiği geçemezse **X trader'dan çıkarılır**.

## FAZ 8 — Multi-Source AI Trader
Sadece kanıtlı kaynaklar birleşir:
```
Market Data + ML/RL + (X|News|Macro — kanıtlıysa) → Decision Layer → BUY/HOLD/SELL
```
LLM direkt BUY demez; ham bilgiyi yapılandırır: `Asset/Event/Sentiment/Novelty/Confidence`.

## FAZ 9 — NautilusTrader / Execution
Hedef değil, ihtiyaç olursa: AI Decision → NautilusTrader → Risk/Order Management → Exchange. Freqtrade sınırına ulaşınca değerlendirilir.

## FAZ 10 — Uzun Süreli Live Paper Trading
```
REAL MARKET → AI TRADER → PAPER ACCOUNT ($10/$100/$1000)
```
Metrikler: Return, Sharpe, Sortino, MaxDD, Fee/Slippage/Spread/Latency/Turnover/Frequency.
Backtest → Walk-forward → Live Paper farkı, özellikle haber anındaki spread/likidite/latency/slippage incelenir.
Çıkış: min performance, maxDD, stability, max backtest/live gap, min gözlem süresi sağlanmadan gerçek paraya geçilmez.

## FAZ 11 — Gerçek Para
Binance API: Read ✅ Trading ✅ Withdraw ❌ — minimum order/notional kontrolü. $10 çok küçükse zorlanmaz. Amaç 10→15000 değil, paper edge'in gerçek execution'da varlığını test etmek.

---

## 🔐 Anayasa (20 Madde)
1. Eşikler sonuçlardan önce belirlenir. 2. Final Test tuning'e kapalı. 3. Bir fazın Final Test'i başka fazın tasarımında kullanılamaz. 4. Final Test geliştirmede kullanılırsa yeni Final Test gerekir. 5. Primary metric önceden belirlenir. 6. Secondary primary yerine geçemez. 7. Çoklu karşılaştırmada düzeltme. 8. Walk-forward foldları bağımsız sayılmaz. 9. Rejimler hindsight değil, mekanik ve önceden kilitli. 10. RL tuning sadece Train+Validation. 11. RL ilk başarısızlıkta elenmez. 12. Backtest slippage gerçek maliyet değil. 13. X predictive power olmadan bağlanmaz. 14. X automation izole. 15. X kapanırsa sistem çalışır. 16. Her model baseline'a kıyaslanır. 17. Sıra: Backtest→Walk-forward→Live Paper→Real Money. 18. "Anlamlı fark yok" ≠ "edge yok"; Type II (effect size/CI/sample/power) raporlanır. 19. Gerçek para en son. 20. Sonuçlar görülünce kurallar değişmez.

---

## 🎯 Nihai Mimari
```
MARKET DATA → X/NEWS (kanıtlı) → AI/ML/RL Decision Layer → BUY/HOLD/SELL → EXECUTION (Freqtrade/Nautilus) → PAPER (önce) / REAL (en son) → PERFORMANCE DATA → STATISTICAL TESTING → RESEARCH LOOP
```
**İlk taş:** `Freqtrade + Binance + Dry-Run + $10 sanal bakiye`
