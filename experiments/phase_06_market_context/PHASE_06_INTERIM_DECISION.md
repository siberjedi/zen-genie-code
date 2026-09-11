# PHASE 6 — INTERIM DECISION REVIEW (review only; M.20 değişikliği yok)

**Kapsam:** 6A/6B/6C sonuçları + scout kaynakları üzerinden devam/kapanış
kararı analizi. İndirme/fit/backtest/holdout/feature/M.20 değişikliği YOK.

## Kanıt özeti (VAL, 5m/H12/L1/M2/42)

| Deney | FULL−BASE ΔPSS | CI95 | NEW AUC | FULL AUC | Gate |
|-------|----------------|------|---------|----------|------|
| 6A cross-asset | −0.000038 | [−0.000103, +0.000029] | 0.6206 | 0.6800 | a✗ b✓ c✗ d✗ |
| 6B funding | −0.000037 | [−0.000107, +0.000033] | 0.5362 | 0.6798 | a✗ b✓ c✗ d✗ |
| 6C OI (revize koşu) | −0.000016 | [−0.000103, +0.000069] | 0.6004 | 0.6800 | a✗ b✓ c✗ d✗ |

BASE (E032-verbatim) üç koşuda bit-tutarlı: PSS −0.002117, edge −0.706,
AUC ~0.68, top-decile gross mean ~+0.0009.

## 1. Kanıt ne söylüyor?

Üç farklı bilgi ailesi (kesitsel breadth, pozisyon-maliyeti, pozisyon-stoku)
sıfır-civarında Δ üretti; CI'lar ekonomik anlamlı etkiyi (gerekli ~+0.003+)
DIŞLIYOR — bunlar güçsüz-nötr değil, **bilgilendirici null**'lardır.
Aynı anda FULL kollar b-desteğini (AUC~0.68) korudu: sinyal çıkarımı çalışıyor,
ekonomik dönüşüm çalışmıyor.

## 2. Bağımsız null'lar mı, ortak yapısal problem mi?

İKİSİ BİRDEN (rakip değil, tamamlayıcı): her deney kendi null'unu güvenilir
şekilde kurdu (dar CI); desen ise ortak — 1h forward brüt getiri zarfı
(~±10bp) locked cost'un (30bp) çok altında. Edge/cost ≥1.2 için top-decile
gerekli ~+0.0066 (mevcut ~+0.0009'un ~7.5 katı). Bağlayıcı kısıt ENFORMATİF
değil EKONOMİK: maliyet duvarı + 1h ufuk. Yeni feature bu aritmetiği ancak
niteliksel farklı getiri rejimi açarak aşar.

## 3. Yeni market-context kaynağının şansı için gerekçe miktarı

ZAYIF. Üç çeşitli aile elendi (ekonomik ölçekte, güçlü). Kalan adayın, fiyatı +
konumlanmayı aşan, 1h'de yaşayan VE 7.5× sıçrama üreten bilgi taşıdığına dair
önsel gerekçe gerekir — mevcut adayların hiçbirinde bu profil yok (§4–6).

## 4. Order book: yeni bilgi mi, aynı problemin tekrarı mı?

Quote bilgisi (imbalance/spread) teknik olarak yenidir. AMA: (i) mikro-yapı
sinyali saniye-dakikada ölür; kendi ufuk-kanıtımız (h=3 PSS negatif) 15-dk
öngörünün bile yokluğunu gösteriyor — 1h hedefle uyumsuz; (ii) TB-maliyet +
ücretli erişim; (iii) aynı ekonomik problemi (30bp altında 1h getiri) daha
hızlı-ölen sinyalle re-test riski YÜKSEK. Hüküm: tick-ufkunda bilgilendirici,
**kilitli çerçevede önceli düşük**.

## 5. Liquidations

Burst-seyrek yapı 5m gridde çoğunlukla sıfır → efektif düşük-frekans sinyal;
ücretli üçüncü-parti (metodoloji/revizyon riski, backfill satın-almadan
kanıtlanamaz); aynı türev-konumlanma ailesinden funding/OI null'ları emsal.
Hüküm: incremental önceli DÜŞÜK + erişim-belirsiz.

## 6. News/X neden düşük öncelikli?

Arşiv YOK (CryptoPanic 1-ay/1-yıl cursor-only; X pay-per-use + silinme +
retrospektif-indeks kararsızlığı); publication-vs-decision zamanlaması tarihsel
olarak kanıtlanamaz; sentiment ground-truth yok; 5m alfa yarı-ömrü şüpheli;
X ayrıca görev-emriyle HOLD. Doğru şekilde düşük öncelikli.

## 7–8. 6D haklı çıkarılabilir mi? (6 kriter testi)

| Aday | Bağımsız kaynak | Mekanizma | Maliyet-uyumu | Leakage-kontrol | Erişim | Prereg kriter | Hüküm |
|------|----------------|-----------|---------------|-----------------|--------|---------------|-------|
| Order book | kısmen | zayıf (ufuk) | HAYIR | evet | ücretli/ağır | evet | KALIR |
| Liquidations | kısmen | zayıf | şüpheli | koşullu | belirsiz | evet | KALIR |
| News/X | evet | belirsiz | şüpheli | HAYIR (arşiv) | yok/zor | kısmen | KALIR |

Hiçbir aday 6 kriteri birlikte geçmiyor. "Henüz denemedik" gelten sayılmaz.
**6D haklı ÇIKARILAMAZ.**

## 9. Karar

**A) PHASE 6 CLOSED — MOVE ON.**

Gerekçe: ucuz/zaman-damgalı-tutarlı/tam-kapsamlı market-context uzayı tükendi
(üç aile ekonomik ölçekte elendi); kalanlar pahalı + ufuk-uyumsuz +
arşiv-şüpheli; ortak yapısal bulgu (maliyet duvarı) yeni feature ile aşılamaz
nitelikte. Kapanış, üç bilgilendirici null + korunmuş holdout'lar + tekrar
üretilebilir artefaktlar bırakır.

Kapanış şartları (öneri, M.20/user onayı ayrı): yeni 6X deneyi açılmayacak;
P5/B/C/A kilitli kalır; Phase 6 artefaktları dondurulur; sonraki faz kararı
ayrı alınır (bu review faz tasarlamaz).

**READY FOR USER DECISION**
