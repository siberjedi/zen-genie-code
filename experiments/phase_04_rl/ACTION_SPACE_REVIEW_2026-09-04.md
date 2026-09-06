# Phase 4.10 RL Action Space Design Review — 2026-09-04 (tasarım-only)

> Kod/training/tuning YOK. Final Test B YOK. Mevcut 40 koşu + diag kayıtları
> üzerinden kanıt + teori. Phase 4 sonuçları korunuyor.

## Kanıt özeti (40 koşu, tuning47/run_*.json + diag_*.jsonl)
- Invalid oranı: min %16.5, max %97.0, ortalama %65.6 — 40/40 koşu %1 eşiğinin
  üstünde (gate hard-fail evrensel).
- Sharpe>0 (12 koşu): invalid ort %56.2 | Sharpe≤0 (28 koşu): %69.7.
  En iyi koşular en düşük-invalid koşular: E1/999 (+2.123, %25.2), E6/2026
  (+1.183, %16.5), E6/999 (+1.745, %34.4). İlişki var, nedensellik KANITLI DEĞİL.
- Entropy (SB3 `entropy_loss`, negatif=büyük): E4 -0.343 (en deterministik)
  → E6 -0.613 (en yüksek); KL 0.003-0.01 (öğrenme makinesi sağlıklı).
  Yüksek entropi invalid'i TEMİZLEMİYOR (E3/E6 ent 0.03'e rağmen %28-90).

## 1. Current action space problemi gerçekten önemli mi? EVET
- Olasılık kütlesi: ~2/3 örneklem durum-geçişi üretmiyor → keşif bütçesi ~3x seyrelmiş.
- Entropi tuzağı: invalid ile HOLD aynı sonucu verir → aynı advantage →
  gradyan ayıramaz; entropy bonusu invalid kütleyi AKTİF korur (uniforma iter).
- Kapasite: 3 logit'ten biri her state'te ölü ağırlık; bastırma, sıfır
  reward-gradyanıyla öğrenilmek zorunda (saf temsil yükü).
- Alternatif okuma (dürüstlük): spam dejenerasyonun SEMPTOMU da olabilir.
  Mevcut veriyle yön ayrıştırılamıyor — pilotun varlık nedeni bu.

## 2-3. A/B/C karşılaştırması (11 boyut)
| boyut | A) Current | B) Masking | C) Penalty |
|---|---|---|---|
| MDP değişimi | yok | state-bağımlı 2-aksiyon (geçişler aynı) | geçişler aynı, reward değişir |
| PPO uyumu | native Discrete | YOK (MaskablePPO/sb3-contrib veya özel head gerekir) | trivial |
| exploration | ~3x seyrelmiş | SADECE valid aksiyonlar (2-3x verimli) | ceza kaçınma davranışı eklenir |
| entropy etkisi | invalid kütleyi korur | valid kümede temiz entropi | ceza entropiyle çekişir |
| öğrenme sinyali | bastırma için sıfır gradyan | bastırma yükü kalkar | bastırma gradyanı var (yapay) |
| bias riski | statüko (kalibre-siz politika) | DÜŞÜK (maske gerçek feasible set) | ORTA-YÜKSEK (penalized MDP ≠ true MDP; magnitude hiperparametresi) |
| implementasyon | sıfır (mevcut) | ORTA (dep + mask API + doğruluk testleri) | trivial (1 satır + magnitude) |
| reproducibility | mevcut sistem | aynı sistem + deterministik mask (state fonksiyonu) | aynı sistem |
| protocol impact | YOK | VAR (env tasarımı 4.4'te kilitli → formal faz prosedürü) | VAR (reward "tek, basit" kilitli → prosedür + hacking analizi şart) |
| backtest karşılaştırılabilirliği | baz | ARTAR (backtest de invalid emir üretmez) | AZALIR (cezalı amaç ≠ gerçek amaç) |
| failure modes | bilinen dejenerasyon | maske bug'ı = felaket (valid aksiyonu yasaklarsa); mask-doğruluk testleri şart | ceza büyükse felç, küçükse etkisiz; hacking (cezadan kaçınma) |

Bilimsel en temiz: **B** (confound'u amaç fonksiyonunu değiştirmeden kaldırır).

## 4. Protocol prosedürü (B pilotu için)
Yeni faz dalı (örn. 4.11), ön-kayıtlı: 2 B-config (E1 hiperparametre aynası +
1 ent varyantı) × 5 kilitli seed = 10 koşu (~3.5sa, bütçeden düşer); env/maliyet/
pencere A ile birebir; mask-doğruluk testleri koşul; A-kontrol olarak mevcut
40 koşu yeniden KULLANILIR (tekrar koşulmaz).

## 5. Pilot ölçeği
En fazla 2 config × 5 seed = 10 koşu. Gerekçe: etki yönünü görmek için yeterli,
bütçenin %2'sinden azı; negatif sonuçta kayıp ihmal edilebilir.

## 6. Pilot başarı kriterleri (dinamik-terimli, kârlılık-eşiksiz)
- (a) invalid oranı ≈%0 doğrulanır (mask inşası sanity);
- (b) B-medyan Sharpe − A-medyan Sharpe > 0 (Mann-Whitney yönü, p raporlanır);
- (c) seed-std B'de A-havuzundan küçük; (d) yeni patoloji yok (gate'ler).
Kilitli eşikler (0.80/MaxDD) pilot BAŞARI kriteri DEĞİLDİR (final seçimde geçerli).

## 7. Pilot başarısız olursa
Invalid semptomatik demektir; RL sonucu "mevcut tasarımda edge kanıtı yok"
olarak KALIR, bütçe korunur; sıra 4.2 H1-H6 hipotezlerine (reward/ufuk) geçer.
Başarılı olursa bile "optimize strateji" DEĞİLDİR — candidate hypothesis.

## Karar
- **RUN FORMAL ACTION-SPACE EXPERIMENT** (pilot-ölçekli B; yukarıdaki protokolle).
- Gerekçe: problem evrensel (40/40) + mekanizma maddi (seyrelme + entropi tuzağı +
  kapasite) + test ucuz (~10 koşu) + en temiz varyant (B) ödülü değiştirmez.
- C REDDEDİLDİ (protokol/reward değişimi + hacking + karşılaştırılabilirlik kaybı).
- A-devam REDDEDİLDİ (bilinen-confound'lu tasarıma 42 config gömmek israf olur).

Yeni training YOK (bu rapor sonrası duruluyor; pilot ayrı onayla başlar).
