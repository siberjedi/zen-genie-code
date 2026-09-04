# Faz 3 — Kilitli Label Tanımı (2026-09-04, sonuç öncesi kilitli)

Kaynak: `src/freqai/labels.py:1`. Değişiklik = yeni Final Test gerekir.

## Tanım
- **Horizon H = 12 mum** (5m → ~1 saat).
- **Threshold = 0.002 (%0.2)** = round-trip maliyet (`fee_taker 0.001 × 2`,
  `config/experiment.yaml:77-78`). Gerekçe: maliyetin üstündeki hareket "işe yarar sinyal".
- `label[t] = 1` eğer `close[t+12]/close[t]-1 > 0.002`, yoksa `0`.

## Sızıntı disiplini
- Future return SADECE label için kullanılır.
- Feature'lar label adımından bağımsız üretilir (`build_features` → `build_labels` → join);
  test, label adımının feature değerlerini değiştirmediğini kanıtlar.
- Son 12 satırın label'ı tanımsızdır (NaN) ve ATILIR. Bu kayıp mekaniktir
  (tarih aralığına bağlı değil), seçim yanlılığı yaratmaz.

## Sınıf dengesi
- Dengesizliğe karşı `class_weight="balanced"` (model kartında kilitli).
- Gerçek label oranı deneyde raporlanacak; threshold orana göre AYARLANMAYACAK.

Doğrulama: `tests/test_freqai_readiness.py::test_label_definition` — PASS.
