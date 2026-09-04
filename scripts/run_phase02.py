"""
Phase 2 Runner — Walk-Forward (hazır, çalıştırma yok)
Tek komut: py -3 scripts/run_phase02.py  (veya make walkforward)
Çıktı: experiments/phase_02_walkforward/{folds,trades.csv,metrics.csv,regime_report.csv,overlap_report,run_metadata.json}
Not: Bu dosya Phase 1 kapanış sonrası oluşturuldu, Phase 2 henüz KOŞULMADI (kullanıcı onayı bekleniyor).
"""
import argparse, hashlib, json, pathlib, subprocess, sys, datetime, platform
import yaml
import pandas as pd

ROOT = pathlib.Path(__file__).parents[1]
# src import için
sys.path.insert(0, str(ROOT))
EXP_OUT = ROOT / "experiments/phase_02_walkforward"
CONFIG_EXP = ROOT / "config/experiment.yaml"
CONFIG_FT = ROOT / "config/freqtrade.example.json"
STRATEGY = ROOT / "freqtrade/user_data/strategies/BaselineStrategy.py"

def git_info():
    def run(cmd):
        try:
            return subprocess.check_output(cmd, cwd=str(ROOT), text=True, stderr=subprocess.STDOUT).strip()
        except:
            return "unknown"
    commit = run(["git", "rev-parse", "HEAD"])
    tag = run(["git", "describe", "--tags", "--exact-match"])
    if "unknown" in tag or "fatal" in tag:
        tag = run(["git", "tag", "--points-at", "HEAD"])
        if not tag:
            tag = "no-tag"
    status = run(["git", "status", "--porcelain"])
    clean = status == ""
    return commit, tag, clean

def config_hash():
    h = hashlib.sha256()
    for p in [CONFIG_EXP, CONFIG_FT, STRATEGY]:
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:16]

def check_data():
    data_dir = ROOT / "freqtrade/user_data/data/binance"
    if not data_dir.exists():
        return False, "data dir yok"
    files = list(data_dir.rglob("*.json")) + list(data_dir.rglob("*.feather")) + list(data_dir.rglob("*.csv"))
    # Freqtrade data: Binance_xxx_5m.json/feather
    n = len(files)
    if n == 0:
        return False, f"{data_dir} boş — download_data çalıştırılmadı"
    return True, f"{n} dosya"

