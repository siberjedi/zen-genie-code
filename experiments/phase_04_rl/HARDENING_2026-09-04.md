# Phase 4.1 RL Environment Hardening — 2026-09-04 (eğitim YOK)

> Audit (`READINESS_AUDIT_2026-09-04.md`, 10 blocker) sonrası düzeltmeler.
> Testler: `tests/test_rl_hardened.py` 12/12 PASS. Training/tuning YOK.

## A. Yapılan değişiklikler
- `src/rl/env.py` → v4.1.0 rewrite: cash-bazlı ekonomi, fee+slippage, MTM reward,
  obs'ta position+equity, episode-sonu zorunlu likidasyon, guard sayaçları.
- `src/rl/train.py` → rewrite: config okuma, feather loader + rol penceresi +
  Final B guard, 50×5 budget grid + ledger + 12h callback, SAC/PPO hard select,
  seed_all + metadata. hardcoded 100k KALDIRILDI (açık `total_timesteps` alanı,
  varsayılan 500k yapısal; bağlayıcı sınır 12h cap).
- `requirements.txt`: `gymnasium==1.3.0`, `stable-baselines3==2.9.0` pin
  (kurulum doğrulandı; torchvision uyarısı ilgisiz).
- Yeni strateji threshold'u YOK (SL/ROI eklenmedi), protokol/threshold/budget DEĞİŞMEDİ.

## B. Reward economics
`reward_t = log(pf_t / pf_{t-1})`, pf = cash + amount×close (mid, slippage'siz MTM).
Fee (0.001/ayak) + slippage (5bps adverse) cash hesabında; toplamı exact ayrışır
(test 5: Σreward == log(final/initial) 1e-9). Turnover manipülasyonu cezalı
(yıkama turu ~%0.2+ kayıp); shaping YOK (drawdown/turnover penalty eklenmedi).

## C. Execution model
All-in tek-slot long (belgeli limit), Discrete(3), buy/sell/invalid sayacı,
aynı-candle flip imkansız, SL>ROI>sinyal YOK (RL kararı — baseline kuralları eklenmedi).

## D. Data split / leakage protection
Loader: feather + zorunlu tarih + rol⊂config penceresi (train 314,911 / val 51,825
BTC satırı, örtüşme yok — test 6). Future/lookahead/reward TEMİZ; episode tek
parça (PPO kredi-atama notu duruyor); normalizasyon YOK (bilinçli, değişiklik yok).

## E. Final Test B protection
`FinalTestLeakError` HARD ERROR (test 7: sentetik örtüşme + rol penceresi).
Veri bugün YOK (disk 2023-12-30 bitiyor) — indirilMEDİ.

## F. Risk controls
Invalid-action sayacı, position invariant (`PositionInconsistencyError`),
bankruptcy truncate, turnover/fee sayaçları (log), zorunlu likidasyon.
Drawdown: info'da izlenir, truncate YOK (strateji eşiği olurdu).

## G. Reproducibility
`seed_all` (random/numpy/torch+cudnn) + env/model seed + metadata (seed, algo,
config hash, range, feature list, env version/hash, commit, timestamp, süre,
capital, fee, slippage). Aynı seed+aksiyon → bit-identical (test 8).

## H. Tuning budget implementation
Grid ≤50 config + ≤5 seed (aşımda `BudgetExceededError`, test 12),
ledger (runs/configs/seeds/max_total_hours), 12h wall-clock callback
(`TimeoutExceeded`), `--config` gerçekten okunuyor (test 11: 50×5×12).

## I. Test sonuçları
12/12 PASS (import, smoke, transition, fee-math el hesabı, forced-close,
isolation, guard, determinism, risk, algo-select, config, budget). Training YOK.

## J. Kalan blockerlar
- YOK (B1–B10 kapandı). Bilinen limitasyonlar (blocker değil): tek-pair default
  (B10, protokol şart koşmuyor), normalizasyon yok, episode chunking yok,
  SAC discrete'te desteklenmiyor (HARD ERROR verir — tasarım kararı).
- Phase 3.6 taşıma: fee temsili exact, slippage 5bps eklendi (maliyet TABAN
  tamam); turnover cezası reward'da doğal mevcut.

## K. RL READY / NOT READY
- Environment + runner + guard + test hazır. Eğitim onayı ayrı adımda.

PHASE 4.1 COMPLETE — RL TRAINING STILL NOT STARTED
