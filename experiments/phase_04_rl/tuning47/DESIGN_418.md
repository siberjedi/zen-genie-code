# PHASE 4.18 — DENEY TASARIMI / PREREGISTRATION
## "RL GERÇEK ALFA TESTİ" — DECISION-LEVEL PREDICTIVE POWER

Durum: **TASARIM (kod yok, training yok, tuning yok, Final B'ye temas yok, protokol kilidi değişikliği yok).**
Fazın son cümlesi: **"READY FOR USER APPROVAL"** — onay gelmeden 4.18 için HİÇBİR script/test yazılmayacak.

---

### 1. Research question

**"RL policy, giriş kararını verdiği ANDA, gelecekteki getiriyi öngören bilgi taşıyor mu?"**

- Soru **P&L / Sharpe üzerinden DEĞİL**, yalnızca **karar-anı koşullu forward getiri** (decision-level predictive power) üzerinden test edilir.
- 4.16'da gelir büyük ölçüde `exposure × market drift` ile açıklandı; 4.17 Alpha Gate hiçbir E1 seed'i aday kabul etmedi. Bu faz, "RL bir *pricing signal* üretiyor mu" sorusunu drift'ten bağımsız, karar-anı getirisiyle ayırmayı hedefler.
- 4.18 sonucu iyi çıksa bile otomatik "RL başarılı" denmeyecek: decision-level predictive edge ≠ economic trading edge.

### 2. Hypothesis H1

- **H1 (etki):** RL BUY kararlarının ardından gelen forward getiriler, aynı pencere/aynı rejim koşullu **random/control** girişlerinin forward getirilerinden **pozitif** yönde ayrışır (sinyal gerçek gelecek bilgisi taşır).
- İkincil H1: SELL kararlarından sonra forward getiri **negatif** yönde ayrışır (iyi çıkış sinyali).

### 3. Null hypothesis

- **H0:** RL BUY giriş sonrası forward getiri dağılımı, random/control girişlerininkinden **ayrışmaz** (median farkı = 0 / 0.5'e göre direction accuracy). RL "ad hoc bull-time dilimlerine long girme" politikasından öte bilgi taşımaz.
- Primarily seed-level olarak test edilir; pooled yalnızca betimsel (bağımsızlık varsayımı yok).

### 4. Dataset / window

- **Piyasa:** BTC/USDT, 5m kapanışlar; val penceresi `2023-01-01 .. 2023-06-30` (181 gün), `len(closes)=51,825`, `n_tradable=51,794` adım, `off=30`.
- **Data kaynağı:** `freqtrade/user_data/data/binance/BTC_USDT-5m.feather` (prized dates + closes). Yeni veri indirilmez.
- **Fiyat bazı:** signal-quality testi her kurumda aynı olması için **mid/close** fiyat; slippage/fee ayrıca decomposition'da ayrı raporlanır (adil karşılaştırma, frictraction sinyal kalitesinden ayrıştırılır).
- **Env parametreleri (değişmez):** FEE=0.001, SLIP=0.0005, all-in long-only, start=100. Bu faz test için env değişmez.

### 5. Seeds

- **E1 retro: {42, 7, 123, 2026, 999}** — yeni model EĞİTİLMEZ; mevcut artefaktlar kullanılır.
- Kaynaklar: `tuning47/art_E1_seed{s}.json` (adım başına action — deterministik karar dizisi), `run_E1_seed{s}.json` (val metrikleri, fee/slip, trade sayısı), `diag_E1_seed{s}.jsonl` (cross-check), `meta_E1_seed{s}.json` (model hash).
- Öngörülen giriş adetleri (flat→long): 42≈40, 7≈7, 123≈117, 999≈11, 2026≈0. 7 ve 999 **a priori EVALUABLE eşiğinin altında** (bölüm 13).

### 6. Signal extraction

- **Örnek birimi = giriş kararı (event):** action adımı k'da `pos: 0→1` geçişi (all-in olduğu için zaten long iken action=1 no-op'tur; yalnızca gerçek flat→long geçişleri sayılır). Seed başına n ≈ completed trade sayısı (+ terminal-açık kısmi pozisyonlar).
- **Karar indeksleri ve fiyat:** giriş action k; **execution candle = 30+k**; base fiyat `P0 = close[30+k]`.
- **Retrospectif karar akışı:** `art_E1_seed{s}.json` action dizisi + close'lar üzerinden deterministik event listesi üretilir (action dizisi sabit kayıtlıdır → gelecek bilgisi *yapısal olara*k giremez). `DecisionLogger` modern training'lerde doğrudan kayıt yapacak (bölüm "Decision Logging").
- **SELL eventleri:** `pos: 1→0` geçişleri; aynı forward-return ölçümü SELL-anı bazıyla (iyi SELL ⇒ forward getiri NEGATİF).

### 7. Forward-return definition

- h kayan pencere: `r_h(k) = close[30+k+h] / close[30+k] − 1`, h ∈ {1, 3, 12, 36, 72} (5m/15m/1h/3h/6h); diagnostic h ∈ {240, 720} (+20h/+60h).
- **Off-by-one guard:** execution candle `30+k`'nın kendisi forward aralığa DAHİL EDİLMEZ (geleceğe dönük aralık `30+k+1 .. 30+k+h`).
- **Ufuk kesim (guard):** `30+k+h > 51,824` olan event, o ufukta DÜŞÜRÜLÜR → her ufukta n farklı olabilir ve rapor edilir.
- **Karar bağımsızlığı (unconditional quality):** BUY sonrası forward getiri, RL'nin daha sonra çıkıp çıkmadığından BAĞIMSIZ ölçülür (o andaki sinyal kalitesi soruluyor).

### 8. Controls / benchmarks

| # | Kontrol | Tanım | Kaynak |
|---|---|---|---|
| 1 | **Random/control (ANA)** | Seed'ın rejim başına giriş adadyiyle birebir aynı sayıda, aynı rejim adım aralıklarından uniform random giriş; aynı h ufukları; 2,000 Monte-Carlo tekrarı → kontrol mean/median dağılımı | türetilmiş |
| 2 | **Buy-and-Hold** | Pencerede tek sanal giriş (adım 0'dan sona) → R_BH drift referansı; ayrıca "random noktadan h-getirisi" koşulsuz drift beklentisi | türetilmiş |
| 3 | **Locked regime classifier** | Entry = rejim==bull ve long değilse (4.16 bull_exposure stratejisi; window'da ~3 girş); REJİM-KOŞULLU random giriş (density-matching, birincil birim) ile çift rapor | türetilmiş |
| 4 | **Phase 3 baseline BUY** | Phase 3 Gameplan baseline BUY sinyalleri (val penceresi); degrade (sıfır/1-2 giriş) → "n çok küçük, referans-only" işaretlenir | phase03 artefaktları |
| 5 | **FreqAI BUY** | FreqAI modelinin aynı val penceresindeki BUY sinyalleri → per-entry forward return (aynı h) | `phase_03_freqai/results/val_trades_seed{s}.csv` |

**Ana karşılaştırma:** RL BUY forward return **vs random/control** — her seed, her ufuk; random kontrol trend-aware olduğu için "yükselen piyasada herhangi bir noktadan girince kazanma" artefaktını RL'den ayırır. FreqAI/regime satırları yorum desteğidir.

### 9. Metrics

- n; mean / median forward return; **A) Directional accuracy** `P(r_h>0)` (binom, H0=0.5).
- **B) Threshold hit rates:** `P(r>0.002)`, `P(r>0.004)`, `P(r>0.008)`.
- **C) Mean / median forward return** (RL ve her kontrol için, seed ve pooled).
- **D) Horizon curve:** h ∈ {1,3,12,36,72} + diag {240,720} × RL/random.
- **E) BUY quality by regime:** bull/bear/sideways/sideways_high_vol alt gruplarında aynı metrikler (n küçük → betimsel).
- **F) SELL quality:** SELL-anı forward getirisi `r_h` (iyi SELL ⇒ negatif); mean/median/negatif-oranı; window-sonu açık SELL'ler hariç tutulur.

