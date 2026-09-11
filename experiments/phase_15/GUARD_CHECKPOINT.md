# GUARD CHECKPOINT (analiz + mevcut test; commit YOK)

**Kapsam:** İnceleme + var-olan testler. Yeni test/backtest/fit/download/
holdout-açma/commit/push YOK. `test_phase500.py` KOŞULMADI (feather
yüklediği için bu görevde yasak; son bilinen: 19/19 ALL PASS).

## 1. Guard dosyaları

- **`src/freqai/p5_splits.py`** (122 satır) — holdout rezervasyon sabitleri
  (TRAIN/VAL/FINAL_A/B/C/P5 + sha256 pin), `check_not_in_protected`,
  `verify_holdout_hash`, `load_holdout`, `split_train_val_p5`,
  `HoldoutLeakError`/`HoldoutHashError`. Rol: TÜM pencere-guard'larının
  tek kaynağı. Import: stdlib + pandas SADECE (repo-içi bağımlılık YOK).
  İçerik çalışır durumda (aşağıda doğrulandı). Kritik bağımlılık: YOK.
- **`src/rl/decision_log.py`** (177 satır) — `DecisionLogger`, `read_log`,
  `validate_line`, `obs_hash`/`dataset_hash` (+ `canonical_hash`).
  Rol: karar/audit-log bütünlüğü (repro izlenebilirliği). Import: stdlib +
  numpy/pandas + `src.rl.determinism.canonical_hash` (TRACKED dosya —
  aşağıda). İçerik çalışır durumda. Kritik bağımlılık: YOK (tek iç
  bağımlılık tracked).

## 2. Dependency graph özeti

- p5_splits ← 10+ tüketici: phase502_labels, phase504_walkforward,
  phase506/6a/6b/6c/7_run, phase500_holdout_verify, phase_m20_confirm,
  test_phase500/501/502/504, phase10_preflight. Merkezi guard düğümü.
- decision_log ← test_decision_log.py + scripts/phase417_bench.py.
- Ters-yön (guard'ların ihtiyaçları): p5_splits → ∅ (dış paket hariç);
  decision_log → determinism.py (TRACKED, mevcut). Kayıp halka YOK.

## 3. Test sonucu

- `test_decision_log.py`: **6/6 passed (0.77s)**, izole temp-dizin, yan etkisiz.
- `test_phase500.py`: **KOŞULMADI** — `load_holdout()` feather açtığı için
  bu görevde yasak; son bilinen durum 19/19 ALL PASS (oturum kaydı).
- Davranış probu (yeni test DEĞİL, mevcut fonksiyonların çağrısı):
  import OK; temiz tarihlerde `check_not_in_protected` sessiz PASS;
  korumalı tarihlerde `HoldoutLeakError` ABORT. Guard mekaniği canlı.

## 4. SHA256

- `src/freqai/p5_splits.py` — 4978 byte — `96158d134b5d994ab2a9dba1126ca530a87adaf58f1cceabbf3e4b45649d86d8`
- `src/rl/decision_log.py` — 7181 byte — `8fa28a64962e1b3ffe210ac17758777b5672e729d04e07f801929d6a4b1171e6`

## 5. Working-tree durumu

İki dosya da untracked; tracked değişiklik YOK (bu görevde); commit YOK.
İçerikleri bu denetimde okundu, değiştirilmedi.

## 6. Commit readiness

**READY (onay bekleniyor):** iki dosya da atomik commitlenebilir —
harici untracked bağımlılık yok (determinism.py tracked), içerdikleri
sabitler/fonksiyonlar 10+ tüketici tarafından aktif kullanılıyor,
davranış doğrulandı. Dahil EDİLMEYECEKLER (ayrı karar): diğer 200+ dosya,
artefaktlar, unknown dosyalar, holdout verileri, kirli tracked dosyalar.

## 7. Riskler

- Commit gecikirse guard kodu 200+ dosya arasında kaybolma riski sürer
  (bu checkpoint'in varlık sebebi).
- `test_phase500.py` bu görevde koşulmadı — tam guard regresyonu için
  holdout-izinli ayrı tur gerekir (M.20 kararı).
- determinism.py tracked AMA içeriği bu denetimde incelenmedi (sadece
  varlık+import doğrulandı); derin audit istenirse ayrı tur.

VERDICT: READY FOR ATOMIC GUARD COMMIT
NEXT: kullanıcı onayı → yalnızca bu 2 dosyanın atomik commit'i (push YOK)
