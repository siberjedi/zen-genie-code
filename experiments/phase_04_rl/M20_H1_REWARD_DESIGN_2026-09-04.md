# M.20 Ön-Kayıt: H1 Reward Experiment — MTM vs Realized-Only (TASARIM, onay bekliyor)

> Statü: TASLAK — kod DEĞİŞİKLİĞİ YOK, training YOK, Final Test B YOK.
> Onaylanmadan implementasyon YASAK. Bu belge sonuç içermez.

## 1. M.20 deney prosedürü
- Branch: `phase-4.13-h1` (kavramsal; açılmadı). Tek değişken: reward sinyali.
- Kollar: CONTROL = mevcut E1 kayıtları (5 seed, yeniden KOŞULMAZ);
  TREATMENT = realized-only, E1 mirror hyperparams, 5 kilitli seed, 600k step,
  chunk/normalizer/maliyet/pencere aynen. Toplam YENİ koşu: 5 (~2sa).
- Seçim YOK, threshold YOK (pilot-grade okuma; kilitli eşikler final seçimde geçerli).
- Final Test B: YOK (veri indirilmedi, metrik görülmedi).

## 2. MTM reward matematiksel tanımı (mevcut, `src/rl/env.py:108-170`)
- `pf(t) = cash(t) + amount(t) × close[t]` (mid, slippage'siz MTM).
- Her adım: `reward(t) = log(pf(t) / pf(t-1))` (`env.py:142`).
- BUY: `exec = close×(1+slip)`, `amount = cash×(1-fee)/exec`, `cash → 0`.
- SELL: `exec = close×(1-slip)`, `cash = amount×exec×(1-fee)`.
- Forced: son mumda aynı SELL matematiği + `reward += log(cash/pf)` (`env.py:157`).
- Özdeşlik: Σreward ≡ log(final/initial) (test-kanıtlı, 1e-9).

## 3. Realized-only reward matematiksel tanımı (ÖNERİ, uygulanmadı)
- BUY anında: `cost_basis = cash` (tüm nakit) kaydedilir; **reward = 0**.
- Pozisyon açıkken (HOLD dahil): **reward = 0** (MTM drift ÖDÜLLENDİRİLMEZ).
- SELL anında: `reward = log(proceeds / cost_basis)`,
  `proceeds = amount × close×(1-slip) × (1-fee)` (mevcut SELL muhasebesiyle birebir).
- Forced liquidation: SELL ile AYNI formül (gerçekleşmiş zarar/kâr tam yansır).
- Flat durumda: **reward = 0**.
- Log birimi korunur (MTM ile aynı ölçekte, karşılaştırılabilir büyüklük).
- Özdeşlik DEĞİŞİR: Σreward = Σ log(proceeds_i/basis_i) ≠ log(final/init)
  genel durumda (açık-drift hariç) — raporlamada açıkça belirtilir.

## 4. İki reward arasındaki tek değişken
- SADECE `reward(t)` atama satırları (`env.py:142` + forced `env.py:157` karşılığı).
- AYNI KALANLAR: portfolio/equity muhasebesi, fee (0.001), slippage (5bps),
  execution (fiyatlar, slip yönleri), obs, chunking (5000), normalizer, PPO
  hyperparams, seedler, timesteps, pencereler, forced-liquidation MEVCUDİYETİ.

## 5. Control/treatment eşleştirmesi
| boyut | CONTROL (E1, kayıtlı) | TREATMENT (realized) |
|---|---|---|
| hyperparams | ent .003/lr 3e-4/n2048/b64/e10/γ.99 | BİREBİR AYNI |
| seedler | 42,7,123,2026,999 | AYNI |
| veri/split/chunk/normalizer | 2020-22/2023H1, 5000, train-fit | AYNI |
| maliyetler | fee .001, slip 5bps | AYNI |
| reward | MTM log | realized-only log |
| n koşu | 5 (mevcut) | 5 (yeni) |

## 6. Ölçülecek metrikler
- Primary (pilot-grade): validation Sharpe median+mean (aynı daily_365 metodoloji).
- Secondary: net, MaxDD(wallet), Sortino, PF, WR, trade count, turnover, fee/gross,
  slip, median hold, forced/non-forced ayrımı, seed std, action dağılımı.
- Diagnostic (uzun-hold teşviki için): hold-süresi dağılımı, forced-exit oranı
  + forced P&L payı, trade-başı net, top-3 konsantrasyon, zero-trade oranı,
  unrealized-drawdown realizasyon oranı (forced ile kapanan zarar payı).
- İstatistik: n=5 caveat; Mann-Whitney yönü + Cohen d (raporlama, eşik DEĞİL).

## 7. Başarı/başarısızlık yorumlama kuralları (ön-kayıtlı, eşik DEĞİL)
- DESTEK (hepsi gerekli DEĞİL, yön aranır): exit WR/PF iyileşmesi + Sharpe
  medyan yönü + hold dağılımının etikete yaklaşması + seed-std kötüleşmemesi.
- RED (hipotez dışı): Sharpe yönü negatif + exit WR/PF kötüleşirse H1 reddedilir
  (sonuç yine de raporlanır; parametreyle oynanmaz).
- Kilitli eşikler (0.80 vb.) pilot BAŞARI kriteri DEĞİLDİR.

## 8. Riskler ve confound'lar
- R1 never-sell patolojisi: realized-only'de zarar realize etmekten kaçınma
  OPTİMAL olabilir; chunk-sınırı forced exit'leri bunu 5000 mumla SINIRLAR
  (teorik üst-bound'lı erteleme). Diagnostic'lerle izlenir (yukarıda).
- R2 seyrek reward: MTM'den DAHA seyrek sinyal → keşif zorlaşabilir (beklenen
  yön: turnover düşüşü; başarısızlık modu olarak ön-kayıtlı).
- R3 n=5: istatistiksel güç düşük; yön + tutarlılık okunur, hüküm verilmez.
- R4 forced-paylaşım: chunk-boundary forced'lar iki kolda da AYNI mekanikle
  çalışır (kontrollü confound).

## 9. Protocol impact
- EVET, resmi M.20 dalı GEREKİR: reward "tek, basit log portfolio return"
  kilitli tanımdır; bu belge değişiklik ÖNERİSİDİR, değişiklik değil.
- Onaylanmadan: kod YOK, koşu YOK. Onaylanırsa: yalnızca bu belgede yazan
  kapsamda implementasyon + test + 5 koşu; kapsam dışı her şey YASAK kalır.

## 10. Uygulama öncesi gerekli testler (onay SONRASI, koşu ÖNCESİ)
- T1: BUY→reward 0; T2: hold→reward 0 (pozisyonlu/pozisyonsuz);
  T3: SELL→log(proceeds/basis) exact; T4: forced→SELL ile aynı formül;
  T5: Σreward ≠ telescoping (beklenen FARK documented); T6: MTM kolu
  regresyonu (mevcut 12 test yeşil kalmalı); T7: mask/guard uyumluluğu.

## SON KARAR
READY FOR M.20 APPROVAL (tasarım eksiksiz, kapsam kilitli, riskler ön-kayıtlı;
onay yoksa H5-precursor ile sınırlı kalınır, training YOK)
