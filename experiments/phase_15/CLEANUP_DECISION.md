# CLEANUP DECISION (karar kaydı; UYGULAMA YOK)

**Statü:** REVIEW-ONLY. delete/move/rename/refactor/commit/push/backtest YOK.
Holdout açılmadı. Kod değiştirilmedi. Aşağıdaki her karar UYGULAMA için
ayrı kullanıcı onayı ister.

## 1. FIX-2 implementation plan (kod YOK — şartname)

- **Hangi dosya:** YENİ dosya `tests/test_holdout_registry.py` (mevcut
  `test_phase500.py` DEĞİŞMEZ — o dosya holdout feather açtığı için bu
  denetimden muaf tutulur; registry-denetimi feather'sız olmalıdır).
  Alternatif (daha zayıf): M.20 şablonuna doküman-maddesi. Önerilen: İKİSİ
  (test birincil, doküman-madde ikincil).
- **Hangi fonksiyon:** `test_registry_matches_protected()` — registry'deki 4
  pencereyi `p5_splits.PROTECTED` sabitleriyle karşılaştırır (tarih-aralığı
  eşitliği + statü ∈ {CONSUMED, UNTOUCHED} + CONSUMED ise tüketici-kaydı
  varlığı).
- **Invariant:** registry pencereleri == PROTECTED pencereleri (birebir);
  statü kümesi kapalı; tüketim kayıtsız olamaz.
- **Mevcut testle doğrulanabilir mi:** HAYIR (test_phase500 feather açar;
  registry-denetimi feather'sız olmalı) → **yeni küçük test dosyası GEREKİR**
  (gerekçe kayıtlı; kod bu görevde YAZILMADI).
- **Holdout'suz uygulanabilir mi:** EVET (sabit + markdown/json parse only).

## 2. Unknown-source decisions

- `scripts/phase_m20_replication.py` (5.442 B) — import/reference: YOK
  (sıfır kod-bağımlılığı doğrulandı); deney-bağımlılığı: YOK (hiçbir rapor
  girdisi değil); git: untracked; silme-riski: DÜŞÜK (izole) ama
  provenance belirsiz + paralel-oturum sahipliği ihtimali → **ARCHIVE**
  (karantina-dizini + kayıt; silme DEĞİL).
- `experiments/phase_m20_execution/PHASE_M20_EXECUTION_REPLICATION.md`
  (4.101 B) — aynı gerekçeyle **ARCHIVE** (eş-dizin içinde tutanakla).
- DELETE-CANDIDATE: İKİSİ İÇİN DE REDDEDİLDİ (geri-alınamaz + sahiplik
  belirsizliği). INVESTIGATE kapatıldı (taranabilir başka iz YOK).

## 3. Large artifact decisions (silme YOK)

- 5× `rf_seed*.joblib` (37.9MB): **KEEP** — DÜZELTME: 3 canlı tüketici var
  (`phase03_finalize.py:128`, `phase35_diagnose.py:36`, `phase36_exec_study.py:38`
  `joblib.load` çağırıyor). Önceki "ARCHIVE-SAFE" notu YANLIŞTI (sadece
  yeniden-üretilebilirliğe bakılmıştı); bağımlılık nedeniyle KEEP. Git'e girmez.
- `oof500.parquet` (27.3MB) + oof6a/6b/7 + feature parquet'leri: **KEEP**
  (sanity-check'lerin canlı girdisi; yeniden-türetim saatler-sürer).
- 17 dosya 5–20MB (feather'lar + xa/oi + forward418.json): **KEEP**
  (kaynak-veri + checksum'lu; yeniden-indirme maliyetli).
- Politika: >5MB hiçbir şey git'e girmez (LFS'siz); hash-manifestleri yeterli.

## 4. NEXT_PHASE decision: STALE → ARCHIVE (öneri)

Dosya Phase-10 tasarımını gösteriyor (o faz koşup kapandı). UPDATE = yeni faz
tasarımı demek (bu görevde YASAK). KEEP anlamsız (yanıltıcı pointer).
**ARCHIVE** (taşıma onayı ayrı).

## 5. Empty directory decisions (silme YOK)

- `phase_10_paper/`: **KEEP** — `paper_vs_backtest.py:23` default-çıktı yolu
  olarak referans veriyor + config blokları mevcut (canlı olmasa da bağlı).
- `phase_06_x_layer/`, `phase_00_protocol/`, `phase_05_compare/`: **KEEP** —
  kod-referansı yok ama maliyet sıfır + namespace/protokol-belge değeri;
  silmenin faydası yok. DELETE-CANDIDATE: HİÇBİRİ (gerekçe yetersiz).

## 6. Final-test assignment analysis (statü DEĞİŞİKLİĞİ YOK)

- Tüketilen: FINAL_A (P3), FINAL_P5 (M.20-confirm) — kayıtlı, tekrar kullanılmaz.
- Korunan: FINAL_B (RL-rezervi), FINAL_C (karşılaştırma-rezervi) — dokunulmadı.
- Boşluk: P5 sonrası atanmış final-test YOK. Seçenekler (karar DEĞİL, analiz):
  (a) 2025H2 olgunlaşınca M.20 ile belirle + download-then-lock akışı
  (6C-revizyon emsali prosedür şablonu olabilir); (b) forward-paper ile ikame.
  Atama ayrı M.20 ister; bu belgede yapılmadı.

## 7. Canonical test workflow (kod değişikliği YOK)

- **Komut:** repo-kökünden `py -m pytest tests/ -q` (pytest 9.1.1 kurulu, doğrulandı).
- **Hızlı smoke** (seconds, side-effect-free): test_decision_log, test_maxdd,
  test_power, test_sharpe_annualization, test_capital_protection,
  test_phase505_stats, test_phase6a/b/c_features, test_phase501_features,
  test_phase504_walkforward.
- **Ağır suite** (dakikalar; frame-build/model-fit): test_phase502_labels,
  test_phase503_models, test_freqai_readiness, test_rl_phase44.
- **Holdout-gated** (ayrı izin ister): test_phase500 (feather açar).
- **TEMP çözümü:** repo-dışı mutlak-yol yazımı araç-sandbox'una takılıyor;
  driver-dosya ARTIK GEREKSİZ (pytest doğrudan koşuyor) — sorun kapandı,
  kod değişikliği yapılmadı.
- **CI/local farkı:** CI yok; local'de yukarıdaki komut yeterli.

## 8. Untracked classification (209 satır; ~129MB bireysel + collapsed-dizin içerikleri)

- **A KEEP — kritik/kaynak (yaklaşık 70 dosya + 6 faz-dizini + holdout dizini):**
  `src/freqai/p5_splits.py`, `src/rl/decision_log.py`, ~37 phase scripti,
  11 test, sonuç JSON/MD/parquet'leri, holdout dizini (feather+manifest+registry),
  data manifest/checksum JSON'ları, faz rapor MD'leri.
- **B ARCHIVE — korunmalı ama aktif değil (yaklaşık 140 dosya, ~120MB):**
  130 phase_04_rl JSON/JSONL (7-Eylül koşu artıkları), phase_03 trade CSV'leri
  (REPORT-referanslı → pratikte KEEP-yanlı), indirilmiş zip/parquet veriler
  (URL+hash manifestli → yeniden-çekilebilir).
- **C GENERATED — yeniden üretilebilir (log dosyaları, <1MB):**
  download.log/run.log/pilot.log/verify.log ailesi.
- **D UNKNOWN — inceleme gerekli (2 dosya):** §2'deki ikili (ARCHIVE önerili).
- **E DELETE-CANDIDATE:** BOŞ (bilinçli; silinebilir-iddialı dosya YOK).

38 pre-existing dirty tracked dosyaya DOKUNULMADI (ayrı sahiplik; bu planda yok).

---
## PHASE 1 (önce yapılması gereken):
1. Atomik guard commit'i ZATEN YAPILDI (3093dce — teyitli, tekrarlama).
2. HOLDOUT_REGISTRY + INDEX.md + bu planın M.20/user onayı (doküman-katmanı kapanış).

## PHASE 2 (sonra):
3. FIX-2 test dosyası implementasyonu (şartname §1) + koşumu.
4. `next_phase/` ARCHIVE taşıması + unknown 2 dosya karantina.
5. Soğuk-depolama arşivi (B-kategorisi hash-manifestiyle).

## PHASE 3 (sonra):
6. Yeni final-test ataması (M.20) + conventions/test-runner tamamlayıcı işleri
   (test_conventions.py, merkezi to_ms — ayrı mini-turlar).

## DO NOT TOUCH:
holdout dizini + feather'lar · unknown 2 dosya (karantina öncesi) ·
38 kirli tracked · büyük artefaktlar (politika öncesi) · NEXT_PHASE içeriği ·
B/C holdout'ları · P5 feather · config dosyaları.

## REQUIRES USER APPROVAL:
Yukarıdaki FAZ 1–3'ün TÜMÜ (her adım ayrı onay; özellikle: commit'ler,
arşiv taşımaları, unknown disposition, final-test ataması).

VERDICT: CLEANUP DECISION READY
NEXT: USER REVIEW
