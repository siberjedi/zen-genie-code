# PHASE M.20 — LOWER-COST EXECUTION REPLICATION (recomputasyon; fit YOK)

**Kapsam:** Phase 7 H48 sinyalinin USDⓈ-M perps-taker rejiminde bağımsız
replikasyonu. Model fiti YOK (sklearn çağrılmadı); kilitli artefaktlardan
(oof7 + funding parquet) deterministik recomputasyon. Holdout kapalı.

## 1. Execution regime (dışsal doğrulama)

- Venue: Binance USDⓈ-M BTCUSDT perpetual. Regular-user taker fee:
  dönem-belgeli **%0.04** (2023 kaynaklı tarife; güncel doküman %0.05 —
  karıştırılmadı; %0.05 duyarlılık olarak ayrıca raporlandı, karar girdisi
  DEĞİL). Round-trip commission = 2 × 0.0004 = **0.0008**. BNB indirimi
  varsayılmadı (operasyonel ek-varsayım olurdu). Maker fee kullanılmadı
  (fill/adverse-selection modellenmeden iyimser kalır — Phase 8 §5).
- Etiket: **historical-regime replication** (dönem tarifesi belgelendiği için;
  current-regime değil).

## 2. Signal (verbatim, dondurulmuş)

B3 / L1@H48 / M2 / seed42 / frozen TRAIN-q90 — Phase 7 artefaktları aynen
kullanıldı (647 event, skorlar ve Y_i değişmedi). Threshold/horizon/model/
feature/seed'e DOKUNULMADI.

## 3. Cost (frozen formül)

```
C_M20 = commission + spread + slippage + funding
      = 0.0008     + 0.0010 (Phase 8: 5bps/side)
        + funding_i (per-event, deterministik)
```
- `funding_i` = LONG için `(t_i, t_i+48bar]` settlement oranları toplamı
  (6B indirmesi; kapsama assert'li, eksik YOK; keyfi değer YOK).
- Ölçülen: funding ort **+0.0000356** (min −0.000089, maks +0.000458).
- **C_M20 (ortalama toplam) = 0.0018356** (18.36bp). Sabit kısım 0.0018.

## 4. Gates + karşılaştırma tablosu

| Ölçü | Phase 7 (C=0.003) | M.20 (C_M20) |
|------|-------------------|--------------|
| gross return (event mean) | +0.005771 | +0.005771 (aynı eventler) |
| total execution cost | 0.003000 | 0.001836 (0.0008+0.0010+0.000036) |
| net return | +0.002771 | **+0.003935** |
| PSS (pooled) | −0.000659 | +0.000505 |
| edge/cost (pooled) | −0.220 | 0.275 (< 1.2 ✗) |
| AUC / rankIC / tau | 0.6019 / 0.0544 / 0.4222 | aynı (skor değişmedi) |
| event count / rate | 647 / 0.0125 | aynı |
| MaxDD | 0.963 | 0.9195 (> 0.20 ✗) |
| theta48 | +5.4690 | +7.7657 |
| bootstrap CI95 | [3.58, 8.89] | [5.91, 10.83] (alt > 0 ✓) |
| power / Cohen d | 1.00 / +0.179 | aynı (< 0.30 ✗) |
| q (pooled t-test) | 1.0 | 0.0054 (✓) |

- Phase 7 gross edge: **+0.005771** (event çerçevesi; pooled-decile: +0.002341).
- Phase 7 C=0.003 net edge: **+0.002771** (event) / −0.000659 (pooled PSS).
- M.20 gross edge: **+0.005771** (aynı — tutarlılık kanıtı).
- M.20 net edge: **+0.003935**.
- C_break_even (event): **0.005771** (57.7bp).
- C_M20: **0.0018356** (18.36bp).
- Safety margin: **+0.003935** (+39.4bp).
- %0.05-duyarlılık (etiketli, karar-dışı): net +0.003735 → kategori değişmez.

## 4b. Zorunlu yan-yana karşılaştırma (event çerçevesi; pooled parantezde)

- Phase 7 gross edge: **+0.005771** (+0.2341% pooled-decile)
- Phase 7 C=0.003 net edge: **+0.002771** (−0.000659 pooled-PSS)
- M.20 gross edge: **+0.005771** (aynı eventler — tutarlılık)
- M.20 net edge: **+0.003935**
- C_break_even: **0.005771** (57.71bp)
- C_M20: **0.0018356** (18.36bp = 0.0008 + 0.0010 + 0.0000356)
- Safety margin = C_break_even − C_M20: **+0.003935** (+39.35bp)

## 5. Comparison — karar

Net edge (+0.003935) > 0 AMA resmi gate'ler eksik (edge 0.275<1.2,
d 0.179<0.30, MaxDD 0.92>0.20) → **B) WEAK POSITIVE — NEEDS INDEPENDENT
CONFIRMATION.** Bu bir rescue DEĞİLDİR (maliyet dışsal-gerekçeli; eşikler
oynatılmadı; event seti dondurulmuş).

## 6. Leakage / holdout

P5/B/C/A kapalı; fit yok; tuning yok. Sonuç final claim DEĞİL —
**needs independent confirmation** (ayrı protected test + ayrı M.20 olmadan
ilerleme yok).

## 7. No-rescue-tuning beyanı

Threshold/horizon/model/feature/seed/cost/spread/slippage/funding optimize
EDİLMEDİ (tamamı frozen veya dışsal-belgeli). %0.05 varyantı duyarlılıktır,
seçim değildir.

## 9. ABSOLUTE RULE

**Phase 7 FAIL remains valid under C=0.003.**