### 10. Statistical tests

- **Primer (per seed, ufuk h=12=1h):** RL median vs random-kontrol median dağılımı → **ampirik Monte-Carlo p** (kontrol replikasyonlarının RL nokta tahminine ≤ oranı); ikincil **Mann-Whitney U** (median) ve **Welch t** (mean).
- **Bootstrap CI:** seed-level ve pooled için percentile bootstrap; **pooled'ta SEED-KÜME (cluster) bootstrap** — event değil seed örneklenir, `n_seed=5`.
- **Effect size:** Cohen's **d** (mean fark / pooled sd) + **Cliff's delta** (parametrik olmayan).
- **Güç:** `compute_power(effect=d, n1=min(n_RL,n_ctrl), α=0.05, ratio=1)`; `power<0.80` → **"LOW POWER"** etiketi; `n_eff<12` → **"EVALUABLE DEĞİL"**.
  - Önceden hesaplanan bütçe (d=0.8): n=7→0.28, n=11→0.43 (7 ve 999 **asla EVALUABLE olamaz**), n=40→0.94, n=117→1.00.
- **Çoklu test:** primer seed×1h matrisinde **BH-FDR** (q<0.05); ufuk/rejim/eşik tabloları keşifsel ilan edilir (α=0.05 pre-register).
- **Küçük n kuralı (spec'ten):** 7 veya 11 giriş üzerinden gelen yüksek Sharpe/median "edge" OLARAK KABUL EDİLMEZ; yalnız betimsel + bootstrap CI raporlanır.

### 11. Causality / leakage audit

| # | Kontrol | Beklenen/doğrulanan semantik |
|---|---|---|
| 1 | Observation window | `obs = closes[k : k+30]` — action k anında son 30 kapanış; en geç `close[30+k−1]` bilgisi |
| 2 | Execution candle | Füll `close[30+k]` (slippage ayrı); sinyal anı = karar anı |
| 3 | Forward-return base | `P0=close[30+k]`; gelecekteki aralık `30+k+1..30+k+h` (off-by-one guard) |
| 4 | Kullanılan feature'lar | Yalnız obs (close serisi) + normalizer; **normalizer train-only** (val penceresinde fit yok) |
| 5 | Normalizer | 4.15 doğrulaması: train üzerinde fit, val'e sadece uygulama |
| 6 | Future→observation | Action dizisi `art` dosyasında sabit; forward-return hesabı yalnız `close` indeksleriyle, obs'a kasıtlı sızıntı yok |
| 7 | Off-by-one | `obs closes[k:k+30), execution close[30+k]` semantiği 4.15'te doğrulandı; 4.18'de event üretiminde AYNI indeksleme test edilir (`tests/test_phase418.py` sentetik fixture ile) |
| 8 | Replay bütünlüğü | 4.15 replay equity == kayıtlı equity (her seed); 4.18 event listesi diag stream ile cross-check |

### 12. Exposure-vs-timing decomposition (betimsel)

```
RL_net ≈ DRIFT(E·R_BH) + TIMING − FRICTION
```
- `DRIFT = E × R_BH` (exposure-only expected); `FRICTION = fee_total + slip_total` (% start); `TIMING = RL_net − DRIFT + FRICTION` (residual).
- **Keskin timing ölçüsü (4.16 convention):** `TIMING_reentry = RL_net − REENTRY_net`, REENTRY = passive exposure-koruyucu referans (4.16: 42:+62.28, 7:+42.13, 123:+14.71, 2026:0, 999:+76.03). Bu, "aynı exposure'ı pasif tutsaydın ne kazanırdın" soru sürerimini timing'ten ayırır.
- Her iki kimlik de **multi-trade compounding nedeniyle yaklaşık/descriptive** olarak damgalanır, kesin P&L iddiası değildir.
- Raporda açıkça: **fazın ana sonucu know P&L değil, "RL kararları gelecekteki getiriyi öngörüyor mu?"** sorusudur.

### 13. Failure / EVALUABLE criteria

- **F1 n-engeli:** primer ufukta `n_eff<12` → istatistik katmanı **"EVALUABLE DEĞİL"** (yalnız betimsel). Bilinen: 7 (n≈7), 999 (n≈11), 2026 (n=0 → sinyal yok seed).
- **F2 power:** primer hücrelerde `power≥0.80` şartı; altında otomatik **"LOW POWER"** etiketi; bu hücreden edge iddiası üretilmez.
- **F3 edge verdiği için (pre-registered):** "DECISION-LEVEL EDGE" denebilmesi için HEPSİ: (a) pooled RL−random median farkı **lower 95% cluster-CI > 0** (h=12), (b) primer seed matrisinde **FDR-q<0.05**, (c) **≥3/5 seed aynı yönde**, (d) FreqAI/regime kontrollerinde tutarlılık (sanity).
- **F4 saçma-önlem:** tek-seed küçük-n yüksek ortalamalar (örn. 999'un 11 girişi) edge vakası sayılmaz; yalnız kritik olarak raporlanır.
- **F5 geçerli çıktı:** koşullar sağlanmazsa sonuç **"HIÇBİR DECISION-LEVEL EDGE TESPİT EDİLMEDİ"** — bu bir hata değil, geçerli (ve 4.16/4.17 ile tutarlı) bir sonuçtur.

### 14. Expected compute / time

- Saf retrospective, tertip vektörleştirilmiş (numpy): event üretimi + forward-return dizileri + 2,000 Monte-Carlo kontrol tekrarı **toplam CPU < 1 dakika** (seed başına ~saniyeler).
- GPU yok; yeni veri indirme yok; training/tuning yok. Ana maliyet `phase418_forward.py` Monte-Carlo replikasyonlarıdır (numpy, precompute close array).

### 15. Exact files / scripts needed (onay sonrası oluşturulacak)

| Dosya | İçerik |
|---|---|
| `experiments/phase_04_rl/tuning47/DESIGN_418.md` | BU dosya (tasarım/preregistration) |
| `scripts/phase418_events.py` | Event extraction: per-seed flat→long (BUY) & long→flat (SELL) event listesi + rejim etiketi + forward-return dizileri (h×event matrisi) → `tuning47/events418.json` |
| `scripts/phase418_forward.py` | Forward-return + kontroller: random/control (2,000 MC), B&H ref, regime-coşullu, FreqAI (`val_trades_seed{s}.csv`) ve Phase3 baseline sinyal listeleri → `tuning47/forward418.json` |
| `scripts/phase418_stats.py` | Per-seed + pooled istatistik: MWU/Welch, ampirik MC-p, bootstrap (seed-cluster) CI, Cliff's d, compute_power, FDR, eşik hit-rate, horizon curve, regime breakdown, SELL kalitesi → `tuning47/stats418.json` |
| `scripts/phase418_decomp.py` | Exposure-vs-timing decomposition (bölüm 12 kimlikleri, 4.16 reentry anchor dahil) → `tuning47/decomp418.json` |
| `scripts/phase418_report.py` | REPORT_418.md üretir (13 başlıklı: RQ→Hipotez→Veri→Seeds→Extraction→Fwd-Ret→Kontroller→Metrikler→Testler→Leakage→Decomp→EVALUABLE→Compute) |
| `tests/test_phase418.py` | Sentetik fixture: off-by-one guard (execution candle forward aralığa girmiyor), random-kontrol determinisity (MC seed'li), obs indeksleme, window-sonu kesim |
| Çıktı | `tuning47/REPORT_418.md` + `events/forward/stats/decomp418.json` |

### 16. Protocol impact

- **Alpha Gate LOCKED-DIAGNOSTIC olarak kalır** — 4.18'de selection criterion YAPILMAZ.
- 4.18 kanıtı, gelecekte gate'in resmi kılınıp kılınmayacağı kararına girdi sağlar (bugün karar alınmaz).
- Locked threshold'lar (`Sharpe≥0.80`, gap<0.35, 30 gün, power 0.80): DEĞİŞMEZ.
- Env/reward/action-space/normalizer: DEĞİŞMEZ. Training/tuning: YOK. MAVİ log: 4.18'de yeniden çalıştırma yok.
- Yeni kod YALNIZ `scripts/phase418_*`, `tests/test_phase418.py` (+artefaktlar) — mevcut modüllere temas yok.

### 17. Final Test B protection

- Final Test B'ye: **indirilmez, açılmaz, çalıştırılmaz, metrikleri okunmaz/hesaplanmaz**. Test listesinde Final B'yi okuyan hiçbir script tanımlanmamıştır. Retrospektif E1 artefaktları (art/run/diag/meta + BTC_USDT-5m feather) DIŞINDA veri kaynağı yoktur.
- Guard: `phase418_*` script'lerinde Final Test B dosya yollarına referans bulunmaması kod-review kuralı olarak tutulur.

---

## SON KURAL (bu turda)

NO CODE · NO TRAINING · NO TUNING · NO FINAL TEST B · NO PROTOCOL LOCK CHANGE

## **READY FOR USER APPROVAL**