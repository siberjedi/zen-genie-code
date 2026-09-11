# PHASE 13 — GATE / PRECONDITION CHECK (scout; indirme/fit/backtest YOK)

**Kapsam:** 4 kapının kanıt-toplanması. Araştırma-verisi indirilmedi, feature
yok, model yok, holdout kapalı (B/C'ye dokunulmadı), threshold denenmedi,
hipotez eklenmedi.

## 1. GATE 1 — Tam tarihçe / veri tedariği: CONDITIONAL

| Vendor | Ürün/tier | 2020+ arşiv kanıtı | API/export | Ücret | Kredi/ek | Binance tek-venue |
|--------|-----------|-------------------|------------|-------|----------|-------------------|
| Glassnode | Professional | "Up to 15+ Years" (dokümante) | API + kredi-metre | $999/ay + yayınlanmamış kredi ücreti | Evet (BTC/call=1) | Katalogda (doğrulanacak) |
| CoinGlass/CryptoQuant | Professional/Premium | "as far back as we track" (belirsiz) | Token + satır-metreli kredi | Plan + top-up | `exchange=binance` filtresi dokümante |
| CoinMetrics | PRO (iletişim-satış) | FlowNetBNBUSD metriği dokümante; min_time doğrulanamadı (catalog-all anahtarsız 400) | API key gerekli | Yayınlanmamış | FlowNetBNB* mevcut |

Gerçek retrievability kanıtı (authenticated coverage probe: earliest-timestamp
+ bir örnek-hafta çekimi) tedarik gerektirir → M.20 harcama kararı olmadan
kapanmaz. Doküman-kanıt var, canlı-kanıt yok. **CONDITIONAL.**

## 2. GATE 2 — Point-in-Time / revision riski: FAIL

- **CoinGlass: belgeli NON-PIT.** "Historical data may change as new exchange
  wallets are discovered" — geriye-dönük revizyon, look-ahead kirliliği.
- **Glassnode PIT ürünü VAR ama pencere-dışı:** PIT takibi en erken 2024'te
  başladı (Tem-2025 genişlemesi); "PIT history only exists from the moment
  tracking begins" → **2020–2023 için PIT-doğru tarihçe MEVCUT DEĞİL**,
  hiçbir katmanda satın alınamaz.
- **Revizyon-duyarsız tasarım (Seçenek A):** YOK. Yön+büyüklük ikisi de
  re-clustering ile kayar; lag-tamponları yeniden-sınıflandırmayı düzeltmez;
  tek-venue filtresi azaltır, ortadan kaldırmaz.
- **PIT-garantili alternatif (Seçenek B):** 2020–2023 için MEVCUT DEĞİL.
- **Belirleyici kanıt:** Glassnode'un kendi araştırması mutable-vs-PIT
  ıraksamasının MATERYAL olduğunu gösteriyor ("cumulative performance
  diverges meaningfully") — tam bizim kullanım senaryomuz.
- "Muhtemelen değişmez" kabul edilmedi. **FAIL.**

## 3. GATE 3 — Preregistered deney tasarımı: PASS (kilitlenebilir; hükümsüz)

3 metrik (Binance netflow, stablecoin-supply-ratio, SOPR-bandı) + mekanizma
notları + lag'ler (günlük bar, trailing-7d z) + L1/H288 + C=0.003 + M2 frozen +
eşik-siz (L1) + FDR-3 (metrik-başına kol, BH) + tam gate zinciri — tamamı
kağıt-üzerinde kilitlenebilir. Veri hükümsüz kıldığı için tasarım arşiv
niteliğindedir. **PASS (tasarım olarak; deneye geçirmez).**

## 4. GATE 4 — Tek venue / Binance: FAIL

- Binance filtresi MEVCUT (CoinMetrics FlowNetBNBUSD dokümante; CoinGlass
  `exchange=binance` dokümante) → mekanizma PASS.
- 2020+ kapsama: anahtarsız doğrulanamadı → tek başına CONDITIONAL olurdu.
- PIT: Gate-2 başarısızlığı devralınır (Binance etiketleri de revize edilir).
- Deterministik hizalama: UTC günlük/saatlik gridler → PASS.
- **Toplam: FAIL (PIT gerekçesiyle).**

## 5. Kanıt / kaynak

Glassnode pricing + PIT docs + research (mutability, Mar-2023; PIT-gereklilik,
Mar-2026; Snowflake PIT, Haz-2026); CoinGlass docs (non-PIT beyanı, kredi
metresi, finalizasyon +1h); CoinMetrics docs + canlı community-probu
(AdrActCnt OK / FlowInExch[USD] 400 → sette yok); repo-taraması (on-chain
sıfır). Araştırma-verisi indirilmedi.

## 6. Riskler

Ücret-opaklığı (yayınlanmamış kredi fiyatları) · revizyon-kaçağı (belgeli) ·
snooping (100+ metrik → prereg ≤3 şartı saklı) · survivorship (FTX-çıkışı
dahil kompozisyon kayması) · ücretsiz-katman gecikmesi · güç (günlük
ölçekte bile balina-olay seyrekliği).

## 7. Genel karar: STOP

Kritik gate (G2) FAIL → kural gereği deney açılmaz. G1/G4'teki CONDITIONAL'lar
hükümsüzdür (PIT olmadan tedarik anlamsız).

## 8. M.20 lock tasarımı: YOK (kilitlenecek tasarım üretilmedi)

Phase-13 scout §3'teki taslak, arşiv-nitelikte saklıdır; revizyonu için önce
PIT-doğru 2020–2023 verisinin VARLIĞI gerekir (şu an yok). Supply-bazlı
(PIT-sağlam) metriklerle daraltılmış ayrı bir soru, istenirse taze scout ister.

## 9. Neden kapatıldı

2020–2023 penceresi için PIT-doğru exchange-flow tarihçesi hiçbir satıcıda
mevcut değil; revizyon-duyarsız tasarım yok; ücretsiz katmanlar akış metriği
vermiriyor. Test edilebilirlik koşulu sağlanamadı.

---
*İndirme/fit/backtest/holdout/threshold/hypothesis YOK. Commit yok.*
