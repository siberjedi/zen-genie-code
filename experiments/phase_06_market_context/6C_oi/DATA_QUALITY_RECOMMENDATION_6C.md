# DATA QUALITY RECOMMENDATION 6C — önceden-belirlenebilir kural (öneri)

**Statü:** Metodolojik öneri. M.20 lock'una uygulanmadı; onay/red otoritenindir.

## Önerilen kural (R-QC + glitch bütçesi)

1. **Gözlem filtresi (noktasal, nedensel):** `OI ≤ 0` snapshot INVALID sayılır
   → missing (NaN); doldurma/interpolasyon YOK.
2. **Yayılım:** feature pencereleri NaN'ı exact formüllerle yayar; etkilenen
   satırlar düşer (mevcut politika aynen).
3. **VAL kabul gate'i (revize):** toplam INVALID snapshot (VAL içinde) ≤ 12
   (1 saat) VE her contiguous blok ≤ 12 VE her blok venue-belgeli (sıfır-OI +
   NaN companions) VE yayılım-satır sayısı raporlu. Aksi halde STOP.
4. **TRAIN:** aynı filtre; kayıp satırlar raporlanır; FULL n_train ≥200k gate'i
   aynen kalır.
5. **Neden snapshot-bütçesi (satır-bütçesi değil):** tolerans NEDENE (glitch
   süresi) bağlanır, etkiye değil — yayılım pencere-boyuna bağlı olduğundan
   satır-eşiği pencere seçimine göre oynamamalıdır.

## Şartlar (kuralın geçerlilik koşulları)

- Filtre yalnızca `OI ≤ 0` noktasal koşuluna dayanır (gelecek bilgisi yok).
- Bütçe sayıları (12/12) revizyon lock'unda sabitlenir, koşu sırasında değişmez.
- Her blok ham kanıtıyla (tarih/saat/adet) raporlanır.
- Oran-kolonları bu kuralın dışındadır (deneyde kullanılmıyor).

## Dürüstlük kaydı (okunmadan geçilmemeli)

Bu eşikler olay görüldükten sonra yazıldı (4 snapshot biliniyor). Dolayısıyla
tam "ön-kayıtlı" sayılmaz; M.20'nin tercihi: (i) bu haliyle kabul (pragmatik,
gerekçeli), (ii) daha muhafazakar eşikle kabul, veya (iii) 6C'yi kapatma.
Üçü de meşrudur; seçim otoritenindir.

## Alternatif (eşdeğer)

B-formu (ingestion filtresi) benimsenirse downstream etkiler birebir aynı
olmalıdır (test ile kanıtlanır); aksi halde ayrı tasarım sayılır.

## M.20 revizyon paketi (gerekli değişiklik listesi)

1. Lock §8/§10'a R-QC filtresi + glitch-bütçesi ekle (sayılar sabitli).
2. VAL gate ifadesini "sıfır" → "bütçe-içi" olarak güncelle.
3. RUN_REPORT şablonuna blok-kanıt tablosu ekle.
4. Split/model/metrik/gate zincirine DOKUNMA.

**Karar otoritenindir; bu belgede deney tekrarlanmadı, lock değiştirilmedi.**
