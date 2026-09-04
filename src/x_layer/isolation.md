# Faz 6 — X İzolasyon Sözleşmesi (Anayasa Madde 14/15)

- X hesabı trader'ın kritik altyapısından izole: ayrı process/container, ayrı IP/credential.
- Rate limit / challenge / kısıtlama → trader durmaz, sadece X kaynağı devre dışı kalır.
- Browser automation (Playwright/Chromium) — X otomasyon kurallarına uyulur.
- Kill-switch: `X_ENABLED=false` ile tüm X katmanı bypass edilir.
