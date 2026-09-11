# RESEARCH PAUSE — REPOSITORY HARDENING (denetim; değişiklik YOK)

**Statü:** AUDIT. Silme/taşıma/rename/commit/push YOK. Yeni hipotez/deney YOK.
Aşağıdaki "önerilen temizlik" SADECE öneridir; uygulama kullanıcı onayı ister.

## 1. Repo durumu

- 17 experiment dizini (4'ü BOŞ placeholder: phase_00_protocol, phase_05_compare, phase_06_x_layer, phase_10_paper).
- ~40 phase scripti (`scripts/phase*.py`), 21 test dosyası, faz-başı sonuç JSON/parquet artefaktları.
- Tüm faz dizinleri + scriptler + testler bu oturumda üretildi ve untracked durumda.

## 2. Git durumu

- Toplam 247 değişiklik: **209 untracked** (130 phase_04_rl artefaktı [7 Eylül'den kalma] + ~40 script + 11 test + faz dizinleri), **38 tracked-modified** (tamamı 4 Eylül öncesi faz-1–4 çıktıları + config'ler; bu oturumda dokunulmadı).
- Bu oturumda COMMIT YOK (bilinçli; denetim izi riski §10'da).

## 3. Holdout durumu

- FINAL_P5: CONSUMED (M.20-confirm) · FINAL_A: CONSUMED (P3) · FINAL_B/C: UNTOUCHED.
- Detay: `experiments/phase_05_ml/holdout/HOLDOUT_REGISTRY.md` (YENİ, bu görevde).
- Açık kalem: P5 yerine yeni final test atanmadı.

## 4. Unknown-source dosyalar (DOKUNULMADI)

- `scripts/phase_m20_replication.py` (5.442 byte, 09.09 13:12:09) — M.20 re-evaluasyonun alternatif implementasyonu (slippage varsayımı farklı: 10bp vs 4+1bp). Okundu, çalıştırılmadı, kullanılmadı.
- `experiments/phase_m20_execution/PHASE_M20_EXECUTION_REPLICATION.md` (4.101 byte, 09.09 13:13:36) — yukarıdakinin rapor eşi.
- Neden unknown: bu oturumun tool-call kaydında oluşturulma izi yok; paralel oturum/kullanıcı eliyle yazılmış olabilir. Taramada başka unknown dosya BULUNAMADI (bugünkü mtime'lı diğer tüm dosyalar bu oturumun kayıtlı tool-call çıktılarıyla eşleşiyor).
- Öneri: M.20 sahibi adopt/quarantine/remove kararı versin; sonuçlarım bağımsızdır.

## 5. Büyük artifact'ler (SİLİNMEDİ, liste)

- 37.9MB ×5: `freqtrade/user_data/Freqai_models/rf_seed*.joblib` (P3 modelleri).
- 27.3MB: `experiments/phase_05_ml/results/oof500.parquet`.
- P14 aggTrades zip'i diske YAZILMADI (stream işlendi; 2.6GB yer kaplanmadı — iyi).
- Politika: >20MB dosyalar git'e GİRMEMELİ (LFS veya manifest-hash ile dışarıda tutulmalı); oof parquet'leri tekrar-üretilebilirlik için gerekli (tutulmalı, untracked).

## 6. Encoding/unit/timestamp riskleri (kod değişikliği YOK — borç kaydı)

- **cp1254 konsol:** Türkçe karakterli `print` 6 kez crash üretti (test/check isimleri ASCII'ye çevrilerek geçildi). Kalıcı çözüm: `PYTHONIOENCODING=utf-8` + `tests/test_conventions.py`.
- **pandas3 datetime birimi:** `astype(int64)` ns/ms karışıklığı 4 ayrı bug üretti (phase6c/10/11 + testler); hepsi `Timedelta-bölmeli` ms dönüşümüne çevrildi. Kalıcı çözüm: merkezi `to_ms()` helper (şu an 3 scriptte kopyala-yapıştır var).
- **BTC/USD/USDT mixed-unit:** Phase 11'de ~$1.18M artefakt üretti; BTC-numeraire + kimlik-assert'i ile yakalandı/düzeltildi. Kalıcı çözüm: para-birimi soneki zorunluluğu (`_btc/_usd`) + her muhasebe modülünde flat-market kimlik testi.
- **Timezone:** tz-naive/tz-aware karşılaştırma 2 kez patladı; `tz_localize('UTC')` guard pattern yerleşti ama merkezi değil.
- **Basis/funding birimi:** bp vs oran karışma riski (R-QC notlarında belgeli).

## 7. Guard durumu

- MEVCUT ve ÇALIŞIYOR: `check_not_in_protected` + `HoldoutLeakError`, `verify_holdout_hash` + `HoldoutHashError` + sha256 pin (`2441bf17…`), label-bound kesimi, split guard'ları, test_phase500 (19 test).
- EKSİK (FIX NEEDED — kod yazılmadı, sadece işaret): (a) merkezi `HOLDOUT_REGISTRY` vardı-yoktu → BU GÖREVDE oluşturuldu (çözüldü); (b) `next_phase/NEXT_PHASE_DESIGN.md` STALE (Phase-10 tasarımını gösteriyor) → §8; (c) birleşik test koşucu yok (20+ dosya tek tek koşuluyor) → öneri §10.

## 8. NEXT_PHASE stale durumu

`STALE — UPDATE REQUIRED BEFORE NEXT EXPERIMENT`. İçerik Phase-10 tasarımını gösteriyor (o faz koşup kapandı). Otomatik doldurulmadı (yasak). Yeni faz açılmadan önce ya arşivlenmeli ya güncellenmeli.

## 9. Test durumu

- Syntax: 102 dosya `py_compile` PASS (bu denetimde koşuldu).
- Canlı smoke: `test_phase505_stats.py` 19/19 ALL PASS (bu denetimde koşuldu).
- Tam paket: BU DENETİMDE KOŞULMADI (çoğu suite model fit ediyor; ~10+ dk, sonuçlar zaten faz-raporlarında kayıtlı ve oturum-içi yeşildi). Öneri: `py -m pytest tests/ -q` tek komutu + CI yok (eklenebilir).

## 10. Önerilen temizlik listesi (SADECE ÖNERİ — uygulama YOK)

1. Faz-kapanış commit'leri (P5→P15 sırasıyla, küçük atomik commitler; push YOK, kullanıcı onayı sonrası).
2. `next_phase/NEXT_PHASE_DESIGN.md` → arşivle veya güncelle.
3. Boş placeholder dizinler (phase_00_protocol, phase_05_compare, phase_06_x_layer, phase_10_paper) → README-stub veya kaldırma kararı.
4. Unknown 2 dosya → M.20 tasarruf kararı (adopt/quarantine/remove).
5. `tests/test_conventions.py` (encoding/unit/timezone kuralları) + merkezi `to_ms()` helper.
6. Büyük artefakt politikası (LFS vs manifest-hash; oof'lar untracked tutulur).
7. Yeni final-test ataması (P5 sonrası boşluk) — ayrı M.20.
8. `run_all_tests` tek-komut koşucu (+opsiyonel CI).
9. `C:\Windows\Temp` altına yazılan geçici driver'lar oturum-dışıdır; repo'yu kirletmedi (bilgi).

---
*Bu belge denetim ürünüdür; kendisi dışında hiçbir dosya oluşturulmadı/değiştirilmedi/silinmedi (çıktı dosyaları §10 kapsamı dışındadır — onlar görevin istenen çıktısıdır).*
