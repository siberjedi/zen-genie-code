# SETUP — Zen-Genie araştırma çekirdeği

## Gereklilikler
- Python 3.11+ (3.12 önerilir)
- `TA-Lib`: sistem kütüphanesi gerekir (Windows'ta önceden derlenmiş tekerlek/conda önerilir)
- freqtrade bu pakette kütüphane olarak kullanılmaz; harici araçtır (canlı kurulum bu paketin dışında)

## Kurulum
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma (örnek)
```bat
.venv\Scripts\activate
python scripts/download_data.py --pairs BTC/USDT --timeframe 5m --days 30
python scripts/verify_dryrun.py
```
- `dashboard/`, `config/`, `experiments/` bu pakette yoktur (bilerek çıkarıldı).
- Gerçek borsa anahtarı/token dosyası repoda yoktur ve `.gitignore` ile engellidir.
