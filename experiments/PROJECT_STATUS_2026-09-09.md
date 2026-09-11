# PROJECT STATUS REPORT — Phase 0–11 + Mevcut Durum + Önerilen Sonraki Adım
Tarih: 2026-09-09 · Tür: salt-okunur inceleme (kod yazılmadı, faz başlatılmadı, dosya değiştirilmedi — bu rapor hariç)

## 1. Phase 1–11: test edilen hipotezler/stratejiler

| Faz | Hipotez / strateji | Kapsam |
|-----|-------------------|--------|
| P0 | Protokol (20 madde, locked): Train→Validation→Final Test ayrımı, final-test tüketim kuralları | Altyapı |
| P1 | Dry-run altyapısı (Freqtrade + Binance canlı veri, $10 sanal) | İnfra |
| P2 | BaselineStrategy (RSI14 + SMA50/200, 9-fold walk-forward, 18 pair) | Kural tabanlı |
| P3 | FreqAI supervised ML (RF 200/8/50, 8 feat, H=12, 5 seed) | ML, 5m |
| P4 | RL (PPO 4 config × 5 seed, log-portfolio-return reward) + 4.18 decision-level alfa testi | RL |
| P5 | 44-hücreli ML matrisi (4 blok × 3 label × 3 model + baseline + 8 sekonder) | ML, 5m/15m |
| P6 | 7 bilgi kaynağı scout (cross-asset, funding, OI, book, liquidation, news, X) | Araştırma |
| 6A | Cross-asset context (breadth/dispersion/corr, 6 feat) incremental edge | ML + yeni veri |
| 6B | Funding rate (5 feat, settlement-hizalı) incremental edge | ML + yeni veri |
| 6C | Open Interest incremental edge | ML + yeni veri |
| P7 | H48 (4h horizon) swing: aynı pipeline, H=12→48 | Horizon |
| P8 | Cost varsayımı denetimi (C=0.003 savunulabilir mi?) | Metodoloji |
| M.20 | Frozen H48 sinyali + gerçekçi futures maliyeti (C≈13.4bp) re-evaluasyon | Yeniden muhasebe |
| M.20-confirm | M.20 pozitifinin 2025H1'de bağımsız doğrulaması | Holdout testi |
| P9 | Funding & Basis Carry (delta-nötr hasat, statik) | Carry |
| P10 | Calendar & Session (E1 weekend / E2 overnight / E3 post-settlement fade) | Deterministik kural |
| P11 | Dated-futures basis convergence (12 CM quarterly, cash-and-carry) | Carry |

## 2. Hangileri neden FAIL oldu?

