# Phase 4.12 RL Next-Experiment Design Review — 2026-09-04 (tasarım-only)

> Uygulama YOK, training YOK, Final Test B YOK, protokol DEĞİŞİKLİĞİ YOK.
> Kanıt tabanı: Phase 4 (40 koşu) + 4.7 (E1) + 4.11 pilot (B1/B2, 10 koşu) + 4.2/4.5/4.8/4.9 kayıtları.

## 1. H1-H6 karşılaştırma tablosu

| # | Hipotez | Dokunduğu problem | Destekleyen kanıt (4.11 sonrası) | Karşı kanıt | İzolasyon | Reward değişir? | Env değişir? | Protocol? | Ölçek | Başarı kriteri | Başarısızlıkta sonraki adım |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | MTM-dilüsyon çıkış sinyalini boğuyor | Exit kalitesi (WR~0.2, PF~0.3-0.6; exit'ler örnekleniyor ama kaybediyor) | Exit'ler var ama değersiz; uzun-hold zararları (3.5: >60m gross -63.7); churn→hold spektrumunun TAMAMI negatif | Yok (doğrudan test edilmedi) | Realized-only vs MTM A/B, diğer her şey sabit | EVET | HAYIR (kayıt zaten var) | EVET (M.20) | 1 config-mirror × 5 seed = 5 koşu (~2sa) | Exit WR/PF dağılım kayması + Sharpe yönü (n=5 caveat; kilitli eşik DEĞİL) | H5 + gamma-karakterizasyonu (protokolsüz ölçümler) |
| H2 | Obs ölçek gradyanı aç bırakıyor | Öğrenme hızı/kalitesi | Ham: 60k fiyat vs 1e-4 reward (gerçek) | Normalizer 4.4'ten beri AKTİF ve sonuç değişmedi; PPO update'leri sağlıklı (KL 0.006-0.013) | — (tüketildi) | — | — | — | — | — | Emekli: cevaplandı |
| H3 | Chunking kredi-atamayı düzeltir | 315k ufuk / 1.9 episode | Kısmen: 4.7'de 120 episode/koşu ile exploration DÜZELDİ (binlerce SELL) | Ama edge doğmadı → ufuk gerekli-değil-yetersiz | — (tüketildi) | — | — | — | — | — | Emekli (altta yatan sorun değilmiş) |
| H4 | Entropy çöküşü | Keşif çökmesi | Tersine kanıt: entropi sağlıklı (-0.40..-0.61), KL sınırlı | — | — (tüketildi) | — | — | — | — | — | Emekli: çöküş YOK |
| H5 | Rejim uyumsuzluğu | Val-tek-rejim (ralli) yanlılığı | Train %50 negatif ay vs val 1/6 negatif; en iyi sonuçlar ralli-bacakları | Ralli DIŞI da negatif (ayı 2022'de baseline da negatif; Phase 2) | Dondurulmuş E1 modelleri + ayı-penceresi eval (inference-only, mevcut veri+model) | HAYIR | HAYIR | HAYIR | 0 eğitim (sadece inference) | Rejim-kırılımlı AUC/WR/PF (karakterizasyon, seçim DEĞİL) | H1'e git (rejim açıklamazsa) |
| H6 | Sell-keşfi yok | Exit yokluğu | GEÇERSİZ KALDI: 4.7/4.11'de onbinlerce SELL örneklendi | Exit VAR ama değersiz → sorun keşif değil KALİTE | — (evrildi: exit-kalitesi = H1 alanı) | — | — | — | — | — | Emekli (yerini H1 aldı) |

Özel konular: (1) horizon→H1/H3-satırı; (2) reward-ufku→H1; (3) holding/kredi→H1 (+gamma karakterizasyonu desteksiz); (4) rejim→H5; (5) entry/exit→exit'ler var, değersiz (H1); (6) diğer hipotezler→tabloda emekli.

## 2. En güçlü 2 aday hipotez
1. **H1 (birincil):** eleme usulüyle ayakta kalan tek mekanik açıklama. H2/H3/H4 uygulandı-ölçüldü (sorun değilmiş), H6 kanıtla evrildi, masking (4.11) semptomu eledi. Geriye exit-kredisinin yapısı kalıyor.
2. **H5-precursor (destek):** sıfır-eğitim maliyetiyle rejim-kırılımlı tablo; H1 sonucunun yorum çerçevesi olur (ralli-bağımlılık varsa H1 etkisi rejim-şartlı okunur).

## 3. En ucuz ve en temiz deney
- Sıralama: (i) H5 ayı-penceresi eval — 0 eğitim, mevcut model+veri, inference-only; (ii) H1 A/B — 5 koşu (~2sa), tek değişken (reward), E1-control mevcut.
- Temizlik: H1 A/B'de MTM kolu YENİDEN KOŞULMAZ (40 A + 10 B kaydı control); sadece realized kolu koşar. Karşılaştırma aynı metriklerle.

## 4. Protocol impact
- H1: EVET — reward "tek, basit" kilitli tanım; M.20 prosedürüyle değişiklik önerisi (taslak ekinde DEĞİL, ayrı onayda) gerekir. Onaylanmadan KOD YOK.
- H5-precursor, gamma-karakterizasyonu, tüm raporlama: protokol GEREKTİRMEZ.

## 5. Önerilen deney tasarımı (H1 A/B)
- Kollar: MTM (mevcut E1 kayıtları, n=5) vs realized-only (E1 mirror hyperparams, n=5 seed, 600k step, chunk/normalizer/maliyet/pencere aynen).
- Ön-kayıt: yön hipotezi (exit WR/PF iyileşmesi), n=5 caveat, kilitli eşikler seçim-dışı.
- Bütçe: 5 koşu (~2sa) + mevcut kontroller. Final B YOK. Başarı ≠ edge kanıtı (pilot-grade).

## 6. Neden diğerlerinden önce?
- H2/H3/H4: zaten uygulandı ve elendi (tekrarı israf).
- H6: kanıtla evrildi (keşif var, kalite yok).
- H5 tek başına: açıklar ama DÜZELTMEZ (karakterizasyon; H1'in yorum çerçevesi olarak paralel koşar).
- Masking sonrası kalan TEK test-edilmemiş mekanizma H1'dir; alternatifi 42 config'i kör harcamaktır (4.10 kararı bunu yasaklıyor).

## Karar
NEXT EXPERIMENT: H1 (M.20 onayı ARDINDAN; onay yoksa H5-precursor ile sınırlı kalınır, training YOK)
