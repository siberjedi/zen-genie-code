# PHASE 11 — RESULTS (frozen carry, 12 CM quarterly)

**Karar:** FAIL
- net carry (ort/cevrek, oran): +0.003698 | toplam BTC: -6.1468 (USD memo ~$-192,492)
- program toplami (konversiyonlu): -6.3187 BTC
- edge: 10.521 | Sharpe_ann: 0.158 CI=[-1.747,1.152]
- MaxDD: 0.0882 | win-rate: 0.417 | turnover/yr: 3.4
- likide: yok
- p=0.3945 q=0.3945 | d=+0.079 power(d=0.8)=0.829
- gate'ler: {'net_pos': True, 'edge': True, 'sharpe_ci': False, 'maxdd': True, 'd_power': False, 'fdr': False, 'chain': False}
  - BTCUSD_200925: net=-1.5695BTC liq=False giris=+71bp
  - BTCUSD_201225: net=-4.9141BTC liq=False giris=+160bp
  - BTCUSD_210326: net=-1.4420BTC liq=False giris=+376bp
  - BTCUSD_210625: net=+1.3583BTC liq=False giris=+823bp
  - BTCUSD_210924: net=-0.6066BTC liq=False giris=+111bp
  - BTCUSD_211231: net=-0.1426BTC liq=False giris=+165bp
  - BTCUSD_220325: net=+0.1573BTC liq=False giris=+183bp
  - BTCUSD_220624: net=+2.5932BTC liq=False giris=+110bp
  - BTCUSD_220930: net=+0.1757BTC liq=False giris=+14bp
  - BTCUSD_221230: net=+0.9075BTC liq=False giris=+36bp
  - BTCUSD_230331: net=-2.4656BTC liq=False giris=+18bp
  - BTCUSD_230630: net=-0.1984BTC liq=False giris=+133bp

**PHASE 11 CLOSED**

Anomali/notlar (sonuç-değiştirmez, kayda geçirildi):
- Q2-2023 çıkışı settlement'ten ~8h erken (spot grid VAL_END=2023-06-30 00:00'da
  biter; kilitli loader aşılmadı — korumalı/pencere-dışı veri YOK).
- v1 implementasyonda karma-birim muhasebe hatası YAKALANDI (teminat FX'i
  P&L'e sızıyordu, ~+$1.18M artefakt); BTC-numeraire'a kilit-tanımıyla
  düzeltildi, self-check kimliği 8.68e-15 ile geçti; yukarıdaki sayılar
  düzeltilmiş makineden + bağımsız teyitlidir.