# LEAKAGE ASSESSMENT 6C — observation / publication / availability / decision

Karar anı: BTC 5m bar close `t`. Kural: snapshot yalnızca `create_time ≤ t`
ise o bar'da kullanılabilir (asof-backward, yuvarlama yok).

## Zaman ayrımı (S1)

- **Observation time:** `create_time` (borsa snapshot anı, 5m kadans).
- **Publication time:** ertesi günkü günlük dosya yayını — TARİHSEL çalışmada
  etkisizdir (2020–2023 barları o tarihte de mevcuttu; klines ile aynı mantık).
- **Availability time:** `create_time` (+saniyeler; exchange push/poll).
- **Decision time:** bar close `t`.
- "Timestamp var" yeterli değildir; yukarıdaki kuralı sağlayan birleştirme
  (merge_asof backward, exact-ms) zorunludur. Bar-içi türev istatistik
  (örn. bar-içi OI max) feature OLAMAZ.

## Geceyarısı kuralı

İki dosyadaki çakışan bucket için deterministik dedup (öneri: ilk-görüneni
tut); dedup sonrası kalan dup → STOP. Kural lock'ta kilitlenir.

## Üçüncü-parti ikazı (S4/S5, yalnızca fallback'te)

- Poll-damgalı serilerde (S5) damga = poll anı, event anı değil → karar anına
  geriye yuvarlama; ileri-yuvarlama YOK.
- Revize edilebilir serilerde revizyon-dondurulmuş snapshot şartı; beyan yoksa
  HIGH LEAKAGE RISK → kullanılmaz.
- Sağlayıcı gecikme beyanı + kaydırma (6B D1 emsali) lock'a girer.

## Yasaklar

- İleri-yuvarlama (ceil) ile bar atama YOK.
- Eksik gün/snapshot doldurma YOK (satır düşer).
- Oran-sütun boşluklarını OI ile doldurma YOK (ayrı politika veya kullanmama).
