# PHASE 17 — HOLDOUT PLAN (FINAL_B / FINAL_C assignment protokolü)

**Statü:** PROTOCOL. Bu fazda holdout verisi indirilmedi/okunmadı/tüketilmedi.
Assignment, M.20 otoritesinin ayrı onayıyla yürürlüğe girer.

## 1. Mevcut durum (kayıt)

| Pencere | Aralık | Statü |
|---------|--------|-------|
| TRAIN | 2020-01-01 → 2022-12-31 | mevcut veri, kilitli |
| VAL | 2023-01-01 → 2023-06-30 | mevcut veri, kilitli |
| FINAL_A | 2023-07-01 → 2023-12-31 | **CONSUMED (P3)** |
| FINAL_B | 2024-01-01 → 2024-06-30 | **UNTOUCHED** |
| FINAL_C | 2024-07-01 → 2024-12-31 | **UNTOUCHED** |
| FINAL_P5 | 2025-01-01 → 2025-06-30 | **CONSUMED (M.20-confirm)** |

Sabitler: `src/freqai/p5_splits.py` (kilitli; FINAL_B/C UNTOUCHED).
Registry: `experiments/phase_05_ml/holdout/HOLDOUT_REGISTRY.md` (statüler
değiştirilmedi).

## 2. Önerilen atama

- **Birincil: FINAL_B (2024H1)** — VAL'den (2023H1) hemen sonraki altı ay;
  trend/vol rejimi 2024H1, eğitim dönemine (2020–2022) en yakın iki rezervden
  biridir. Beklenen: 2024H1 trend-li bir dönem (spot rally) — crash-avoidance
  mekanizması için en az olumsuz olmayan test ortamı.
- **Yedek: FINAL_C (2024H2)** — yalnızca FINAL_B veri bütünlüğü bozulursa
  (hash uyuşmazlığı / eksik veri) kullanılır; bu durum önceden M.20'ye
  raporlanır.
- İkisi birlikte test EDİLMEZ (tek değerlendirme ilkesi, P5 emsali).

## 3. Download-then-lock akışı (P5 emsali)

1. **M.20 assignment kararı:** FINAL_B'nin Phase 17'ye atanması, M.20
   otoritesinin yazılı onayıyla kayda geçer (registry'ye yeni satır).
2. **Download:** Binance kline verisi (5m, BTCUSDT, 2024-01-01 → 2024-06-30
   23:55 UTC) indirilir; URL + dosya sayısı + satır sayısı manifest'e yazılır
   (P5 manifest emsali: `manifest_2025H1.json`).
3. **Lock:** indirilen feather'ın SHA256'sı hesaplanır ve **pin** olarak
   `p5_splits`-tarzı sabit + registry'ye yazılır. Pinden sonra dosya
   değişmez; her okuma `verify_holdout_hash` ile pin'e vurulur.
4. **Koruma:** `check_not_in_protected` + pencere dışı veri kontrolü
   (FINAL_B aralığı dışı satır = ABORT).
5. **Tek değerlendirme:** Phase 18 koşumu, atanan holdout'ta BİR kez çalışır.
6. **Tüketim kaydı:** sonuç + karar registry'ye yazılır; statü
   UNTOUCHED → CONSUMED.

## 4. Guard zinciri (koşum öncesi zorunlu)

- [ ] M.20 assignment onayı (kayıtlı)
- [ ] manifest + sha256 pin mevcut
- [ ] `verify_holdout_hash()` PASS
- [ ] FINAL_B aralığı dışında veri yok (window assert)
- [ ] Preregistration grid'i (PHASE_17_PREREGISTRATION.md §3) değişmedi
- [ ] Kod review + freeze (sonuç öncesi)
- [ ] Registry'de UNTOUCHED → CONSUMED satırı, tek seferlik

## 5. Kullanılmayacaklar (kesin)

- FINAL_A / FINAL_P5: CONSUMED — erişim yok.
- FINAL_C: yedek — FINAL_B sağlamsa dokunulmaz.
- TRAIN/VAL: yalnızca selection/stabilite; holdout'a sızma yok.

## 6. Sonuç kabulü

- Karar yalnızca C=0.003 OOS metrics + PREREGISTRATION §12 gate'leri
  üzerinden.
- Holdout sonucu ne olursa olsun: sonuç, gate tablosu ve tüketim kaydı
  registry + faz raporuna işlenir; "tek şans" ilkesi gereği retry yok.

VERDICT: HOLDOUT PLAN READY — assignment M.20 onayı bekliyor.