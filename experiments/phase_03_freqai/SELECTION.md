# Faz 3 — Seed Seçim Kuralı (sonuç öncesi kilitli, 2026-09-04)

Final Test A'ya bakılmadan, validation sonuçlarına göre tek kural:

1. 5 seed'in validation Sharpe'ları (`daily_365`, kendi metodolojimiz) sıralanır.
2. **En yüksek validation Sharpe'lı seed seçilir** (dondurulmuş konfigürasyon).
3. Eşitlikte küçük seed numarası kazanır.
4. Seçilen seed'in full-train modeli Final Test A'da TEK SEFER değerlendirilir.
5. Final Test A sonucu ASLA tuning/seçimde kullanılmaz (yalnızca rapor).

Bu kural deney çalışmadan önce yazıldı; sonuçlara göre değiştirilemez.
