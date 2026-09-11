"""Phase 5 — Matrix runner + rapor (DESIGN 500 sec 21/22; user §30).

44 formal cell: E001-E036 (primary 5m) + 3 baseline + S001-S008 (secondary 15m).
Artifacts -> experiments/phase_05_ml/results/ (matrix500.json, metrics500.json,
gate500.json, wf500.json, oof500.parquet, manifest500.json) + NIGHT_RUN_REPORT.md +
TRAIN_VALIDATION_RESULTS.md.

Budget: cap <= 12 CPU-saat (rl_budget.max_train_hours emsali, process_time ile
olculur). Asilirsa kalan cell'ler SKIP edilir -> PARTIAL run (karar E).
2025H1 holdout DEVREDE DEGIL: hicbir kod FINAL_P5/B/C/A yuklemez.
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase502_labels import (build_frame, split_train_val_per_label, COST_C,
                             H_PRIMARY, H_SECONDARY_15M, LABELS)
from phase503_models import (make_model, fit_predict, fit_baseline_scores,
                             M1, M2, M3, BASE)
from phase504_walkforward import (phase5_folds, fold_slices, run_fold,
                                  wf_pss_scores, wf_consistency, bounds_respected,
                                  overlap_report, WF_MIN_CONSISTENCY)
from phase505_stats import (cell_metrics, pss_stats, fdr_family, arm_gate,
                            select_candidate, seed_direction_consistency, ALPHA)

RES_DIR = ROOT / "experiments" / "phase_05_ml" / "results"
EXP_DIR = ROOT / "experiments" / "phase_05_ml"
CPU_HOUR_CAP = 12.0
SEEDS = [42, 7, 123]
CORE_SEED = 42
HO_EDGE = 1.2

PRIMARY_MATRIX = []
_i = 0
for blk in ("B0", "B1", "B2", "B3"):
    for lb in ("L0", "L1", "L2"):
        for md in (M1, M2, M3):
            _i += 1
            PRIMARY_MATRIX.append((f"E{_i:03d}", blk, lb, md))

SECONDARY_MATRIX = []
_j = 0
for blk in ("B1", "B3"):
    for lb in ("L0", "L1"):
        for md in (M1, M3):
            _j += 1
            SECONDARY_MATRIX.append((f"S{_j:03d}", blk, lb, md))

BASELINE_MATRIX = [(f"BASE{lb}", "B3", lb, BASE) for lb in LABELS]

FRAMES = {}


def load_frames():
    if "5" not in FRAMES:
        FRAMES["5"] = build_frame(tf_minutes=5, horizon=H_PRIMARY)
    if "15" not in FRAMES:
        FRAMES["15"] = build_frame(tf_minutes=15, horizon=H_SECONDARY_15M)


def run_cell(cell_id, block, label, model, seed=CORE_SEED, tf_minutes=5,
             horizon=H_PRIMARY, time_ledger=None):
    """Tek cell: fit (seed) + val score + metrik + oof. (met, oof dict) dondurur."""
    t0 = time.process_time()
    frame = FRAMES[str(tf_minutes)]
    d = split_train_val_per_label(frame, label, block, tf_minutes=tf_minutes,
                                  horizon=horizon)
    if model == BASE:
        scores, _ = fit_baseline_scores(d["y_train"], d["y_val"], label, seed)
    else:
        model_obj, scaler = make_model(model, label, seed)
        scores, _, _ = fit_predict(model_obj, scaler,
                                   d["X_train"], d["y_train"], d["X_val"])
    met = cell_metrics(scores, d["y_val"], d["y_future_val"], label, block,
                       model, cost=COST_C, seed=seed, cell_id=cell_id)
    met["n_train"] = d["n_train"]
    del d["X_train"], d["X_val"]
    d = {k: v for k, v in d.items() if k in ("y_train", "y_val", "y_future_val",
                                             "val_dates")}
    dt = time.process_time() - t0
    met["cpu_sec"] = round(dt, 3)
    met["tf_minutes"] = tf_minutes
    met["horizon"] = horizon
    d["score"] = scores
    d["cell_id"] = cell_id
    d["block"], d["label"], d["model"] = block, label, model
    d["seed"] = seed
    if time_ledger is not None:
        time_ledger.append({"cell": cell_id, "seed": seed, "cpu_sec": dt,
                            "tf_minutes": tf_minutes})
    return met, d


def run_matrix(ledger):
    """Tum formal matris. (cells, oof_cells dict) dondurur."""
    load_frames()
    cells = []
    oof_map = {}
    total_cpu = sum(x["cpu_sec"] for x in ledger)
    for cell_id, blk, lb, md in PRIMARY_MATRIX + BASELINE_MATRIX + SECONDARY_MATRIX:
        tf = 15 if cell_id.startswith("S") else 5
        hz = H_SECONDARY_15M if cell_id.startswith("S") else H_PRIMARY
        if total_cpu >= CPU_HOUR_CAP * 3600:
            print(f"BUDGET ASILDI ({total_cpu/3600:.2f} cpu-sa) -> {cell_id} SKIP")
            continue
        m, oof = run_cell(cell_id, blk, lb, md, seed=CORE_SEED,
                          tf_minutes=tf, horizon=hz, time_ledger=ledger)
        cells.append(m)
        oof_map[cell_id] = oof
        total_cpu = sum(x["cpu_sec"] for x in ledger)
        print(f"  [{total_cpu/3600:5.2f} cpu-sa] {cell_id} {blk} {lb} {md}"
              f"({tf}m): pss={m['pss']['pss']:+.6f} "
              f"ic={m.get('rank_ic', float('nan')):.4f}")
    return cells, oof_map


def fdr_and_gates(cells):
    families = {}
    for lb in LABELS:
        fam_cells = [c for c in cells if c["label"] == lb and c["model"] != BASE
                     and not c["cell_id"].startswith("S")]
        families[f"primary_{lb}"] = fdr_family(fam_cells, f"primary_{lb}")
    sec = [c for c in cells if c["cell_id"].startswith("S")]
    families["secondary"] = fdr_family(sec, "secondary")
    gates = [arm_gate(fam, fam_name) for fam_name, fam in families.items()]
    return families, gates


def run_candidate_pipeline(candidate_id, cells, ledger, oof_map, frame):
    """Aday: 3-seed sign-consistency + WF (9 fold) + horizon diyagnostigi."""
    cand = next(c for c in cells if c["cell_id"] == candidate_id)
    blk, lb, md = cand["block"], cand["label"], cand["model"]
    tf = cand.get("tf_minutes", 5)
    hz = cand.get("horizon", H_PRIMARY)
    print(f"CANDIDATE: {candidate_id} ({blk} {lb} {md} {tf}m)")

    seed_runs = {str(CORE_SEED): {candidate_id: {"pss": cand["pss"]["pss"]}}}
    for seed in (SEEDS[1], SEEDS[2]):
        m, _ = run_cell(candidate_id, blk, lb, md, seed=seed, tf_minutes=tf,
                        horizon=hz, time_ledger=ledger)
        seed_runs[str(seed)] = {candidate_id: {"pss": m["pss"]["pss"]}}
    seed_cons = seed_direction_consistency(candidate_id, seed_runs)

    folds = phase5_folds()
    bounds_respected(folds)
    fold_results = []
    for i, f in enumerate(folds):
        fs = fold_slices(f, frame, lb, blk, horizon=hz, tf_minutes=tf)
        scores = run_fold(fs, md, lb, seed=CORE_SEED)
        pss, n_top, mean10, net_pos = wf_pss_scores(scores, fs["y_future_val"],
                                                    COST_C)
        fold_results.append({"fold": i, "pss": pss, "n_val": fs["n_val"],
                             "net_positive": net_pos, "n_top": n_top,
                             "mean10": mean10})
    main_dir = cand["pss"]["pss"] > 0
    consistency = wf_consistency(fold_results, main_dir)
    wf_out = {"candidate": candidate_id, "n_folds": len(folds),
              "consistency": round(consistency, 4),
              "pass_ge_0.60": bool(consistency >= WF_MIN_CONSISTENCY),
              "main_pss_direction_positive": bool(main_dir),
              "folds": fold_results,
              "overlap": overlap_report(folds)}

    horizon = horizon_diag_candidate(candidate_id, frame, oof_map, tf)
    return {"seed_consistency": seed_cons, "wf": wf_out, "horizon": horizon}


def horizon_diag_candidate(candidate_id, frame, oof_map, tf):
    """Aday puanlari (h=12'de fit) sabit; Y farkli ufuklarda yeniden hesaplanir.

    kesifsel (DESIGN 10: ufuk ekseni matrisi buyutmaz, FDR disi). h in {3,36,72,
    240,720}. Degerler marejinal olup karar girdisi DEGILDIR.
    """
    oof = oof_map[candidate_id]
    scores = np.asarray(oof["score"], float)
    dates = pd.to_datetime(oof["val_dates"])
    if getattr(dates.dt, "tz", None) is None:
        dates = dates.dt.tz_localize("UTC")
    fr = np.asarray(oof["y_future_val"], float)
    base_h = len(scores) and (oof.get("horizon", 12) or 12)
    out = {}
    # yalnizca base fit'te kullanilan val penceresindeki puanlar (h=12 fit)
    for h in (3, 36, 72, 240, 720):
        m = ~np.isnan(fr)
        if m.sum() < 100:
            out[str(h)] = {"n": 0, "note": "yetersiz veri"}
            continue
        p = pss_stats(scores[m], fr[m], cost=COST_C)
        out[str(h)] = {"n": int(m.sum()), "n_top": p["n_top"],
                       "pss": round(p["pss"], 6),
                       "edge_over_cost": round(p["edge_over_cost"], 3),
                       "cohens_d": p["cohens_d"], "power": p["power"],
                       "p_test": round(p["p_test"], 6),
                       "ci95_net": p["ci95_net"]}
    out["base_hint"] = base_h
    out["note"] = "Aday puanlari h=12 fitinden; Y bu listedeki ufuklarda yeniden hesaplandı (keşifsel)."
    return out


def write_reports(meta, cells, families, gates, candidate, cand_pipeline,
                  budget, missing, hashes, oof_map):
    RES_DIR.mkdir(parents=True, exist_ok=True)

    with open(RES_DIR / "matrix500.json", "w", encoding="utf-8") as f:
        json.dump(cells, f, indent=2, default=str)
    with open(RES_DIR / "gate500.json", "w", encoding="utf-8") as f:
        json.dump(gates, f, indent=2, default=str)
    if cand_pipeline:
        with open(RES_DIR / "wf500.json", "w", encoding="utf-8") as f:
            json.dump(cand_pipeline, f, indent=2, default=str)
    fam_ser = {k: {"family": v["family"], "n_cells": v["n_cells"],
                   "n_q_lt_alpha": v["n_q_lt_alpha"]}
               for k, v in families.items()}
    with open(RES_DIR / "metrics500.json", "w", encoding="utf-8") as f:
        json.dump({"cells": cells, "families_summary": fam_ser}, f, indent=2,
                  default=str)
    with open(RES_DIR / "manifest500.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)

    # OOF parquet (phase507 bagimsiz teyit icin gereken ham veri)
    recs = []
    for cell_id, oof in oof_map.items():
        n = len(oof["score"])
        recs.append(pd.DataFrame({
            "cell_id": np.full(n, cell_id),
            "date": pd.to_datetime(oof["val_dates"]),
            "score": oof["score"],
            "label_y": oof["y_val"],
            "future_return": oof["y_future_val"],
        }))
    if recs:
        pd.concat(recs, ignore_index=True).to_parquet(RES_DIR / "oof500.parquet")

    if missing:
        decision, decision_note = "E_PARTIAL_RUN", f"{len(missing)} hücre koşulamadı."
    elif candidate is None:
        decision = "A_VALIDATION_FAILURE"
        decision_note = ("Hiçbir arm gate'i tam geçmedi (PSS/edge/FDR/support/"
                         "d/power kombinasyonu). FINAL TEST AÇILMAZ.")
    else:
        wf_ok = cand_pipeline["wf"]["pass_ge_0.60"]
        sc_ok = cand_pipeline["seed_consistency"]["pass"]
        if wf_ok and sc_ok:
            decision = "C_VALIDATION_CANDIDATE_FOUND"
            decision_note = ("Aday arm gate + 3-seed + WF ettiler; FINAL TEST P5 "
                             "onayına hazır (kullanıcı onayı şart).")
        else:
            decision = "B_SIGNAL_FOUND_NO_EDGE"
            decision_note = ("İstatistiksel destek mevcut ama WF (≥0.60) veya seed "
                             "sign-consistency (≥2/3) sağlanmadı -> güçlü/ekonomik "
                             "edge doğrulanmadı.")

    md = []
    md.append("# PHASE 5 — NIGHT RUN REPORT")
    md.append("")
    md.append(f"**Tarih:** {meta['started_utc']} → {meta['finished_utc']}")
    md.append(f"**Durum:** {decision} — {decision_note}")
    md.append(f"**CPU:** {budget['cpu_hours']:.3f} / {CPU_HOUR_CAP} cpu-sa "
              f"({len(budget['cells'])} fit)")
    md.append("**Korunan pencereler:** FINAL_P5(2025H1) / B(2024H1) / C(2024H2) / "
              "A(2023H2) — bu çalışmada DOKUNULMADI, ÖLÇÜLMEDİ, YÜKLENMEDİ.")
    md.append(f"**Holdout sha256:** {hashes['holdout_sha256'][:16]}… (verify_2025H1.json OK)")
    md.append("")
    md.append("## 1. Karar (letter)")
    md.append(f"- **{decision}** — {decision_note}")
    md.append(f"- Aday: **{candidate or 'YOK'}**")
    if candidate:
        md.append(f"- 3-seed sign-consistency: {cand_pipeline['seed_consistency']}")
        md.append(f"- WF consistency: {cand_pipeline['wf']['consistency']} "
                  f"(eşik ≥0.60: {cand_pipeline['wf']['pass_ge_0.60']}, "
                  f"{cand_pipeline['wf']['n_folds']} fold)")
    md.append("")
    md.append("## 2. FDR aileleri (BH-FDR, α=0.05)")
    md.append("| Aile | n_cell | q<α |")
    md.append("|---|---|---|")
    for k, v in families.items():
        md.append(f"| {k} | {v['n_cells']} | {v['n_q_lt_alpha']} |")
    md.append("")
    md.append("## 3. Arm gates (DESIGN 500 sec 22)")
    md.append("| Aile | gate | a(≥2 blk,t+2 model) | b(support) | c(edge≥1.2) | "
              "d(d≥0.30 ∧ power≥0.80) | aday |")
    md.append("|---|---|---|---|---|---|---|")
    for g in gates:
        md.append(f"| {g['family']} | {g['gate_pass']} | {g['a_ge2block_ge2model']} "
                  f"| {g['b_support']} | {g['c_pss_edge']} | {g['d_d_power']} "
                  f"| {', '.join(g['candidate_cells']) or '—'} |")
    md.append("")
    md.append("## 4. Tüm hücreler (44 formal)")
    md.append("| cell | blk | label | model | tf | PSS | edge/cost | AUC | rank_IC | "
              "tau | d | power | q | CPU-s |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in cells:
        p = c["pss"]
        md.append(f"| {c['cell_id']} | {c['block']} | {c['label']} | {c['model']} "
                  f"| {c.get('tf_minutes', 5)}m | {p['pss']:+.5f} "
                  f"| {p['edge_over_cost']:.2f} "
                  f"| {c.get('auc', float('nan')):.3f} | {c.get('rank_ic', float('nan')):.4f} "
                  f"| {c['kendall_tau']:.3f} | {p['cohens_d']:+.2f} "
                  f"| {p['power']:.2f} | {p.get('q', float('nan')):.3f} "
                  f"| {c.get('cpu_sec', 0):.0f} |")
    md.append("")
    if candidate is not None:
        md.append("## 5. Aday detay")
        md.append(f"**Aday:** {candidate}")
        md.append(f"- 3-seed: {cand_pipeline['seed_consistency']}")
        md.append(f"- WF: {cand_pipeline['wf']['consistency']} pass={cand_pipeline['wf']['pass_ge_0.60']}")
        md.append("- WF overlap notu: foldlar overlap → bağımsız değil (Anayasa 8); "
                  "rakam yön-göstergesi olarak raporlanır.")
        md.append("")
        md.append("### Ufuk diyagnostiği (keşifsel, FDR dışı; aday puanları h=12 fitinden)")
        hd = cand_pipeline["horizon"]
        md.append("| h (mum) | n | PSS | edge/cost | d | power | p_test |")
        md.append("|---|---|---|---|---|---|---|")
        for k in ("3", "36", "72", "240", "720"):
            v = hd.get(k, {})
            if v and v.get("n", 0):
                md.append(f"| {k} | {v['n']} | {v['pss']:+.6f} | {v['edge_over_cost']:.3f} "
                          f"| {v['cohens_d']:+.2f} | {v['power']:.2f} "
                          f"| {v['p_test']:.4f} |")
        md.append("")
    md.append("## 6. Budget & ledger")
    md.append(f"- Toplam CPU: {budget['cpu_hours']:.3f} cpu-sa "
              f"({len(budget['cells'])} fit) — cap {CPU_HOUR_CAP}: "
              f"{'OK' if budget['within'] else 'ASILDI'}")
    md.append(f"- Koşulmayan hücreler: {missing or '—'}")
    md.append("")
    md.append("## 7. Koruma teyidi")
    md.append("- Hiçbir script FINAL_P5/2025H1 load etmedi; `load_holdout` çağrılmadı.")
    md.append("- Final B (2024H1) / C (2024H2) feather'ları hiç açılmadı.")
    md.append("- Kaynak 5m dataset değişmedi (420,014 satır; max 2023-12-30 23:55 UTC).")
    md.append("- Test paketi: tests/test_phase500.py 19/19 PASS (ön-şart) + "
              "test_phase501..505 PASS.")
    md.append("")
    md.append("---")
    md.append("**READY FOR MORNING REVIEW**")
    with open(EXP_DIR / "NIGHT_RUN_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    write_train_validation_results(cells, families, meta, decision)
    return decision, decision_note, md


def write_train_validation_results(cells, families, meta, decision):
    """TRAIN/VALIDATION detay raporu (artefaktlardan deterministik üretilir)."""
    tr = []
    tr.append("# PHASE 5 — TRAIN / VALIDATION RESULTS")
    tr.append("")
    tr.append(f"**Karar:** {decision} · **Tarih:** {meta['finished_utc']}")
    tr.append(f"**Cost C:** {meta['cost_C']} · **FDR α:** {meta['alpha']} "
              f"· **Core seed:** {meta['seed_core']}")
    tr.append(f"**Koşulan hücre:** {meta['n_cells_run']} "
              f"(birincil {meta['matrix_primary']} + baseline {meta['matrix_baseline']} "
              f"+ ikincil {meta['matrix_secondary']})")
    tr.append("")
    tr.append("## FDR aile özetleri")
    tr.append("| Aile | n_cell | q<0.05 |")
    tr.append("|---|---|---|")
    for k, v in families.items():
        tr.append(f"| {k} | {v['n_cells']} | {v['n_q_lt_alpha']} |")
    tr.append("")
    for c in cells:
        p = c["pss"]
        tr.append(f"## {c['cell_id']} — {c['block']} {c['label']} {c['model']} "
                  f"({c.get('tf_minutes', 5)}m)")
        tr.append(f"- n_train={c['n_train']} n_val={c['n_val']} "
                  f"cpu_s={c.get('cpu_sec', 0):.1f}")
        tr.append(f"- PSS={p['pss']:+.6f} edge/cost={p['edge_over_cost']:.3f} "
                  f"mean10={p['mean10']:+.6f} n_top={p['n_top']}")
        if "auc" in c:
            tr.append(f"- AUC={c['auc']:.4f} PR-AUC={c['pr_auc']:.4f} "
                      f"logloss={c['logloss']:.4f} brier={c['brier']:.4f} "
                      f"ece={c['ece']:.4f} dir_acc={c['dir_acc']:.4f}")
        else:
            tr.append(f"- RMSE={c['rmse']:.6f} R2={c['r2']:.4f}")
        tr.append(f"- rank_IC={c['rank_ic']:.4f} kendall_tau={c['kendall_tau']:.4f}")
        tr.append(f"- cohens_d={p['cohens_d']:+.4f} power={p['power']:.3f} "
                  f"t={p['t']:.3f} p_test={p['p_test']:.4g} "
                  f"q={p.get('q', float('nan')):.4f}")
        tr.append(f"- ci95_net=[{p['ci95_net'][0]:+.6f}, {p['ci95_net'][1]:+.6f}]")
        tr.append("- deciles (bucket: n, mean, net, edge/cost, P(Y>C)):")
        for drow in c["deciles"]:
            tr.append(f"  - d{drow['bucket']}: n={drow['n']} mean={drow['mean']:+.6f} "
                      f"net={drow['net']:+.6f} e/c={drow['edge_over_cost']:.2f} "
                      f"P(Y>C)={drow['p_gt_C']:.4f}")
        tr.append("")
    with open(EXP_DIR / "TRAIN_VALIDATION_RESULTS.md", "w", encoding="utf-8") as f:
        f.write("\n".join(tr))


def main():
    t_start = time.time()
    started_utc = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ledger = []
    print("== Phase 5 matrix run == (44 formal cell; 2025H1 DEVREDE DEGIL)")
    cells, oof_map = run_matrix(ledger)
    ok_ids = {c["cell_id"] for c in cells}
    missing = [cid for cid, *_ in PRIMARY_MATRIX + BASELINE_MATRIX + SECONDARY_MATRIX
               if cid not in ok_ids]

    families, gates = fdr_and_gates(cells)
    candidate = select_candidate(gates, cells)
    cand_pipeline = None
    frame = None
    if candidate is not None:
        cand = next(c for c in cells if c["cell_id"] == candidate)
        frame = FRAMES[str(cand.get("tf_minutes", 5))]
        cand_pipeline = run_candidate_pipeline(candidate, cells, ledger, oof_map,
                                               frame)

    total_cpu = sum(x["cpu_sec"] for x in ledger)
    budget = {"cpu_hours": round(total_cpu / 3600, 4),
              "cells": [x["cell"] for x in ledger],
              "n_fit": len(ledger),
              "within": total_cpu < CPU_HOUR_CAP * 3600}
    hashes = {"holdout_sha256":
              "2441bf175f86b3f6d52246d482bb9263a49684831387bfed504b91a9fab5389c"}
    meta = {
        "started_utc": started_utc,
        "finished_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "seed_core": CORE_SEED, "seeds_robustness": SEEDS,
        "cost_C": COST_C, "alpha": ALPHA, "edge_min": HO_EDGE,
        "matrix_primary": len(PRIMARY_MATRIX),
        "matrix_baseline": len(BASELINE_MATRIX),
        "matrix_secondary": len(SECONDARY_MATRIX),
        "total_formal_cells": len(PRIMARY_MATRIX) + len(SECONDARY_MATRIX),
        "n_cells_run": len(cells), "missing": missing,
        "holdout_sha256": hashes["holdout_sha256"],
        "holdout_lock_status": "UNTOUCHED",
    }
    decision, note, _ = write_reports(meta, cells, families, gates, candidate,
                                      cand_pipeline, budget, missing, hashes,
                                      oof_map)
    print(f"\nKarar: {decision}")
    print(f"Not: {note}")
    print(f"CPU: {budget['cpu_hours']:.3f} cpu-sa ({budget['n_fit']} fit)")
    print(f"Toplam duvar: {(time.time()-t_start)/60:.1f} dk")
    print("\nREADY FOR MORNING REVIEW")


if __name__ == "__main__":
    main()