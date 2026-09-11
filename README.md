# Zen-Genie — AI Trader (ARAŞTIRMA KAPANDI)

> ## ⚠️ SONUÇ: DENENDİ, İŞE YARAMADI
>
> Bu proje, kripto piyasasında otomatik olarak kâr eden bir trading stratejisi
> bulmayı amaçladı. **Bulunamadı.** Araştırma 2026-09-10'da resmen kapatıldı.
>
> - 22 alpha ailesi incelendi, 16'sı karar-verici testle hükme bağlandı → **survivor = 0**
> - Klasik teknik sinyaller, ML (FreqAI/RandomForest), RL (PPO), funding/OI/cross-asset,
>   futures basis, micro trade-flow, long-only trend — hepsi elendi
> - Test edilen stratejilerin hiçbiri "sadece elde tutmayı" (buy & hold) geçemedi
> - Faz 2 baseline'ın **komisyon öncesi** brüt sonucu: -0,15 USDT (3454 işlemde ≈ sıfır)
>
> Bu repo çalışan bir trading botu **değildir**. Gerçek parayla kullanmayın.
>
> ### Sonradan yapılan incelemede bulunan kusurlar
>
> 1. **MaxDD "ruin" rakamı hatalı.** `src/backtest/evaluate.py:23` eşzamanlı pozisyonların
>    `profit_ratio` değerlerini toplayıp günlük portföy getirisi sayıyor; bu, bileşiklenince
>    eğriyi çökertiyor. Faz 2'de raporlanan "~-100% (ruin)" gerçek değil —
>    dolar bazlı doğru hesap: ortalama fold MaxDD **-%34**, en kötü fold **-%59**.
> 2. **Maliyet varsayımı gereğinden yüksek.** C=0.003 (30bp) kilitliydi; Binance Regular
>    seviyede BNB indirimiyle gerçek round-trip ~15bp. Düzeltilmesi test edilen ailelerin
>    hükmünü değiştirmezdi (brütleri zaten 15bp'nin altındaydı), ama varsayım yine de yanlıştı.
> 3. **Dry-run'ın kâr ettiği dönem hiç backtest edilmedi.** Faz 1 (2026, +%4, 19 işlem)
>    ile Faz 2 (2020–2023H1 backtest) aynı kurulum değil; 2025H2–2026 penceresi test edilmedi.
>    19 işlem istatistiksel olarak anlamsızdır ve pozisyon o dönemde neredeyse tamamen long'du.
> 4. **`capital_state.json` drift'i çözülmedi** (kanonik dosya ile stale dosya arası ~6 USDT HWM farkı).
>
> ### Yine de burada değerli olan ne?
>
> Çalışan backtest + walk-forward altyapısı, holdout registry ve guard testleri, FDR/
> preregistration disiplini, ve 22 alpha ailesinin neden işe yaramadığının haritası.
> FINAL_C holdout rezervi hiç kullanılmadı.


Nihai protokol: `PROTOCOL.md:1` (locked 2026-08-27). Tek referans.

## Hızlı Başlangıç — Faz 1 Dry-Run
```bash
docker compose up -d --build   # freqtrade + dashboard
# Dashboard: http://127.0.0.1:5173  API: http://127.0.0.1:8001/docs
```
Çıkış kriteri: 7 gün kesintisiz, P&L/komisyon/bakiye doğru (`PROTOCOL.md:1` Faz 1).

## Dashboard (Faz 1 gözlem — local only)
```bash
docker compose up -d dashboard-api dashboard
# veya local dev:
py -3 -m uvicorn dashboard.backend.app:app --host 127.0.0.1 --port 8001
npm install --prefix dashboard/frontend && npm run dev --prefix dashboard/frontend
```
Detay: `dashboard/README.md:1` — LIVE TRADING DISABLED, sadece `tradesv3.dryrun.sqlite` + Binance public REST.

## Fazlar
0 protokol kilidi → `config/experiment.yaml:1` (X/Y eşiklerini sonuçtan önce doldur)
1 dry-run → 2 walk-forward → 3 FreqAI → 4 RL → 5 karşılaştırma → 6-7 X haber → 8 multi-source → 10 paper → 11 real

Anayasa 20 madde: `PROTOCOL.md:1` en alt.

## Doğrulama
```bash
py -3 scripts/verify_dryrun.py  # 8/9 → 7 gün sonra 9/9
docker ps  # ai-trader-dryrun Up, zen-dashboard Up, zen-dashboard-api Up
```
