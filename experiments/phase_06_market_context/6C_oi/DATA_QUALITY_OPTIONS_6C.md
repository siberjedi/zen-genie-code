# DATA QUALITY OPTIONS 6C — A/B/C/D/E metodolojik karşılaştırma

Değerlendirme eksenleri: leakage riski · selection bias · sample loss ·
reproducibility · validation integrity · preregistration uygunluğu.

## A) NaN bırak + etkilenen örnekleri düşür (status quo)
- Leakage: YOK (noktasal kural, yalnızca geçmiş/pencere-içi).
- Selection bias: DÜŞÜK (venue-kaynaklı eksiklik; yönü açıklanır).
- Sample loss: TRAIN tolere; VAL'de gate'e takılır (mevcut STOP'un sebebi).
- Reproducibility: TAM (deterministik).
- Validation integrity: KORUNUR (kural a priori idi).
- Preregistration: UYGUN (zaten kilitli). **Hüküm: KABUL (mevcut lock).**

## B) Kalite filtresiyle önceden tanımlı dışlama
- A ile downstream-eşdeğer; pipeline daha temiz (`OI ≤ 0 → invalid`).
- Tüm eksenlerde A ile aynı. **Hüküm: KABUL (A'nın revize ifadesi olabilir).**

## C) Feature window'ını değiştirme
- Yama olarak: preregistration İHLALİ (Madde 20) + sorunu bitirmez (küçültür).
- Taze preregistrasyon olarak: hipotez-operasyonelleştirmesi değişir (farklı
  deney sayılır), yine de glitch'e karşı kırılganlık kalır.
- **Hüküm: YAMA OLARAK RED; taze tasarım olarak M.20'ye açık (önerilmez).**

## D) Forward-fill
- Bozuk/stale değeri geleceğe taşır = icat edilmiş bilgi; lock'ta açık yasak.
- Glitch'ler stres anlarına denk gelebilir → yanlı, tehlikeli doldurma.
- Reproducible olması onu geçerli kılmaz.
- **Hüküm: REDDEDİLDİ (otomatik kabul edilmedi).**

## E) Etkilenen dönemi tamamen dışlama
- Post-hoc gün-silme = sonuç-odaklı örnek seçimi; split bütünlüğünü bozar.
- Önceden yazılabilir hali ("glitch'li günü at") artık yazılamaz (veri görüldü).
- **Hüküm: REDDEDİLDİ.**

## Özet tablosu

| Seçenek | Leakage | Bias | Kayıp | Repro | VAL bütünlük | Prereg | Hüküm |
|---------|---------|------|-------|-------|--------------|--------|-------|
| A | yok | düşük | yönetilir | tam | korunur | uygun | KABUL |
| B | yok | düşük | yönetilir | tam | korunur | uygun | KABUL |
| C | yok | düşük | değişir | tam | BOZULUR (yama) | ihlal | RED (yama) |
| D | VAR (kritik) | yüksek | gizlenir | tam | bozulur | ihlal | RED |
| E | yok | YÜKSEK | gizlenir | tam | bozulur | ihlal | RED |
