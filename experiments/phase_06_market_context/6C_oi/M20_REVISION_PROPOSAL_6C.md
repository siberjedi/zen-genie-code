# M.20 REVISION PROPOSAL 6C — QC revizyon tasarımı (TASLAK, ONAY YOK)

**Statü:** ÖNERİ. Deney tekrar çalıştırılmadı, veri indirilmedi, fit yok,
onay yok. Revizyon yalnızca burada tasarlandı; lock'a uygulanmadı.
**Referanslar:** 6C lock/review/run/STOP raporu, POST_STOP_DATA_REVIEW_6C,
DATA_QUALITY_OPTIONS_6C, DATA_QUALITY_RECOMMENDATION_6C, 6A/6B kilit-sonuç,
DESIGN_500, PROTOCOL.md.

## 1. Genel kural (sonuçtan bağımsız bölüm)

**R-QC (gözlem filtresi):** OI snapshot'ı VALID iff `OI > 0`. Gerekçe: OI,
işlem gören piyasada kesin pozitif bir st measurements stoktur; OI=0 +
eşlikçi-NaN oranlar kombinasyonu ekonomik gerçeklik değil yayın arızasıdır
(2021/2022/2023 bloklarının üçünde de aynı imza; taker oranları basılıyken
OI=0 imkansızdır). Tespit noktasaldır, gelecek bilgisi gerektirmez.

**İşaretleme:** ingestion'da boolean `valid` damgası; invalid → missing (NaN).
Doldurma/interpolasyon YOK.

**Yayılım:** feature pencereleri NaN'ı exact formüllerle yayar (chg: dokunan
satır; z/range: pencere-içi her satır). Deterministik, formül-bağımlı,
önceden hesaplanabilir.

**Drop vs STOP:** eksik satırlar düşer (nedensel eksiklik muamelesi); STOP
yalnızca kabul-gate'i (§3) aşılırsa. Satır-düşürme, gözlem-filtresi kadar
geneldir (tarih referansı içermez).

## 2. Sınıf-kuralı vs olay-silme (kritik ayrım)

- **Sınıf kuralı:** "venue-yayınlı invalid observation (OI ≤ 0, piyasa işlem
  görürken), noktasal tespit, missing-muamelesi + yayılım + drop." Bu kural
  2021, 2022 ve 2023 bloklarına AYNI şekilde uygulanır (tarih içermez);
  2023-06-06 görülmeden yazılabilirdi (nitekim NaN-then-drop politikası
  lock'ta zaten vardı).
- **Olay-silme:** "2023-06-06 satırlarını çıkar." Tarih referanslıdır,
  post-hoc seçimdir, split bütünlüğünü bozar. YASAK (değişmedi).
- **Kırılma noktası:** tolerans SAYISI. Sınıf saf, sayı hassastır (§3).

## 3. Tolerans analizi (dürüst çekirdek)

- Nedensel zincir: 4 bozuk snapshot × 288-pencere yayılımı = 603 satır
  (%1.16 VAL). Matematik kaçınılmazdır: strict-zero + bu veri = STOP.
  Koşmak için tolerans > 0 şarttır.
- Konvansiyonel %1 tolerans OLAYI KURTARMAZ (%1.16 > %1) — yani bu koşuyu
  kurtaran her κ (≥%1.16) olaya kalibre edilmiştir. Bu, gizlenemeyecek bir
  post-hoc bulaşmadır; M.20 bilerek karar vermelidir.
- Önerilen form (V1, neden-bağlı): VAL içinde toplam INVALID snapshot ≤ 12
  (1 saat) VE her contiguous blok ≤ 12 VE tamamı venue-belgeli (sıfır-OI +
  NaN companions) VE yayılım-satır sayısı raporlu. Mevcut olay (4 snapshot)
  girer. Neden satır-eşiği değil: tolerans NEDENE bağlanır (etki pencere
  boyuna göre oynar; neden sabittir).
- Alternatif V2 (etki-bağlı): düşen VAL satırı ≤ %2. Mevcut %1.16 girer.
  V1'e göre daha az temizdir (pencere seçimine duyarlı) — yedek olarak sunulur.
- Güç notu: %1.16 kayıp istatistiksel gücü etkilemez (n≈51.2k, top-decile
  ~5.1k); tartışma tamamen protokol-saflığı üzerinedir, istatistik değil.

## 4. Seçenek değerlendirmesi (7 eksen)

**A) Deterministik QC + drop + pre-registered tolerans (V1 önerisi):**
leakage YOK; bias DÜŞÜK (venue-kaynaklı, belgeli); kayıp %1.16 (etki notlu);
repro TAM; güç ETKİLENMEZ; ekonomik yorum DEĞİŞMEZ (ölçek aynı).
Post-hoc bulaşma: VAR (sayı olay-sonrası) — AÇIKLANARAK M.20'ye sunulur.
**Hüküm: ÖNERİLEN REVİZYON (M.20 sahipliğinde).**

**B) Strict VAL=0 + 6C kapatma:** tüm eksenlerde TEMİZ; bedeli OI sorusunun
cevapsız kalması. **Hüküm: MEŞRU ALTERNATİF (varsayılan güvenli seçenek).**

**C) Diğer savunulabilir yaklaşım (incelendi, önerilmiyor):**
nan-aware robust pencereler (min_periods ile geçersiz-gözlem-atlayan rolling)
+ tolerans — genel kırılganlık düzeltmesi olarak DÜRÜST bir motivasyondur AMA:
(i) feature tanımlarını değiştirir (yeni operasyonelleştirme = yeni deney
6C′, revizyon değil), (ii) yine tolerans gerektirir (8 satır > 0),
(iii) motivasyonu olay-gözlemlidir. Taze full-lock istenirse düşünülebilir;
bu revizyonda DEĞİL.

## 5. TRAIN kayıp muhasebesi (revizyonda locklanacak ifade)

Toplam FULL train kaybı = pre-coverage drop (~70k, 2020-01→09) + warmup
(z/range ~288 bar + chg) + glitch-yayılım satırları (TRAIN blokları:
2021 ~300, 2022 ~400 satır). Rapor kalemleri ayrı ayrı; kabul gate'i
`n_train ≥ 200k` DEĞİŞMEZ (mevcut tahminle sağlanır; koşuda ölçülür).

## 6. Firewall beyanı

Revizyon tasarımında 6A/6B VAL sayıları kullanılmadı (feature/model/eşik
seçimi scout-primitiflerinden; tolerans tartışması yalnızca 6C olayına dair).
6A/6B dosyalarına dokunulmadı.

## 7. Exact revizyon paketi (lock deltaları)

1. Lock §8/§10'a R-QC filtresi ekle (tanım §1, sayılar YOK).
2. VAL gate: "sıfır" → V1 kuralı (12/12 sayıları sabitli, §3).
3. RUN_REPORT'a blok-kanıt tablosu (tarih/saat/adet/yayılım) zorunlu satırı ekle.
4. Split/model/metrik/gate/eşiklerde DEĞİŞİKLİK YOK.
5. Revize lock altında TAZE koşu (kaldığı yerden devam DEĞİL; deterministik
   yeniden-koşu; sonuçlar revizyon-açıklamasıyla raporlanır).

## 8. Onay-dışı beyan

Bu belge revizyonu TASARLAR; uygulamaz, onaylamaz. Koşu, indirme, fit YOK.
Sonuç cümlesi otoritenindir.

**READY FOR FINAL M.20 REVISION APPROVAL** (paket hazır; onay otoritenindir)