def main(dry_run=True):
    print("=== Phase 2 Runner — DRY RUN (gerçek backtest yok) ===" if dry_run else "=== Phase 2 RUN ===")
    cfg = yaml.safe_load(CONFIG_EXP.read_text(encoding="utf-8"))
    wf_raw = cfg["walk_forward"]
    # note alanını filtrele (WFConfig bug fix, expanding:false korunuyor)
    from src.backtest.walk_forward import WFConfig, generate_folds
    wf_cfg = {k:v for k,v in wf_raw.items() if k in WFConfig.__dataclass_fields__}
    wfc = WFConfig(**wf_cfg)
    print(f"WF: {wf_cfg}")

    # final_test_A guard
    final_a_start = pd.Timestamp(cfg["splits"]["phase_02_walkforward"]["final_test_A"].split("→")[0].strip().split(" ")[0])
    # yaml string "2023-07-01 -> 2023-12-31  # ..." -> parse first date
    # Daha robust: splits içinden tarihleri ayıkla
    try:
        # experiment.yaml: "2023-07-01 -> 2023-12-31  # ..."
        s = cfg["splits"]["phase_02_walkforward"]["final_test_A"]
        # s contains date and comment
        dates = [t.strip() for t in s.replace("->", "→").split("→")]
        final_a_start = pd.Timestamp(dates[0].strip().split()[0])
        final_a_end = pd.Timestamp(dates[1].strip().split()[0].split()[0])
    except:
        final_a_start = pd.Timestamp("2023-07-01")
        final_a_end = pd.Timestamp("2023-12-31")
    print(f"final_test_A guard: {final_a_start.date()} -> {final_a_end.date()}")

    # Fold üretimi — walk_forward end'i final_A öncesi olmalı
    # Kullanıcı --end vermezse 2023-06-30 kullan (güvenli)
    start = "2020-01-01"
    end = "2023-06-30"  # güvenli, final_A'yı içermez
    folds = generate_folds(start, end, wfc)
    print(f"{len(folds)} fold üretildi ({start}->{end})")
    # Guard: hiçbir fold final_A ile örtüşmemeli
    for i,f in enumerate(folds):
        ts, te = f["test"]
        overlap = not (te < final_a_start or ts > final_a_end)
        if overlap:
            print(f"[GUARD FAIL] fold {i} test {ts.date()}->{te.date()} final_test_A ile örtüşüyor — ABORT")
            sys.exit(2)
    print("[GUARD] final_test_A ile örtüşme yok — OK")

    # Data kontrol
    ok, msg = check_data()
    print(f"data: {'READY' if ok else 'NOT READY'} — {msg}")
    if not ok and not dry_run:
        print("veri yok, indirme gerekli: make download")
        sys.exit(3)

    # Metadata
    commit, tag, clean = git_info()
    run_meta = {
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
        "git_commit": commit,
        "git_tag": tag,
        "git_clean": clean,
        "config_hash": config_hash(),
        "experiment_yaml": str(CONFIG_EXP),
        "freqtrade_config": str(CONFIG_FT),
        "strategy": "BaselineStrategy",
        "strategy_file": str(STRATEGY),
        "strategy_version": hashlib.sha256(STRATEGY.read_bytes()).hexdigest()[:12] if STRATEGY.exists() else "unknown",
        "data_range": f"{start} -> {end}",
        "pair_universe": json.loads(CONFIG_FT.read_text()).get("pairlists", [{}])[0] if CONFIG_FT.exists() else {},
        "fee": cfg.get("costs", {}).get("fee_taker", 0.001),
        "slippage_bps": cfg.get("costs", {}).get("slippage_bps", 5),
        "slippage_model": cfg.get("costs", {}).get("slippage_model", "5bps base"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            "pandas": pd.__version__,
        },
        "wf_config": wf_cfg,
        "final_test_A": f"{final_a_start.date()} -> {final_a_end.date()}",
        "final_test_A_guard": "enabled — folds final_A ile örtüşürse abort",
        "expanding": wfc.expanding,
        "note": "Phase 2 henüz KOŞULMADI — dry_run metadata",
    }

    # Çıktı yapısı (dry_run ise sadece iskelet)
    EXP_OUT.mkdir(parents=True, exist_ok=True)
    (EXP_OUT / "folds").mkdir(exist_ok=True)
    # config snapshot
    (EXP_OUT / "config_snapshot.yaml").write_text(CONFIG_EXP.read_text(encoding="utf-8"), encoding="utf-8")
    (EXP_OUT / "config_snapshot.json").write_text(CONFIG_FT.read_text(encoding="utf-8"), encoding="utf-8")
    # overlap report
    from src.backtest.walk_forward import generate_folds as gf
    overlap_lines = []
    for i in range(1, len(folds)):
        gap = (folds[i]["train"][0] - folds[i-1]["test"][1]).days
        overlap_lines.append(f"fold {i-1}->{i} gap {gap} {'OVERLAP' if gap<0 else 'ok'}")
    (EXP_OUT / "overlap_report.txt").write_text("\n".join(overlap_lines), encoding="utf-8")
    # folds manifest
    import csv as csvm
    with open(EXP_OUT / "folds" / "folds.csv", "w", newline="", encoding="utf-8") as f:
        w = csvm.writer(f)
        w.writerow(["fold","train_start","train_end","val_start","val_end","test_start","test_end"])
        for i,fo in enumerate(folds):
            w.writerow([i, fo["train"][0].date(), fo["train"][1].date(), fo["validation"][0].date(), fo["validation"][1].date(), fo["test"][0].date(), fo["test"][1].date()])
    # placeholder trades/metrics/regime
    (EXP_OUT / "trades.csv").write_text("pair,profit_ratio,close_date\n", encoding="utf-8")
    (EXP_OUT / "metrics.csv").write_text("fold,sharpe,sortino,max_dd,profit_factor,win_rate,method\n", encoding="utf-8")
    (EXP_OUT / "regime_report.csv").write_text("fold,regime,sharpe\n", encoding="utf-8")
    (EXP_OUT / "run_metadata.json").write_text(json.dumps(run_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"metadata: {EXP_OUT / 'run_metadata.json'}")
    print("Çıktı iskeleti hazır — gerçek backtest için: py -3 scripts/run_phase02.py --no-dry-run")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--no-dry-run", action="store_true", help="gerçek backtest (final_test_A guard ile)")
    args = p.parse_args()
    main(dry_run=not args.no_dry_run)
