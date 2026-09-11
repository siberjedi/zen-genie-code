# CLEANUP APPROVAL — PHASE 1 (doküman/onay katmanı; UYGULAMA YOK)

**Kapsam:** FAZ 1 yalnızca. Silme/taşıma/rename/commit/push/test YOK.
Bu dosya, CLEANUP_DECISION.md kararlarını referanslar; çelişki YOK
(9/9 nokta programatik doğrulandı, aşağıda).

## Onaylanan durum (Research Pause)

Araştırma duraklatıldı; laboratuvar denetim altında tutuluyor. Yeni
hipotez/deney/backtest/fit/download/holdout-açma YOK.

## Karar kayıtları (DECISION ile birebir)

- Guard checkpoint commit: **3093dce** ("chore: checkpoint holdout guard
  infrastructure") — teyitli, tekrarlanmayacak.
- Holdout registry: OLUŞTURULDU (`phase_05_ml/holdout/HOLDOUT_REGISTRY.md`);
  statüler DEĞİŞTİRİLMEDİ (bu dosyaya dokunulmadı).
- FIX-2: HENÜZ UYGULANMADI (şartname duruyor; kod/test yazılmadı).
- NEXT_PHASE_DESIGN: ARCHIVE olarak PLANLANDI; TAŞINMADI (Faz 2 işi).
- RF/joblib (5×38MB): KEEP (canlı tüketici var); dokunulmadı.
- 4 boş dizin: KEEP; dokunulmadı.
- Unknown-source 2 dosya: dokunulmadı (karantina Faz 2 işi).
- Büyük artifact'ler: dokunulmadı (politika Faz 2 işi).
- 38 dirty tracked: korundu; dokunulmadı.
- 209 untracked: temizlenmedi (kategorizasyon kayıtlı).

## Tutarlılık beyanı

CLEANUP_DECISION.md ile bu dosya arasında çelişki YOKTUR (otomatik kontrol:
guard-hash, registry, FIX-2-durumu, NEXT_PHASE-planı, RF-KEEP, unknown,
artifact, dirty, untracked — 9/9 eşleşti).

## Faz 2'ye devredilenler (bu fazda YAPILMADI)

FIX-2 implementasyonu + koşumu · NEXT_PHASE arşiv taşıması · unknown
karantina · soğuk-depolama arşivi. Hepsi ayrı onay ister.

VERDICT: PHASE 1 COMPLETE
NEXT: USER REVIEW → PHASE 2
