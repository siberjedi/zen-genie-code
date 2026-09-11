# PHASE 6C — RUN REPORT (STOPPED, sonuç üretilmedi)

**Lock:** M20 6C FINAL · **Karar:** **6C STOPPED — VAL missing > 0**
**CPU:** ~0 (model fiti YOK; yalnızca indirme + feature build + gate kontrolü)
**Koruma:** P5(2025H1)/B(2024H1)/C(2024H2)/A(2023H2) DOKUNULMADI.

## STOP sebebi (lock §11 + STOP koşulu "VAL missing > 0")

- 2023-06-06 11:20–11:35 UTC arasında 4 venue-side sıfır-OI snapshot
  (2021-05-22 ve 2022-03-07/08 glitch'leriyle aynı imza: OI=0, oranlar NaN).
- Etki (VAL, 51.825 satır): union **603 satır NaN** — oi_chg_12: 8,
  oi_z_288: 291, oi_price_div: 8, oi_chg_1: 5, oi_range_288: 291.
- Run gate (`VAL OI NaN == 0`) tetiklendi → `RuntimeError: STOP: VAL missing
  > 0 (603)` → model fiti YOK, sonuç YOK, zorlama YOK.

## Data coverage/hash
MANIFEST_DOWNLOAD_6C.json: 1277 gün dosyası (eksik gün: yalnızca 2020-01-01 →
2020-08-31 pre-coverage aralığı, beklenen), sha256 verified, 297.003 snapshot,
ilk OI 2020-09-01 00:00 (gate ≤2020-09-30 PASS), son 2023-06-30 23:55.
131 NaN snapshot (10 + 102 + 15 + 4; sıfır-OI glitch'leri, NaN-then-drop).

## Integrity
Monoton + dup-yok (dedup keep-first sonrası) + grid aidiyet ±60s + aralık
8h±60s — tamamı PASS. Sıfır-OI glitch'leri 3 ayrı tarihte (2021-05-22,
2022-03-07/08, 2023-06-06).

## Alignment/dedup
ACTUAL-ms asof-backward; geceyarısı dedup sonrası dup kalmadı (STOP tetiklenmedi).

## Leakage checks
Causality probe PASS; test_phase6c 11/11 PASS (formül + availability + dedup
semantiği sentetikte doğrulandı). Canlı veride leakage testi koşamadı (STOP öncesi).

## Train/validation counts
FULL train değerlendirilemedi (STOP VAL gate'inde, fit öncesi). Beklenen kayıp:
pre-coverage ~70k + warmup; n_train ≥200k gate'ine ulaşılamadı (ölçülmedi).

## BASE reproduction
Koşmadı (STOP fit öncesi). E032 referansı geçerli (6A/6B bit-exact kanıtlı).

## BASE/NEW/FULL sonuçları — YOK (model fit edilmedi)

## FULL-BASE / CI / FDR / effect/power / gates — YOK (deney koşmadı)

## Protected-test verification
Loader yalnızca TRAIN+VAL aralığına erişti (feature build grid'i); indirme
2020→2023H1 assert'li; holdout verify koşu sonrası tekrar koşulacak.

## Anomalies
1. Sıfır-OI venue glitch'leri (3 tarih, toplam 131 snapshot) — raporda belgelendi.
2. OI başlangıcı 2020-09-01 (scout'taki ~2020-09-10 tahmininden 9 gün erken —
   lehte, gate'i zaten geçiyordu).

## Exact decision
**6C STOPPED — VAL missing > 0 (2023-06-06 venue glitch, 603 VAL rows).**
RESULTS_6C.json / METRICS_6C.json / GATE_6C.json ÜRETİLMEDİ (deney koşmadı;
üretilmiş gibi gösterilmiyor). Bir sonraki adım ayrı M.20 kararı gerektirir
(seçenekler: pencere-dışı bırakma YOK — splitler kilitli; tasarım revizyonu
veya 6C kapatma).

**Not:** statistical predictive ≠ economic incremental edge — bu koşuda
değerlendirilemedi (deney STOP).
