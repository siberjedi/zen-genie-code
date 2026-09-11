# CLEANUP PLAN (öneri; UYGULAMA YOK — onay gerekli)

**Kapsam:** Bu oturumun denetimine dayanır. delete/move/rename/refactor/commit/
push/backtest YOK. Holdout açılmadı. Kod değiştirilmedi.

## 1. İki unknown-source dosya

- `scripts/phase_m20_replication.py` (5.442 B, 09.09 13:12:09) + `experiments/phase_m20_execution/PHASE_M20_EXECUTION_REPLICATION.md` (4.101 B, 13:13:36).
- **Bağımlılık:** SIFIR kod-bağımlılığı (hiçbir dosya import/çalıştırmıyor; yalnızca benim denetim notlarım + phase_m20_confirm.py docstring'indeki kendini-koruma notu referans veriyor). Kaldırılması hiçbir şeyi kırmaz; tutulması kirletmez.
- ACTION: M.20 disposition (adopt/quarantine/remove) · RISK: düşük (izole) · WHY: provenance belirsizliği denetim izini kirletiyor · DEPENDENCY: yok · SAFE TO EXECUTE: **NO** (onay gerekli).

## 2. Altı büyük artifact (>20MB)

- 5× `freqtrade/user_data/Freqai_models/rf_seed*.joblib` (37.9MB) + `results/oof500.parquet` (27.3MB) + 17 dosya 5–20MB (feather'lar, xa/oi parquet'ler, forward418.json).
- **Arşivlenebilirlik:** joblib'ler yeniden-üretilebilir (eğitim scripti + seed mevcut) + hash-referanslı (RESULT raporunda) → ARCHIVE-SAFE (hash manifestiyle). oof/feature parquet'ler yeniden-türetilebilir (saatler-mertebe CPU) → ARŞİVlenebilir ama pratikte KEEP (hesap > disk). Feather ham veriler → KEEP (yeniden indirme maliyetli + checksum'lu). Hepsi .gitignore'suz + untracked → git'e GİRMEZ (LFS bile önerilmez; manifest-hash + untracked-tutma).
- ACTION: arşiv-politikası onayı (soğuk-depolama listesi) · RISK: düşük · WHY: 680MB worktree şişkinliği · DEPENDENCY: hash-referansları korunmalı · SAFE: **NO**.

## 3. Untracked kategorizasyonu (209 satır; ~129MB bireysel + collapsed-dizin içerikleri)

- **A = kesin gerekli:** `src/freqai/p5_splits.py`, `src/rl/decision_log.py` (**kritik bulgu:** guard kodunun kendisi untracked — ÖNCE commitlenmeli); ~40 phase scripti (repro kayıtları); 11 test; sonuç JSON/MD/parquet'leri; holdout dizini içeriği; manifest/checksum JSON'ları.
- **B = experiment artifact:** 130 phase_04_rl JSON/JSONL (7 Eylül koşu artıkları; scriptlerle yeniden-üretilebilir) + phase_03 trade CSV'leri (REPORT_418 referanslı → KEEP); indirilmiş zip/parquet veri (URL+hash manifestli → ARCHIVE-SAFE).
- **C = geçici/generated:** `download.log`, `run.log`, `pilot.log`, `verify.log` dosyaları; `__pycache__` (zaten ignored).
- **D = unknown:** yukarıdaki 2 dosya.
- **E = muhtemel gereksiz:** BOŞ (iddialı silme adayı YOK — E listesi bilinçli boş bırakıldı; aday çıkarsa tek-tek M.20 ile).

## 4. Önceden-kirli 38 tracked dosya

Tamamı 4 Eylül faz-1–4 çıktıları + config'ler; bu oturumda dokunulmadı. ACTION: yok (ayrı sahiplik) · SAFE: N/A.

## 5. FIX-needed guard'lar (tam değişiklik şartnamesi, kod YOK)

- **FIX-1 (ÇÖZÜLDÜ):** merkezi registry eksikti → `experiments/phase_05_ml/holdout/HOLDOUT_REGISTRY.md` oluşturuldu (convention: holdout dizini; taşıma YOK).
- **FIX-2 (AÇIK):** registry güncellemelerini zorlayan mekanizma yok. Gereken değişiklik (uygulanmadı): (a) M.20 formalizasyon şablonuna "registry-update adımı" maddesi (doküman), (b) `holdout_status()` çıktısını registry statüleriyle karşılaştıran salt-okunur denetim fonksiyonu (örn. `audit_holdout_registry()` → PASS/MISMATCH raporu; otomatik-düzeltme YOK). SAFE: NO (onay + implementasyon turu gerekli).

## 6. NEXT_PHASE kararı: STALE → ARCHIVE önerisi

`next_phase/NEXT_PHASE_DESIGN.md` Phase-10 tasarımını gösteriyor (o faz koşup kapandı). UPDATE = yeni faz tasarımı demek (bu görevde YASAK). Öneri: arşiv dizinine taşıma veya STALE banner (ikisi de onay ister). **Karar: STALE (mevcut); önerilen aksiyon: ARCHIVE.**

## 7. Test-runner TEMP çözümü (kod değişikliği YOK)

- Kök neden: Write aracı workspace-dışı mutlak yolları (`C:\Windows\Temp`) sandbox'lıyor — dosya "yazıldı" görünüp exec anında yok. Repo kodu DEĞİL, araç-davranışı; değiştirilecek repo kodu YOK.
- Çözüm (öneri, uygulama YOK): driver-dosyasız koşu — `py -m pytest tests/ -q` (pytest 9.1.1 kurulu, doğrulandı) repo-kökünden; veya mevcut PowerShell `py -3 tests/test_X.py` deseni. Her ikisi de ek dosya gerektirmez.

## 8. Holdout bağımlılık haritası (dokunma-yasağı gerekçesi)

`holdout/*` dosyalarına bağımlılar: `phase500_download_holdout.py` (üretici), `phase500_holdout_verify.py` (doğrulayıcı), `phase_m20_confirm.py` (tek yetkili tüketici), `p5_splits.py` (sabit/guard), `test_phase500.py` (guard testleri), M20 formalizasyon + HOLDOUT_LOCK + yeni registry (doküman). Sonuç: dizine silme/taşıma/rename = 4 bağımlıyı kırar → **DO NOT TOUCH.**

---
## SAFE CLEANUP:
- (Şu anda güvenle yapılabilecek işlem YOK — her aksiyon onay/uygulama turu ister; bilinçli boş bırakıldı.)

## REQUIRES REVIEW:
1. Faz-kapanış commit'leri (atomik, push'suz).
2. Unknown 2 dosya disposition (adopt/quarantine/remove).
3. Arşiv politikası (soğuk-depolama listesi + hash manifesti).
4. `next_phase/NEXT_PHASE_DESIGN.md` ARCHIVE taşıması.
5. Boş placeholder dizinler (4 adet: stub mu kaldırma mı?).
6. Yeni final-test ataması (P5 sonrası boşluk).
7. `tests/test_conventions.py` + merkezi `to_ms()` + tek-komut test koşucu.
8. FIX-2 registry-denetim fonksiyonu.

## DO NOT TOUCH:
- `experiments/phase_05_ml/holdout/*` (bağımlılık haritası §8).
- Unknown 2 dosya (M.20 tasarrufu öncesi).
- 38 önceden-kirli tracked dosya.
- Büyük artefaktlar (politika onayı öncesi).
- `next_phase/NEXT_PHASE_DESIGN.md` içeriği.
- B/C holdout'ları + P5 feather (tüketilmiş olsa da kanıt).

VERDICT: CLEANUP PLAN READY
NEXT: USER APPROVAL