- **P1: PASS** (9/9 verifier; tek bulgu infra). Projedeki tek PASS altyapı fazıdır.
- **P2: FAIL** — 9 foldun çoğu negatif net (örn. fold0 −33.9, fold2 −30.5); basit indikatör kuralı fee/slip altında ezildi.
- **P3: FAIL (felaket)** — sinyal her mumda flip → 15–16k trade, fee (~145) brütü ezdi; Sharpe ≈ −25 tüm seed'lerde; Final A tüketildi.
- **P4: FAIL** — 20 koşunun 18'i saf HOLD (0 trade), 2'si şanslı buy-and-hold (tek trade +83.3, 2023H1 rallisi); ajan çıkış öğrenemedi. 4.18: decision-level edge YOK (RL ≈ exposure × drift).
- **P5: FAIL** — 44 hücre, 0 FDR adayı (tüm q=1.0). En iyi hücre E014: AUC 0.679 ama PSS −0.00207, edge −0.69. Sinyal izi var, ekonomik edge yok.
- **6A: FAIL** — ΔPSS −0.000038, CI sıfırı içeriyor; FULL AUC 0.68 ≈ BASE.
- **6B: FAIL** — ΔPSS −0.000037, CI sıfırı içeriyor; funding-only AUC 0.536 (gürültü).
- **6C: STOPPED (veri)** — 2023-06-06 venue glitch → 603 VAL satırı NaN → VAL-missing>0 gate'i STOP verdi. Sinyal hükmü DEĞİL. QC revizyonu tasarlandı (R-QC + tolerans), uygulanmadı.
- **P7: FAIL** — θ=+5.47 CI [3.58,8.89] pozitif GÖRÜNÜYOR ama kırılgan kuyruk artefaktı (647 event, %1.2 oran, MaxDD 0.963); gate zinciri FAIL (PSS<0, d<0.30, q=1.0, MaxDD>0.20). Karşıt kanıt θ12=−5.91.
- **P8: karar A** — C=0.003 DEFENSIBLE (20–30bp bandının üstü, muhafazakar-taraflı). Maliyet darboğaz olarak kilitlendi.
- **M.20: B (zayıf pozitif)** — futures maliyetiyle event net +0.44%, θ +8.75; ama MaxDD 0.90 + decile-edge 0.75 + kuyruk-kırılganlığı → confirmatory DEĞİL, doğrulama gerekli.
- **M.20-confirm: NOT-CONFIRMED** — 2025H1'de θ=−10.22 CI [−23.6,+2.99], net NEGATİF (−0.000933), tüm gate'ler FAIL. M.20 pozitifi replike olmadı. **Bedel: FINAL_P5 (2025H1) TÜKETİLDİ.**
- **P9: BACKTEST STOP** — statik carry tüm teminat senaryolarında likide oldu (tarihsel 9.58× excursion; %500 teminat Şub-2021'de öldü; 10× spike hepsini öldürür). Carry ekonomisi değil, sağkalım mekaniği çöktü.
- **P10: CLOSED (üç FAIL)** — E1 net −0.002082, E2 −0.002761, E3 −0.003009 (≈−C, brüt ~0); q=1.0 hepsi; overlap etkisiz. Takvim anomalisi yok.
- **P11: FAIL** — 12 çeyrekte net −6.15 BTC; gate'lerden sadece net_pos/edge/maxdd geçti; Sharpe CI sıfırı kapsıyor (CI [−1.75,+1.15]), d=0.079, q=0.39. Boğa çeyreklerindeki short-kanama (−4.9/−2.5 BTC) ayı primlerini sildi.

**Ortak problem (tüm fazlar):** predictability izleri mevcut (AUC 0.6–0.68, IC>0) ama execution sonrası ekonomik edge oluşmuyor — maliyet duvarı (30bp) + kısa-ufuk brüt zarfı (~±10bp) + kuyruk-kırılganlığı. 11 fazın 10'u bu duvarın farklı yüzlerine çarptı.

## 3. Açık / planlanmış / kilitli sonraki faz

- **YOK.** Onaylı-bekleyen faz yok. `next_phase/NEXT_PHASE_DESIGN.md` Phase-10 tasarımını gösteriyor (tüketildi, güncel değil).
- **Açık M.20 kalemleri:** (a) tüketilen FINAL_P5 yerine yeni final test belirlenmesi (2025H2 olgunlaşınca veya forward paper); (b) 6C QC revizyonu (tasarım hazır, onay/uygulama yok).
- Kilitli ama çalışmamış iş yok (P11 backtest'i koştu; Phase 10 paper hiç başlamadı — dizin boş).

## 4. Phase 11 bulgularının etkisi

- Carry hattı kapandı: deterministik yakınsama bile (basis ±5bp'de sıfırlanıyor) **marjin dinamiği + boğa-rejiminde short-kanama** yüzünden ekonomik değil. Ders: getiri aritmetiği değil, sağkalım aritmetiği belirleyici — gelecekteki her kaldıraçlı tasarım survival-frontier hesabıyla başlamalı (preflight standardı olarak kalmalı).
- Pozitif bulgu: altyapı olgun (BTC-numeraire muhasebe kimliği 8.68e-15, bağımsız teyit birebir). Metodoloji varlığı: sonuç negatifi güvenilir kılıyor.
- Sonraki araştırmaya etkisi: yönlü-tahmin (P5/6/7/10) + prim-hasadı (P9/11) aileleri kapandı. Kalan alan: ya (a) tamamen yeni mekanizma, ya (b) execution/infra katmanı, ya (c) duraklatma.

## 5. Mevcut altyapı durumu

- **Veri:** BTC 5m feather (2020–2023H1 slice + full 2023 sonu) + 18 pair feeder'lar; 2025H1 holdout feather (tüketildi, hash-pinli); Vision indirilenler: 7 cross-asset 5m, funding (6B), OI metrics, UM 1h, CM quarterly (12 kontrat) — ilgili `data/` klasörlerinde + manifestli.
- **Feature:** `src/freqai/` (kilitli 8+28 feat) + phase501 (28 union, Wilder-native) — stabil.
- **Backtest:** freqtrade docker + phase506/phase6a-c_run/phase7_run/phase10_backtest/phase11_backtest scriptleri — hepsi deterministik (seed42), checkpoint'li değil ama tekrar-koşulabilir.
- **Test/gate:** tests/ altında faz-başı test dosyaları (test_phase500…test_phase6c + RL/Sharpe/power testleri); gate zinciri standardize (PSS/edge/AUC/IC/tau/d/power/q/seed/WF/MaxDD). Birleşik test koşucu YOK (dosya-bazlı `py -3 tests/...`).
- **Holdout'lar:** A TÜKETİLDİ (P3), P5 TÜKETİLDİ (M.20-confirm), B/C KORUNUYOR (RL/karşılaştırma için — dokunulmadı).

## 6. Henüz denenmemiş mantıklı edge hipotezleri (öncelik sırasız, hepsi scout ister)

1. **Maker/limit-order execution rejimi** — spread kazanma (ödeme yerine): L2 verisi + latency altyapısı YOK → önce feasibility (yüksek maliyetli, düşük öncelik).
2. **On-chain akışlar** (borsa netflow, balina hareketleri): mekanizma gerçekten farklı (zincir-içi informed flow); veri erişimi (Glassnode/CryptoQuant katmanları) doğrulanmadı → scout gerekli.
3. **Opsiyon volatilite primi** (Deribit short-vol): veri yükü ağır + marjin karmaşık → scout gerekli, düşük öncelik.
4. **Çapraz-borsa arbitrajı** (spot-spot / spot-perp, venue'lar arası): çoklu-venue veri + transfer/ücret modellemesi yok → scout gerekli.
5. **Negatif kontrol olarak ETH/genelleme testi** — yeni edge DEĞİL ama duvarın evrenselliğini test eder (ucuz, tek fazlık falsifikasyon değeri var).
6. **12h/24h ufuklar** — H48 hattının devamı sayılır; fishing riskiyle SADECE taze M.20 + güçlü gerekçeyle (şu an önerilmiyor).
- **Açıkça önerilmeyenler:** yeni ML mimarisi/feature fishing (P5 kapattı), X/sentiment (arşiv yok), likidasyon-burst timing (veri ücretli + seyrek), parametre-rescue varyantları (yasaklı sınıf).

## 7. Teknik borç, bilinen hata, metodolojik risk

1. **Bilinmeyen-kaynaklı dosyalar:** `scripts/phase_m20_replication.py` + `PHASE_M20_EXECUTION_REPLICATION.md` (09.09 13:12–13:13, oluşturan belirsiz) — okundu, çalıştırılmadı, dokunulmadı; M.20 sahibi tasarruf etmeli (benim sonuçlarım bağımsız).
2. **240 uncommitted değişiklik, 38 tracked-modifiye; bu oturumda commit YOK** — denetim izi riski artıyor; en azından faz-kapanış commit'leri önerilir (karar user'da).
3. **Tüketilmiş holdout'lar kayıtlarda dağınık:** P5 tüketimi MANIFEST/GATE dosyalarında var ama merkezi holdout-ledger YOK — yeni final-test ataması öncesi tek dosyalık `HOLDOUT_REGISTRY.md` önerilir.
4. **cp1254 konsol + pandas3 birim tuzakları** (datetime64[ms] vs ns, `astype(int64)`): 6 fazda gerçek bug üretti; hepsi yakalandı ama `CONTRIBUTING`/checklist notu yok — kalıcı `tests/test_conventions.py` önerilir.
5. **Ölü-kod artıkları:** scriptlerde ulaşılamaz bloklar görüldü (temizlendiği kadarıyla); review disiplini önerilir.
6. **Birleşik test koşucu yok:** 20+ test dosyası tek tek koşuluyor; CI yok.
7. **Büyük artefaktlar untracked** (oof parquet'ler ~28MB vb.) — LFS veya manifest-hash politikası yok; tekrar-üretilebilirlik dosya-varlığına bağımlı.
8. **Metodolojik risk (süregelen):** seçim-yanlılığı baskısı her fazda mevcut (H48/M.20 vakaları belgelendi); replikasyon disiplini (M.20-confirm gibi) standart tutulmalı.
9. **`next_phase/NEXT_PHASE_DESIGN.md` güncel değil** (Phase-10 tasarımını gösteriyor) — ya arşivlenmeli ya güncellenmeli.
10. **Phase 10 paper + phase_06_x_layer dizinleri BOŞ** — planlanıp başlanmamış işler; kapatma/kapsam kararı bekliyor (sessiz borç).

---
*Bu rapor salt-okunur incelemeyle üretildi. Öneriler karar DEĞİL; her biri ayrı M.20 ister.*
