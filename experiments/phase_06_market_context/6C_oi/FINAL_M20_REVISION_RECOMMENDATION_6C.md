# FINAL M.20 REVISION RECOMMENDATION 6C (ÖNERİ, ONAY DEĞİL)

**Statü:** Metodolojik öneri. Deney tekrar çalıştırılmadı, veri indirilmedi,
fit yok, lock değiştirilmedi, onay verilmedi.

## 0. Aritmetik düzeltme (önce hata, sonra doğrusu)

STOP raporundaki "603 VAL satırı" ifadesi YANLIŞTIR: 603, 5 kolonun hücre-NaN
toplamıdır (aynı satır 5 kez sayıldı). Doğrusu (ampirik teyitli): drop edilecek
**union = 291 bitişik satır** (2023-06-06 11:20 → 2023-06-07 11:30),
**%0.5615 VAL**. Union == z_288 kümesi. Bu düzeltme STOP-yanlı hatayı AŞAĞI
yönlü düzeltti (kurtarma-yanlı değil) — aynen raporlanıyor.

## 1. Alt sorular (kilitli tanımlar)

- **Corrupt observation:** `OI ≤ 0` snapshot (piyasa işlem görürken).
- **Neden invalid:** OI kesin-pozitif stoktur; sıfır + NaN-companion = yayın
  arızası, ekonomik gerçeklik değil (3 blokta aynı imza).
- **İşaretleme:** ingestion'da noktasal boolean; gelecek bilgisi yok.
- **Yayılım:** exact formüllerle deterministik (chg: dokunan satır; z/range:
  pencere-içi her satır).
- **Drop vs STOP:** satırlar düşer (nedensel eksiklik); STOP yalnızca kabul
  gate'i aşılırsa.
- **Maksimum kayıp:** kabul gate'iyle önceden sınırlanır (§3).

## 2. Seçenek karşılaştırması (7 eksen)

**A) Strict complete-case (VAL missing=0):** post-hoc riski SIFIR; bias yok;
kayıp = deneyin tamamı (kapanış); güç YOK (deney yok); repro tam; leakage
YOK; ekonomik yorum YOK. **Hüküm: en temiz protokol; bedeli sorunun cevapsız
kalması. Geçerli fallback.**

**B) Sabit yüzde tolerans (%1, mekanizma-denetime bağlı):** post-hoc riski
KISMİ (aşağıda savunması); bias SINIRLI (≤%1 en-kötü rejim-seçimi + venue
belgeli); kayıp %0.56; güç ETKİLENMEZ (n_top ~5.170 vs ~5.180);
repro TAM; leakage YOK; ekonomik yorum BÜTÜN (eşikler aynı).
**Hüküm: ÖNERİLEN.**

**C) İkili oran (invalid-% + affected-%):** iki sayı = iki kalibrasyon yüzeyi;
ilke kazandırmaz, karmaşa katar. Mekanizma-denetime bağlı tekil %1'e indirgenir.
**Hüküm: B'ye indirgenir; ayrı kural olarak RED.**

**D) Diğer (süre-sınırı / güç-sınırı / duyarlılık-gate'i):** süre-sınırı
(pencere-boyuna duyarlı, keyfi); güç-sınırı (bu n'de ~%50'ye kadar gevşek —
dişsiz); duyarlılık-gate'i (kendi parametrelerini ister — sonsuz gerileme).
**Hüküm: RED (B'den üstün değil).**

## 3. %1 neden sonuçtan bağımsız sayılabilir (4 savunma)

1. **Konvansiyoneldir:** kaba raporlama granularitesi; 291'den de 603'ten de
   türetilemedi (%0.56'ya da %1.16'ya da eşit değil — ikisine de eşit
   mesafede kaba sayı).
2. **Dişlidir:** 2× olayı (2022-ölçeğinin VAL'deki karşılığı ~%1.1) REDDEDER;
   her şeyi kurtaran ayarlı eşik değildir. Kalibre eşik gözlenen değerin
   hemen üstüne konurdu (%0.6/%1.2); %1 öyle değildir.
3. **Güçten bağımsızdır:** bu n'de güç zaten ~1.0; %1 güç hesabından ÇIKMAZ
   (güçten türetilmiş gibi gösterilmedi).
4. **Düzeltme yönü:** 603→291 düzeltmesi STOP-lehine hatayı düzeltti;
   kurtarma-lehine muhasebe yapılmadı.
   Kalan bulaşma (sayı olay-sonrası yazıldı) AÇIKÇA M.20'ye sunulur +
   anti-ratchet kaydı (§5).

## 4. 291 satırın kural altındaki hesabı

%0.5615 ≤ %1 → KABUL (mekanizma-denetime bağlı: %100 venue-belgeli yayılım,
başka NaN kaynağı yok — VAL NaN kümeleri yalnızca bu aralıkta).
%1 üstü her senaryo (örn. 2× olay) → STOP (kural dişli).

## 5. TRAIN muhasebesi (değişmez)

Kayıp kalemleri ayrı raporlu (pre-coverage ~70k + warmup + glitch-yayılımı);
`n_train ≥ 200k` gate'i aynen. Tolerans YALNIZCA VAL kabulü içindir.

## 6. Firewall

6A/6B VAL sayıları kural seçiminde kullanılmadı. Sınıf-tanımı scout
primitiflerinden; sayı-tartışması bu olaya dair ve yukarıda açıklandı.

## 7. Önerilen revizyon deltaları (M.20 onayına)

1. R-QC filtresi (§1 tanımıyla) lock'a girer.
2. VAL gate: "sıfır" → "mekanizma-denetime bağlı ≤%1 satır; %100 venue-atıflı;
   blok-kanıt tablosu zorunlu".
3. Anti-ratchet: bu tolerans emsal teşkil etmez; gelecek toleranslar kör
   preregistrasyonla yazılır.
4. Split/model/metrik/gate/eşik: DEĞİŞİKLİK YOK.
5. Taze deterministik koşu (devam değil); sonuçlar açıklamayla raporlanır.

## 8. Red yolu (açık tutulur)

M.20 her toleransı reddederse: 6C KAPANIR (A seçeneği). Bu da meşru ve
temizdir; OI sorusu cevapsız kalır. Sahte-üretim (D/E türevleri) hiçbir
koşulda açılmayacaktır.

**READY FOR FINAL M.20 REVISION APPROVAL**
