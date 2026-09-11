# M.20 RE-EVALUATION — frozen H48 sinyali, USD-M futures maliyetiyle

**Kapsam:** Hesap-tekrarı (fit YOK, yeni veri YOK, holdout YOK).
Girdi: results7/oof7 (dondurulmuş skorlar/eventler) + 6B funding arşivi.
**Phase 7 FAIL remains valid under C=0.003.**

## Maliyet (M20, dönem-belgeli)
- fee taker %0.04×2 = 8bp · spread 1bp RT · slip 2bp/side = 4bp → C_FIX = 13bp
- funding: event-başı gerçekleşmiş (237/647 hold settlement kesti, %36.6);
  ortalama +0.356bp → **C_M20_avg = 13.36bp (0.0013356)**
- Duyarlılık: güncel %0.05 taker → +2bp (sonuç değişmez, aşağıda).

## Popülasyon berraklığı (düzeltme kaydı)
İki ayrı popülasyon vardır, karıştırılmayacak:
- **Event seti** (traded rule, BİRİNCİL): frozen TRAIN-q90, n=647,
  gross +0.5771%.
- **Pooled decile** (sinyal-kalite sürekliliği): n_top=5.177,
  gross +0.2342% (Phase 7 raporundaki sayı budur).

## Sonuçlar
- Event: net **+0.4435%**, θ +8.75 CI [6.91, 11.66], edge 3.32, MaxDD 0.901.
- Decile: net +0.1006%, edge 0.75.
- AUC 0.6019, rankIC 0.0544 (maliyetsiz, aynen).
- Break-even: event %0.5771, decile %0.2342. Marj (C_M20'ye): +%0.4435 / +%0.1006.

## Karar: B — Pozitif ama zayıf/kırılgan → bağımsız doğrulama gerekli
Gerekçe: net>0 her iki bazda; AMA MaxDD 0.90>0.20 (kilitli gate FAIL),
decile-edge 0.75<1.2 (FAIL), event seti %1.2 aşırı-kuyruk (eşik-transfer
başarısızlığı) + √1305 annualization şişirmesi. C statüsü (güçlü pozitif)
kazanılmadı; A (negatif) de değil.

## Sonraki faz
Bağımsız doğrulama protokolü için ayrı M.20 kararı gerekir (holdout bu
oturumda açılmadı; P5/B/C/A kilitli). Bu oturumda commit/push yok.
