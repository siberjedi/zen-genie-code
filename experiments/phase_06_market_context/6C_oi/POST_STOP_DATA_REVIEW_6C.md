# POST-STOP DATA REVIEW 6C — kök neden + etki (analiz; fit YOK)

**Kapsam:** 6C STOP olayının veri-kalite incelemesi. Model fit edilmedi,
deney tekrarlanmadı, sonuç üretilmedi. Bu belge "OI edge yok" demez.

## 1. Kök neden

Binance venue-side yayın glitch'i: `sum_open_interest = 0.0` + oran
kolonları NaN basan snapshot'lar (piyasa o sırada işlem görüyordu — taker
oranları basılı). Borsa-arşivli ham veride mevcut; bizim pipeline'ımız
üretmedi. Toplam 4 blok / 3.5 yıl:

| Blok | Aralık (UTC) | Snapshot | Süre |
|------|--------------|----------|------|
| 2021-05-22 | 04:25 → 05:10 | 10 | 50 dk (TRAIN) |
| 2022-03-07/08 | 15:30 → 01:05 (+1) | 116 | ~9.7 sa (TRAIN) |
| 2022-03-08 | 07:10 (tek) | 1 | 5 dk (TRAIN) |
| 2023-06-06 | 11:20 → 11:35 | 4 | 20 dk (VAL — STOP sebebi) |

Nitelik: venue-kaynaklı (EVET), sistematik (HAYIR — sporadik, 5dk–9.7sa),
noktasal kuralla önceden tespit edilebilir (EVET — `OI ≤ 0`, gelecek bilgisi
gerektirmez), çapraz doğrulanabilirlik (İLKEDE — Tardis/CoinGlass poll arşivi;
yapılmadı, indirme/lisans gerektirir).

## 2. Etkilenen zaman aralığı (feature bazında, VAL)

Kök blok: 2023-06-06 11:20–11:35 UTC (4 snapshot).

| Feature | VAL NaN | İlk | Son | Mekanizma |
|---------|---------|-----|-----|-----------|
| oi_chg_12 | 8 | 11:20 | 12:35 | t veya t−12 ∈ glitch |
| oi_chg_1 | 5 | 11:20 | 11:40 | t veya t−1 ∈ glitch |
| oi_price_div | 8 | 11:20 | 12:35 | chg_12 ile aynı maske |
| oi_z_288 | 291 | 11:20 | ertesi gün 11:30 | 288-pencere bulaşması |
| oi_range_288 | 291 | 11:20 | ertesi gün 11:30 | 288-pencere bulaşması |
| **union** | **603 / 51.825 (%1.16)** | | | |

## 3. Etkilenen örnek sayısı

603 VAL satırı (%1.16). Hiçbir fit yapılmadığı için model sonucu etkilenmedi;
etki, gate'in doğru çalışmasıdır (fail-safe kanıtı).

## 4. Kabul edilebilir yöntemler

- **A (NaN + drop):** kilitli status quo. Leakage YOK (noktasal, nedensel);
  selection bias: venue-kaynaklı eksiklik, açıklanan yönde; sample loss TRAIN'de
  tolere, VAL'de gate'li; reproducible; preregistration-uyumlu (zaten kilitli).
- **B (ingestion-öncesi kalite filtresi):** A ile aynı downstream etki, daha
  temiz pipeline ("OI ≤ 0 → invalid → missing"). Kabul edilebilir; revizyonda
  A'nın yerine geçebilir (eşdeğer).

## 5. Reddedilen yöntemler

- **D (forward-fill):** REDDEDİLDİ. Bozuk/stale observation'ı geleceğe taşır;
  lock'ta açık yasak; glitch anları stres dönemine denk gelebilir (yanlı doldurma).
- **E (dönem silme):** REDDEDİLDİ. "Günü gördük, silelim" post-hoc seçimdir;
  split bütünlüğünü bozar; ön-kayıtlı yazılamaz (veri görüldü).
- **C (pencere değiştirme):** yama olarak REDDEDİLDİ (Madde 20: sonuç/gözlem
  sonrası kural değişmez; üstelik sorunu küçültür, bitirmez). SADECE taze
  preregistrasyonla (yeni hipotez-operasyonelleştirmesi olarak) düşünülebilir.

## 6. Revizyon gerekli mi?

EVET — mevcut lock ile deney koşamaz (STOP deterministik tekrarlar; veri
değişmedi). Revizyon M.20'ye aittir; bu belgede uygulanmadı.

## 7. Önerilen değişiklik (taslak; M.20 onayı gerekir)

R-QC kuralı + glitch-bütçesi (detay DATA_QUALITY_RECOMMENDATION_6C.md):
noktasal `OI ≤ 0 → invalid → missing` filtresi; VAL kabulü = toplam invalid
snapshot ≤ 12 (1 saat) VE her blok ≤ 12 VE tamamı venue-belgeli VE yayılım
satırları raporlu; aksi STOP. Mevcut olay (4 snapshot) bu bütçeye girer.
**Dürüstlük notu:** eşik, olay görüldükten sonra yazıldığı için kısmen
post-hoc bilgilidir; M.20 bunu bilerek karar vermelidir (alternatif: 6C kapatma).
