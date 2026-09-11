# PHASE 18C RESULT — LONG-ONLY TREND + VOL-TARGET WF EXPERIMENT

**Statü:** COMPLETED. Preregistration (Phase 17) + FINAL_B lock (18B) + consumption (18C).
Tek preregistered değerlendirme — retry yok, parametre değişikliği yok.

## Implementation bug kaydı (koşum-1)

İlk koşumda agregasyon 1 bar'a çöktü: timestamp-unit varsayımı
(`datetime64.astype("int64")` resolution-bağımlı — pandas 3.0 us/ms karışıklığı,
proje geçmişinde 4 kez bug üretmiş sınıf). Düzeltme: proje kanonik helper'ı
`src.timeconv.to_ms` (Phase 9F'te kilitlendi) kullanıldı. Koşum-1 sonuçları
GEÇERSİZDİR ve üzerine yazıldı (sessiz değil — bu kayıt). Koşum-2 (aşağıdaki)
geçerli sonuçlardır. Strateji/parametre/grid DEĞİŞMEDİ.

## Data
- TRAIN+VAL: 5m 367.023 satır → 4H 7.656 bar · 1D 1.277 bar (2020-01-01 → 2023-06-30 23:55 UTC)
- FINAL_B: 5m 52.416 → 4H 1.092 · 1D 182 bar (2024-01-01 → 2024-06-30 23:55 UTC)
- FINAL_B hash: `28f88258…9387` — koşum öncesi ve sonrası doğrulandı.

## WF (C=0.003, 7 overlap-sız fold; pozitif fold sayısı)

| Aday | Pozitif fold | VAL Sharpe | VAL net |
|------|-------------|-----------|---------|
| 1. 4H SMA200 (PRIMARY) | 4/7 | 1.977 | +0.337 |
| 2. 4H SMA cross(50,200) | 4/7 | 1.203 | +0.153 |
| 3. 4H Donchian(200) | 5/7 | 1.726 | +0.299 |
| 4. 1D SMA50 | 5/7 | 2.582 | +0.507 |
| 5. 1D SMA100 | 5/7 | 1.412 | +0.270 |
| 6. 1D Donchian(100) | 3/7 | 1.153 | +0.200 |

Not: fold detayları 2020H2'nin (+1.10) toplamı domine ettiğini, 2022H1/H2'nin
iki adayda da NEGATİF olduğunu gösteriyor (crash-avoidance mekanizması 2022
ayılarında net koruma sağlamadı: ör. #1 2022H1 −0.144, 2022H2 −0.135, mdd −0.21).

## FINAL_B sonuçları (C=0.003 primary)

| Aday | Sharpe | Net | MaxDD | Excess vs BH | Turnover | p_boot | Aylık pozitif |
|------|--------|-----|-------|--------------|----------|--------|---------------|
| 1. 4H SMA200 | 1.961 | +0.318 | −0.121 | **−0.147** | 30.6 | 0.234 | 3/6 |
| 2. 4H cross | 2.151 | +0.365 | −0.138 | **−0.101** | 8.4 | 0.211 | 3/6 |
| 3. 4H Donchian | 0.731 | +0.093 | −0.206 | **−0.373** | 7.0 | 0.423 | 2/6 |
| 4. 1D SMA50 | 1.452 | +0.218 | −0.100 | **−0.163** | 4.6 | 0.326 | 3/6 |
| 5. 1D SMA100 | −1.783 | −0.155 | −0.171 | **−0.536** | 6.8 | 0.937 | 0/6 |
| 6. 1D Donchian | 0.000 | 0.000 | 0.000 | **−0.380** | 0.0 | 1.000 | 0/6 |

BH benchmark (2024H1): net +0.465 · MaxDD −0.224 (BTC 2024H1 güçlü bull: +%46,5).

## Gate değerlendirmesi (hepsi aday bazında, C=0.003)

| Gate | #1 | #2 | #3 | #4 | #5 | #6 |
|------|----|----|----|----|----|----|
| G1 Sharpe ≥ 0.80 | ✓ 1.96 | ✓ 2.15 | ✗ 0.73 | ✓ 1.45 | ✗ −1.78 | ✗ 0.00 |
| G2 MaxDD ≤ 0.20 | ✓ | ✓ | ✗ −0.206 | ✓ | ✓ | ✓ (flat) |
| G3 WF ≥ 5/7 | ✗ 4/7 | ✗ 4/7 | ✓ 5/7 | ✓ 5/7 | ✓ 5/7 | ✗ 3/7 |
| G4 excess>0 ve MaxDD<BH | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| G5 aylık ≥4/6 + tek-dönem değil | ✗ 3/6 | ✗ 3/6 | ✗ 2/6 | ✗ 3/6 | ✗ 0/6 | ✗ 0/6 |
| G6 param duyarlılığı (VAL N±20%) | ✓ | — | ✓ | ✓ | ✓ | ~ |
| G7 C=0.005 Sharpe ≥ 0.40 | ✓ 1.75 | ✓ 2.10 | ✓ 0.69 | ✓ 1.42 | ✗ −1.85 | ✗ 0.00 |
| G8 vol-target artifact yok | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**G4 hiçbir adayda geçmedi** (hepsi BH'ye karşı negatif excess — vol-target
exposure ~0.24–0.43 ile bull'da BH'nin altında kaldı). **G5 hiçbir adayda
geçmedi.** FDR (BH, q<0.10): tüm p ≥ 0.211 → tüm q ≥ 0.211 → **hiçbir aday
FDR'den geçmedi**.

## Multiple comparison
- 6 aday, bootstrap p (10k, block: 4H=6, 1D=5, seed 42): 0.234/0.211/0.423/
  0.326/0.937/1.000 → BH-FDR q: hepsi > 0.10 → family-claim DESTEKLENMİYOR.
- Aday seçimi: sabit öncelik sırası; Sharpe sıralamasıyla seçim YAPILMADI.

## Vol-target / benchmark notları
- Exposure ortalamaları: #1 0.41, #2 0.43, #4 0.35, #5 0.24 — kaldıraç YOK
  (max 1.0), vol-target leverage-artifact DEĞİL (G8 ✓, VT'sız karşılaştırma
  JSON'da).
- 2024H1 tek-yönlü bull olduğundan long-only + düşük exposure BH'ye kaybetti;
  stratejilerin pozitif netleri risk-ayarlı anlamlıydı ama benchmark üstünlüğü
  G4 şartını sağlayamadı.

## FINAL_B
- CONSUMED = YES · EVALUATED = YES (registry + PHASE_18C_FINAL_B_CONSUMPTION.md).
- Hash koşum öncesi/sonrası doğrulandı: `28f88258…9387`.

## Falsification sonucu (Phase 17 §14)
1. OOS anlamlılık: bootstrap CI sıfır içeriyor (p ≥ 0.21) — ✗
2. MaxDD: bazı adaylar geçti — ✓/✗ karışık
3. WF stabilitesi: 4H ailesi 4/7 — ✗
4. Benchmark üstünlüğü: hiçbir adayda yok — ✗
5. Edge tek döneme dayanıyor (2020H2 fold'u; aylık dağılım 3/6) — ✗
6. Param duyarlılığı: genel olarak sağlam — ✓
7. Vol-target artifact: yok — ✓
8. Cost erimesi: C=0.005'te 4 aday hâlâ pozitif — ✓

**VERDICT: FAIL / FAMILY CLOSED** — 6/6 aday tüm preregistered gate'leri
geçemedi; G4 (benchmark superiority) ve G5 (monthly stability) her adayda
başarısız; FDR family-claim'i desteklemiyor. Phase 17 H1 reddedildi.
FINAL_B tek değerlendirmeyle tüketildi; FINAL_C dokunulmadı.