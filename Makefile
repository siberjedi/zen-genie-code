.PHONY: download verify backtest walkforward paper rl

download:
	python scripts/download_data.py --pairs BTC/USDT ETH/USDT --timeframe 5m --days 400

verify:
	python scripts/verify_dryrun.py

backtest:
	freqtrade backtesting --config config/freqtrade.example.json --strategy BaselineStrategy --timerange 20230101-20230630

walkforward:
	python src/backtest/walk_forward.py --strategy BaselineStrategy --start 2020-01-01 --end 2023-12-31

paper-gap:
	python scripts/paper_vs_backtest.py

rl:
	python src/rl/train.py --algo PPO
