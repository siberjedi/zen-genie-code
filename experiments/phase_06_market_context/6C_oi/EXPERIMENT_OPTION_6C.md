# EXPERIMENT OPTION 6C — tek önerilen hat (lock DEĞİL)

## 6C-1 (önerilen): Vision 5m OI + BASE/NEW/FULL ablation
- **Veri:** S1, 2020-09-10 civarı → 2023-06-30 (run-time teyitli).
- **Kollar:** BASE E032-verbatim / NEW (OI-türevleri, ~4-5 feature: değişim,
  z-score, price-OI divergence yönü, seviye; exact formüller M.20 lock'ta) /
  FULL (B3 + NEW). Model M2 frozen, L1/H12, 5m grid — 6A/6B makinesi birebir.
- **Kayıp yönetimi:** FULL train satırları OI-yok aralıkta düşer (~2020 başı +
  z-warmup); VAL tam. Splitler değişmez; kayıp raporlanır.
- **Karar:** FULL gate zinciri + ΔCI95 alt > 0 (6A/6B ile aynı kural önerilir).
- **Bütçe:** indirme MB'lar, fitler <3 CPU-saat.

## 6C-2 (koşullu fallback): ücretli intraday
Yalnızca S1 run-time teyidi çökerse; S5→S4 sırası, proof-of-coverage + lisans +
bütçe M.20 kararı şart. Ayrı lock gerekir.

## Açılmayacak
- Daily-only tasarım (B hükmü).
- Oran-sütunlarına dayalı tasarım (gap politikasız).
- 6A/6B sonuçlarına göre feature ayarlama (kontaminasyon yasağı 6B §25 emsali).

## M.20'ye açık noktalar
1. OI feature exact seti + z-lookback'ler (öneri §6C-1 yönleri).
2. Geceyarısı dedup kuralının kilit ifadesi.
3. Train-kayıp toleransı (satır sayısı eşiği; ör. FULL train ≥200k bar şartı?).
4. Ücretli fallback bütçesi (evet/hayır).
