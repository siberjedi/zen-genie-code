"""
Faz 1/2 — Binance verisini Freqtrade formatında indirir.
Kullanım: python scripts/download_data.py --pairs BTC/USDT ETH/USDT --timeframe 5m --days 400
Freqtrade yoksa ccxt fallback kullanır.
"""
import argparse, subprocess, sys, shlex

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+", default=["BTC/USDT"])
    p.add_argument("--timeframe", default="5m")
    p.add_argument("--days", type=int, default=400)
    p.add_argument("--exchange", default="binance")
    args = p.parse_args()

    pairs = " ".join(args.pairs)
    # Freqtrade native downloader
    cmd = f"freqtrade download-data --exchange {args.exchange} --pairs {pairs} --timeframes {args.timeframe} --days {args.days} --config config/freqtrade.example.json"
    print(f"[download] {cmd}")
    try:
        subprocess.run(shlex.split(cmd), check=True)
    except FileNotFoundError:
        print("[download] freqtrade bulunamadı — pip install freqtrade")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"[download] hata: {e}")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
