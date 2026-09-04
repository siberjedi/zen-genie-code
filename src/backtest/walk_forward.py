"""
Faz 2 — Walk-Forward motoru (Freqtrade backtesting sarmalayıcısı).
Foldlar bağımsız sayılmaz — overlap/otokorelasyon raporlanır.
"""
from dataclasses import dataclass
from datetime import timedelta
import pandas as pd
import subprocess, shlex, json, pathlib, itertools

@dataclass
class WFConfig:
    train_days: int = 365
    validation_days: int = 90
    test_days: int = 90
    step_days: int = 90
    expanding: bool = False

def generate_folds(start: str, end: str, cfg: WFConfig):
    cur = pd.Timestamp(start)
    end = pd.Timestamp(end)
    folds=[]
    while True:
        train_start = cur if not cfg.expanding else pd.Timestamp(start)
        train_end = cur + timedelta(days=cfg.train_days)
        val_end = train_end + timedelta(days=cfg.validation_days)
        test_end = val_end + timedelta(days=cfg.test_days)
        if test_end > end: break
        folds.append(dict(train=(train_start, train_end), validation=(train_end, val_end), test=(val_end, test_end)))
        cur += timedelta(days=cfg.step_days)
    return folds

def run_backtest(strategy: str, timerange: str, config="config/freqtrade.example.json"):
    """Freqtrade backtest'i çağırır, JSON çıktısını döndürür."""
    cmd = f"freqtrade backtesting --config {config} --strategy {strategy} --timerange {timerange} --export trades"
    print(f"[wf] {cmd}")
    subprocess.run(shlex.split(cmd), check=False)

def overlap_report(folds):
    """Fold örtüşmesini raporla — bağımsızlık uyarısı."""
    for i in range(1,len(folds)):
        prev_test = folds[i-1]["test"][1]
        curr_train = folds[i]["train"][0]
        gap = (curr_train - prev_test).days
        print(f"fold {i-1}→{i} gap={gap} gün {'⚠️ overlap' if gap<0 else 'ok'}")

if __name__ == "__main__":
    import argparse, yaml
    p=argparse.ArgumentParser()
    p.add_argument("--config", default="config/experiment.yaml")
    p.add_argument("--strategy", default="BaselineStrategy")
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default="2023-12-31")
    args=p.parse_args()
    cfg=yaml.safe_load(open(args.config))
    wf=WFConfig(**cfg["walk_forward"])
    folds=generate_folds(args.start, args.end, wf)
    print(f"{len(folds)} fold üretildi")
    overlap_report(folds)
    for f in folds:
        tr = f"{f['test'][0].strftime('%Y%m%d')}-{f['test'][1].strftime('%Y%m%d')}"
        run_backtest(args.strategy, tr, "config/freqtrade.example.json")
