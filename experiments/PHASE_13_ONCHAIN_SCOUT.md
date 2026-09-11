# PHASE 13 — ON-CHAIN FLOW SCOUT (araştırma; kod/backtest YOK)

**Statü:** SCOUT. Feature üretilmedi, backtest yok, holdout kapalı (B/C'ye
dokunulmadı), commit yok. Repo içi on-chain veri/code YOK (taramayla doğrulandı).

## 1. Kaynak envanteri (doğrulanmış)

| Kaynak | Ücretsiz katman | Tam-arşiv erişimi | Çözünürlük | Fiyat |
|--------|-----------------|-------------------|------------|-------|
| Glassnode | YOK (Tem 2026'dan beri) | Professional | 10dk–günlük | Advanced $49–99/ay (4-yıl tarihçe → 2020–21 YOK); Professional $999/ay + yayınlanmamış kredi-metresi |
| CryptoQuant/CoinGlass API | YOK (token = Professional/Premium) | Evet (plan+kredi) | day/hour/block | Kredi-metreli (satır başına); fiyat sayfası opak |
| CoinMetrics Community | EVET (keyless, örn. AdrActCnt 2020+ doğrulandı) | Kısmi | günlük | $0 — AMA exchange-flow metrikleri SETTE YOK (FlowInExch[USD] 400 döndü) |

## 2. Kritik bulgu: PIT revizyonları (leakage)

CoinGlass belgeli: *"endpoint does not support Point-In-Time accuracy...
Historical data may change as new exchange wallets are discovered."*
Cüzdan-kümeleme geriye dönük revize edilir → 2020 değerleri 2024-bilgisiyle
yazılmış olabilir. Bu, backtest'i **yapısal olarak kirletir**; çözümü:
PIT-katmanı beyanı (satıcıdan) veya revizyon-duyarsız tasarım (örn. işaret-
yönlü ham akış + gecikme tamponu) — ikisi de tedarik-öncesi koşul.

## 3. Falsifikasyon protokolü (öneri, kilit DEĞİL)

- Preregister ≤3 metrik (örn. Binance-tek-venue netflow, stablecoin-supply-ratio,
  SOPR-bandı) — mekanizma notuyla; fazlası bahçe-sulama sayılır.
- Ablation: BASE (OHLCV) vs BASE+flow — ΔAUC/ΔPSS/Δedge, FDR-3.
- Lead-lag şartı: flow[t] → return[t+1h..24h]; eşzamanlı korelasyon edge DEĞİL.
- Tek-venue (Binance) seriler tercih edilir (agrega-kompozisyon survivorship'ını,
  örn. FTX-çıkışı, baypas eder).
- Başarısızlıkta hat KAPANIR (retry için taze M.20).

## 4. Edge-büyüklük teorisi

Günlük-ölçek brüt hamleler (50–200bp/gün tipik) 30bp'yi aritmetik olarak
GEÇEBİLİR (5m sinyallerinin aksine) — ama: (a) balina-olay seyrekliği,
(b) ücretsiz katman gecikmesi (günlük +1h finalizasyon), (c) yavaş sinyal =
az bağımsız bahis (güç problemi, carry-vakası emsali). Aktivite-metrikleri
(ücretsiz olanlar) yönsel mekanizmadan yoksun → fiyat-volatilite paketi
riski taşır (Phase-5-redundant şüphesi).

## 5. Riskler

- **Look-ahead:** PIT revizyonları (yukarıda) + blok-onay gecikmesi (günlük+
  ufukta zararsız, intraday'de ölümcül).
- **Survivorship:** borsa-kompozisyon değişimi (FTX vb.); entity-etiketleme
  metodoloji opaklığı.
- **Snooping:** 100+ metrik → prereg ≤3 kuralı zorunlu.
- **Zamanlama:** ücretsiz katman gecikmeleri hızlı ufku öldürür.

## 6. Holdout-güvenli yol

Bu scout: doküman + katalog-probu ile yapıldı (araştırma-verisi indirilmedi).
Herhangi indirme: ayrı M.20 + SADECE TRAIN/VAL pencereleri; B/C kapalı.

## 7. Karar: B) CONDITIONAL GO

Koşullar (hepsi sağlanmadan deney YOK):
1. Ücretli katman tedariki + tam-arşiv (2020+) yazılı teyidi,
2. Satıcıdan PIT/revizyon beyanı (veya revizyon-duyarsız tasarım onayı),
3. Preregistered ≤3 metrik + §3 falsifikasyon protokolü (M.20 lock),
4. Tek-venue (Binance) serilerle kompozisyon riski kapatılmalı.
Koşullar sağlanmazsa otomatik STOP — ek çalışma yok.

---
*Kod değişikliği yok. Yeni faz çalıştırılmadı.*
