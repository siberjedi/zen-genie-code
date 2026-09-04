# Phase 4 RL Readiness Audit — 2026-09-04 (denetim, eğitim YOK, düzeltme YOK)

> Kapsam: `src/rl/env.py:1` (53 satır), `src/rl/train.py:1` (31 satır),
> `config/experiment.yaml:85-90`, `PROTOCOL.md:63-70`. RL eğitimi çalıştırılmadı.
> Blocker'lar SADECE listelendi, kod/protokol değiştirilmedi.

## A. Environment (`src/rl/env.py:9-53`)
- Observation: `Box(window=30, n_feat)` float32; `date/open/high/low` dışı TÜM
  numerik kolonlar (close + çağıranın koyduğu indikatörler). Ham ölçek,
  normalizasyon katmanı YOK. `window` default 30.
- Action: `Discrete(3)` — 0 hold / 1 buy / 2 sell (`env.py:19`).
- Position state: binary (`pos` 0 flat / 1 long, `env.py:24`); tek pozisyon, all-in
  (equity'nin tamamı, `equity=1.0` başlangıç `env.py:26`).
- Balance/equity state: obs'te YOK (ajan kasasını göremez); equity SADECE
  sell'de güncellenir (`env.py:43-47`).
- Entry/exit: buy → `entry=close×(1+fee)`; sell → `log(close×(1-fee)/entry)`
  realize edilir. Aynı-candle flip İMKANSIZ (adım başına tek action); re-entry
  en erken sonraki mumda (H5 quirk'inin sınırlı hali).
- Position sizing: sabit all-in; kısmi pozisyon YOK, kaldıraç çarpanı YOK (1x
  zımni), max-open kavramı YOK.
- Fee: 0.001/ayak (`env.py:11,42,44`) — break-even %0.2 ile tutarlı.
  Slippage: YOK (0) — kilitli 5bps varsayımına aykırı yönde eksik.
- Reward: sell'de realize log portfolio return (`env.py:46`); diğer adımlarda 0;
  mark-to-market YOK (`env.py:52` yorumda itiraf ediliyor).
- Episode: tüm df tek episode; `terminated` sonda (`env.py:50`),
  `truncated` daima False. **Sonda açık pozisyon sessizce düşer** (aşağıda B8).

## B. Reward economics
| Kalem | Temsil | Not |
|---|---|---|
| gross P&L | sell'de `(close-entry)×amount` üzerinden | fee düşülmeden önce |
| transaction fee | giriş+çıkış 0.001 | net return'den düşer, doğrulanabilir formül |
| slippage | YOK | maliyet TABAN tahmin → edge abartılır |
| realized P&L | reward'un ta kendisi (`log`) | |
| unrealized P&L | reward'da YOK, equity'de YOK | açıkta -%50 taşımanın cezası yok |
| drawdown | reward'da YOK | |
- Turnover manipülasyonu: MÜMKÜN DEĞİL (cezalı). Her buy→sell turu ~%0.2+ spread
  kaybettirir; wash-trade enflasyonu yok. Taban strateji "asla trade etme" →
  reward 0 (sağlıklı zemin, exploit değil).
- ANCAK: episode sonunda açık pozisyonun düşmesi, gerçekleşmemiş zararın
  bedavaya atılması demek (B8) — bunun tersi de mümkün (kârın yok sayılması).

## C. Action/execution
- BUY/SELL/HOLD → tek-slot long makine (yukarıda). Gereksiz flip: aynı-candle
  imkansız; mum-arası flip serbest (Phase 3.6 churn rejiminin discrete karşılığı
  mümkün — reward bunu fee ile cezalandırır, engellemez).

## D. Data split
- `train.py:11` tek CSV yükler, tarih filtresi YOK, validation spliti YOK.
- Default path `freqtrade/user_data/data/binance_BTC_USDT_5m.csv` diskte YOK
  (gerçek yerleşim: `data/binance/<PAIR>_USDT-5m.feather`). Bugün bu komutla
  eğitim zaten çöker.
- Final Test B guard mekanizması: KODDA YOK.

## E. Leakage
- Future/lookahead: TEMİZ (reward yalnızca close[t] + saklı entry kullanır).
- Reward leakage: YOK.
- Episode boundary: tek parça df (chunking yok) — 400k+ mumluk episode'da PPO
  rollout/kredi-atama zorluğu (bulgu, guard değil).
- Normalization leakage: N/A (normalizasyon yok) — ama ham-fiyat ölçeği NN
  eğitimi için risk (bulgu).
- Validation contamination: YAPISAL — split olmadığı için bugün çalışacak her
  eğitim, Final A/B dahil tüm tarihi görür.

## F. Risk (açık noktalar)
- All-in + SL/ROI YOK (baseline'da -%10/+%2 var): ajan -%90 açık taşıyabilir,
  ara ceza YOK → catastrophic-drawdown körlüğü.
- Sıfır-gecikme close fill + sıfır slippage: maliyetler gerçek-altı → ölçülen
  edge gerçek-üstü. Phase 3.6 fee'in tek başına öldürdüğünü gösterdi; bu env
  daha da iyimser.
- Tek-pair default (BTC), 18-pair evrenle uyumsuz; short yok (baseline ile tutarlı).
- Açık-pozisyon-düşürme (B8) ile birleşince risk resmi eksik.

## G. Reproducibility
- `train()`'de seed parametresi YOK; `PPO(...)` seedsiz → nondeterministik.
- Run metadata/log KAYDEDİLMİYOR. `experiments/phase_04_rl/` BOŞ.
- `yaml` importlu ama `--config` hiç okunmuyor (`train.py:6,26-31`).

## H. Tuning budget
- Kilit: 50 configs × 5 seeds × 12 hours (`experiment.yaml:85-90`) — DOSYADA DURUYOR.
- Uygulama: `budget` parametresi KULLANILMIYOR, `total_timesteps=100_000`
  hardcoded (`train.py:22`), config/seed döngüsü YOK, 12h cap YOK.
- **SAC dalı sessizce PPO eğitiyor** (`train.py:17-21`): etiket bütünlüğü ihlali.

## I. Final Test B protection
- Tanım mevcut: 2024-01-01 → 2024-06-30 (`experiment.yaml:20`), A ile örtüşmez.
- Veri BUGÜN YOK (disk 2023-12-30'da bitiyor) → yanlışlıkla dokunulamaz (iyi).
- Kod koruması: YOK — eğitimden önce guard + split + tarih-filtreli loader ŞART.

## J. Blockers (düzeltme YOK, sadece liste)
- **B1** `stable_baselines3`/`gymnasium` kurulu DEĞİL (import patlıyor) — bu env'de eğitim imkansız.
- **B2** Default veri yolu geçersiz (CSV vs feather yerleşim uyumsuzluğu).
- **B3** Train/validation spliti + tarih filtresi YOK (tüm tarih + Final A/B tek df).
- **B4** Final Test B (ve A) guard mekanizması YOK.
- **B5** Bütçe uygulanmıyor (döngü/cap yok, 100k hardcoded, `--config` okunmuyor).
- **B6** SAC dalı PPO eğitiyor (yanlış etiket).
- **B7** Seed/metadata plumbing YOK (nondeterministik, denetlenemez).
- **B8** Episode-sonu açık pozisyon sessizce düşüyor (gerçekleşmemiş P&L kaybı).
- **B9** SL/ROI/drawdown guard YOK + all-in + sıfır-slippage iyimser fill (risk-kör, edge-abartılı).
- **B10** Tek-pair default; çoklu-pair evren tasarımı YOK.

## K. READY / NOT READY
- **NOT READY** — 10 blocker (B1–B10). RL training BAŞLATILMADI.
- Phase 3.6 taşıma notu: env fee'yi doğru temsil ediyor (%0.2) ama slippage'i
  eksik → maliyetler TABAN; turnover cezası reward'da mevcut ve doğru yönde.
  Maliyet temsili düzeltilmeden (slippage + guard'lar) eğitilen her edge,
  Phase 3.6 bulgusuna göre de şişkin çıkar. Yeni threshold EKLENMEDİ (talimat
  gereği); sadece denetim.
