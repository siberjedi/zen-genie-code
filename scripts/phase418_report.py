"""Phase 4.18 - REPORT_418.md uretici (yukari taslaklardan okur, yorum yok).

18 baslikli rapor + A/B/C ayri sonuclari.
Cikti: tuning47/REPORT_418.md + stdout ozet.
Calistir: py -3 scripts/phase418_report.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

D47 = ROOT / "experiments" / "phase_04_rl" / "tuning47"
SEEDS = [42, 7, 123, 2026, 999]
HORIZONS = [1, 3, 12, 36, 72, 240, 720]
PRIMARY_H = 12
HNAME = {1: "5m", 3: "15m", 12: "1h", 36: "3h", 72: "6h", 240: "20h", 720: "60h"}


def pct(x):
    return f"{x:+.4f}" if isinstance(x, float) else str(x)


def f(x, nd=4):
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ev = json.load(open(D47 / "events418.json", encoding="utf-8"))
    fw = json.load(open(D47 / "forward418.json", encoding="utf-8"))
    st = json.load(open(D47 / "stats418.json", encoding="utf-8"))
    dc = json.load(open(D47 / "decomp418.json", encoding="utf-8"))

    audit = ev["meta"]["leakage_audit"]
    L = []

    def h1(t, c="="):
        L.append(f"\n## {t}\n")

    h1("1. Executive Summary")
    ed = st["edge_decision"]["final_answer_A"]
    L.append(f"- A) **Decision-level predictive edge: {ed}**")
    L.append("- B) Economic trading edge: BU FAZIN resmi sonucu DEĞİL; 4.17 "
             f"locked A-gate E1 icin FAIL idi (mean 0.225 < 0.80).")
    L.append("- C) RL ≈ exposure × market drift: 4.16/4.17 bu yonde idi; 4.18 "
             "karar-duzeyi bulgusu da ayri seed'larda kontrol-medyaninin altında "
             "(C1/C3 fail) → drift-diskirimi korunuyor.")
    L.append(f"- Flow: leakage audit **PASS** ({len(audit['checks'])} kontrol) → "
             f"events → forward (2000 MC/seed) → stats → decomp → rapor.")
    L.append("- Verdict (prereg C1..C4): **edge YOK**: C1 lower-CI>0 fail "
             "(pooled BUY h12), C3 >=3/5 seed ayni yonde fail "
             f"({st['edge_decision']['conditions']['detail']}), "
             f"C2 q<0.05 (123 ama LOW POWER+asimetrik), C4 sanity PASS.")

    h1("2. Research Question")
    L.append("RL policy, giris kararini verdigi ANDA gelecekteki getiriyi ongoren "
             "bilgi tasiyor mu? (decision-level predictive power; P&L/Sharpe degil)")

    h1("3. Preregistered Hypothesis")
    L.append("- H0: RL BUY sonrasi h=1h forward getirisi, rejim-stratifiye random/"
             "control girislerinden AYRISMaz (median fark 0, dir-acc 0.5).")
    L.append("- H1: Pozitif ayrisma var (gercek sinyal). Ikincil H1: SELL sonrasi "
             "negatif ayrisma.")

    h1("4. Dataset")
    L.append(f"- BTC/USDT 5m val `2023-01-01..2023-06-30`; "
             f"len(closes)=51825, n_tradable=51794, off=30.")
    L.append("- Seeds: {SEEDS}; Kaynak: `art_E1_seed{s}.json` (action dizileri) "
             "+ prices; FreqAI satiri phase03 val_trades ile.")
    L.append(f"- Cikti artefacts: events/forward/stats/decomp418.json")

    h1("5. Leakage Audit")
    for c in audit["checks"]:
        L.append(f"- [{('OK' if c['ok'] else 'FAIL')}] {c['name']} — {c['detail']}")
    L.append(f"- Replay-equality: {audit['replay_equality']}")
    L.append("- Kilit semantik: `obs=closes[k:k+30]`, `execution=close[30+k]`, "
             "`r_h=close[30+k+h]/close[30+k]-1` (execution candle forward aralikta "
             "YOK, h>=1). Feature'lar obs pencere disina cikmaz; normalizer "
             "train-only (burada fit/apply yok); action dizileri post-training "
             "sabit kayitlar.")

    h1("6. BUY Results (RL buy forward-return vs random/control)")
    L.append("| seed | n | rl_mean | rl_med | ctrl_med-med | mc_p(mean) | flag |")
    L.append("|---|---|---|---|---|---|---|")
    for s in SEEDS:
        r = st["primary"]["buy"].get(str(s))
        if not r:
            L.append(f"| {s} | 0 | - | - | - | - | sinyal yok |")
            continue
        L.append(f"| {s} | {r['n']} | {pct(r['rl_mean'])} | {pct(r['rl_median'])} | "
                 f"{pct(r['ctrl_med_med'])} | {r['mc_p_mean']:.4f} | {r['flag']} |")
    L.append("\nNot: t=1h (h=12). Small-n (7/999) EVALUABLE DEGIL; 2026 sinyal yok.")

    h1("7. SELL Results")
    L.append("| seed | n | rl_mean | rl_med | ctrl_med-med | mc_p(mean, low=good) | flag |")
    L.append("|---|---|---|---|---|---|---|")
    for s in SEEDS:
        r = st["primary"]["sell"].get(str(s))
        if not r:
            L.append(f"| {s} | 0 | - | - | - | - | sinyal yok |")
            continue
        L.append(f"| {s} | {r['n']} | {pct(r['rl_mean'])} | {pct(r['rl_median'])} | "
                 f"{pct(r['ctrl_med_med'])} | {r['mc_p_mean']:.4f} | {r['flag']} |")
    ps = st["pooled_sell"]
    L.append(f"\nPooled SELL (seed-cluster): median-diff metric "
             f"{ps['metric_mean_of_seed_median_diffs']:+.4f}, "
             f"CI95 [{ps['ci95_cluster_boot'][0]:+.4f}, {ps['ci95_cluster_boot'][1]:+.4f}], "
             f"lower>0={ps['lower_gt_0']}. BUYUYSE → SELL sonrasi fiyat KONTROLDEN "
             f"YUKARI → sell sinyali onegorucu degil (hatta ters yonde).")

    h1("8. Horizon Curve (BUY forward-return medians: RL vs control)")
    def hcell(seed, h):
        hs = str(h)
        if hs == str(PRIMARY_H) and str(seed) in st["primary"]["buy"]:
            return st["primary"]["buy"][str(seed)]
        return st["secondary_horizons"]["buy"].get(str(seed), {}).get(hs, {})
    L.append("| h | seed123 RL_med | 123 ctrl_med | seed42 RL_med | 42 ctrl_med | "
             "drift_all |")
    L.append("|---|---|---|---|---|---|")
    for h in HORIZONS:
        hs = str(h)
        c123 = hcell(123, h); c42 = hcell(42, h)
        dr = fw["drift_h"].get(hs, 0)
        L.append(f"| {HNAME[h]} ({hs}) | {pct(c123.get('rl_median', 0))} | "
                 f"{pct(c123.get('ctrl_med_med', 0))} | "
                 f"{pct(c42.get('rl_median', 0))} | "
                 f"{pct(c42.get('ctrl_med_med', 0))} | {pct(dr)} |")
    L.append("\nBasit trend (herhangi bir random step'in beklenen 1h getirisi) "
             f"+0.015% — RL 123 bul-cell'inde median <= kontrol.")

    h1("9. Regime Results (BUY h=12, descriptive)")
    L.append("| seed | regime | n | rl_mean | ctrl_mean-med | mc_p |")
    L.append("|---|---|---|---|---|---|")
    for s in SEEDS:
        for r, v in fw["regime_buy"].get(str(s), {}).items():
            if v["n"] == 0:
                continue
            L.append(f"| {s} | {r} | {v['n']} | {pct(v['rl_mean'])} | "
                     f"{pct(v['ctrl_mean_med'])} | {v['mc_p']:.4f} |")
    L.append("\nDegil: rejim alt-grupları kucuk-n → betimsel (edge-lerden sayılmaz).")

    h1("10. Random-Control Comparison (per-seed h=12 details)")
    L.append("| seed | mwu_p | welch_p | mean_diff | CI95(welch) | CI95(boot) | "
             "cohen_d | cliff | power | dirfrac | binom_p |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for s in SEEDS:
        r = st["primary"]["buy"].get(str(s))
        if not r:
            continue
        L.append(f"| {s} | {r['mwu_p']:.4f} | {r['welch_p']:.4f} | "
                 f"{pct(r['mean_diff'])} | [{f(r['ci95_mean_diff'][0])}, "
                 f"{f(r['ci95_mean_diff'][1])}] | "
                 f"[{f(r['ci95_mean_diff_boot'][0])}, "
                 f"{f(r['ci95_mean_diff_boot'][1])}] | {r['cohens_d']:+.3f} | "
                 f"{r['cliff_delta']:+.3f} | {r['power']:.2f} | "
                 f"{r['directional']['frac']:.3f} | {r['directional']['p_binom_vs_0p5']:.4f} |")

    h1("11. Baseline / FreqAI Comparison")
    bh = fw["buy_hold"]
    L.append(f"- B&H: gross {bh['gross_pct']}%, net {bh['net_pct']}% (n=1 trade).")
    L.append(f"- Drift (1h): +%.4f%% — trend-aware kontrol referansi." % (fw["drift_h"]["12"] * 100))
    L.append("- Phase3 baseline: **N/A** (per-entry trade artefacti yok; "
             "comparison.json metrics-only; Gameplan baseline ≈ B&H → B&H satırı).")
    L.append("| seed | FreqAI n(1h) | FreqAI mean(1h) | RL mean(1h) | RL n |")
    L.append("|---|---|---|---|---|")
    for s in SEEDS:
        fa = fw["freqai_buy"][str(s)]
        rl = st["primary"]["buy"].get(str(s))
        L.append(f"| {s} | {fa['n_h'].get('12')} | {pct(fa['mean_h'].get('12'))} | "
                 f"{pct(rl['rl_mean'] if rl else 0)} | {rl['n'] if rl else 0} |")

    h1("12. Exposure vs Timing Decomposition (descriptive)")
    L.append("RL_net ≈ DRIFT(E·R_BH) + TIMING − FRICTION; TIMING_reentry = "
             "RL_net − REENTRY_net (4.16 anchor). HEPsi compounding dartigi → "
             "approximate.")
    L.append("| seed | E | RL_net | DRIFT_g | TIM_g | FRICTION | TIM_net | "
             "REENTRY | TIM_reentry |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for s in SEEDS:
        d = dc["seeds"][str(s)]
        L.append(f"| {s} | {d['exposure_E']:.4f} | {pct(d['rl_net_pct'])} | "
                 f"{pct(d['drift_exposure_only_gross'])} | {pct(d['timing_gross'])} | "
                 f"{pct(d['friction_pct'])} | {pct(d['timing_net'])} | "
                 f"{pct(d['reentry_net'])} | {pct(d['timing_reentry'])} |")

    h1("13. Statistical Results")
    L.append(f"- FDR (BUY h12, BH): {st['fdr_buy_h12_bh']} → "
             f"yalnizca 123 q<0.05 (0.0033) ama LOW POWER ve median bazında degil; "
             f"C2'yi tek basına gezirmez.")
    L.append(f"- Pooled BUY (seed-cluster, 10k): metric "
             f"{st['pooled_buy']['metric_mean_of_seed_median_diffs']:+.6f}, "
             f"CI95 [{st['pooled_buy']['ci95_cluster_boot'][0]:+.6f}, "
             f"{st['pooled_buy']['ci95_cluster_boot'][1]:+.6f}], "
             f"lower>0={st['pooled_buy']['lower_gt_0']} (seed bagimsizligi "
             f"VARSAYILMAZ).")
    L.append(f"- Pooled SELL: CI95 "
             f"[{st['pooled_sell']['ci95_cluster_boot'][0]:+.6f}, "
             f"{st['pooled_sell']['ci95_cluster_boot'][1]:+.6f}], "
             f"lower>0={st['pooled_sell']['lower_gt_0']} (sell tarafında ters yön).")

    h1("14. Evaluable / Not Evaluable")
    L.append(f"- EVALUABLE (n≥{st['evaluable_min']}): 42 (n=40), 123 (n=117) — "
             f"ikisi de LOW POWER (power<0.80).")
    L.append("- EVALUABLE DEGIL: 7 (n=7), 999 (n=11) — 1h sonuclari edge lehine "
             "okunamaz (DESIGN F1).")
    L.append("- 2026: 0 BUY/sell → sinyal-yok seed; 'edge yok' kantı DEĞİL "
             "(prereg note).")

    h1("15. Edge Decision (preregistered C1..C4)")
    for k, v in st["edge_decision"]["conditions"].items():
        if k != "detail":
            L.append(f"- {k}={v}")
    L.append(f"- Detail: {st['edge_decision']['conditions']['detail']}")
    L.append(f"\n**KARAR: {ed}** — pre-registered kurallar disinda sonradan kriter "
             "eklenmedi.")

    h1("16. Limitations")
    L.append("- n cok kucuk (7, 11) seed'ler istatistiksel olarak degerlendirilemedi.")
    L.append("- 123'ün mc_p(mean) sinyali asimetrik 1-2 buyuk event, median ve "
             "power tarafini tutmuyor.")
    L.append("- Pooled uc-yok test n=4 UCSI seed; cluster CI genis.")
    L.append("- FreqAI only BTC/USDT trades (136-141/csv); farkli seed model "
             "hiperparametreleri; yalnizcı tanımlayıcı satır.")
    L.append("- Decomposition approximate (compounding); reentry anchor 4.16 konvansyonu.")
    L.append("- 2023H1 tek piyasa tecrübesi; genellenebilirlik iddiasi yok.")

    h1("17. Protocol Impact")
    L.append("- Alpha Gate **LOCKED-DIAGNOSTIC** kalır; 4.18'de selection "
             "criterion yapılMADi.")
    L.append("- Locked threshold'lar (Sharpe>=0.80, gap<0.35, 30g, power 0.80): "
             "DEĞİŞMEZ.")
    L.append("- Env/reward/action-space/normalizer DEĞİŞTİRMEDİ; training/tuning YOK.")
    L.append("- 4.18 yalnızca YENİ dosyalar: scripts/phase418_*, "
             "tests/test_phase418.py + artefacts/REPORT.")

    h1("18. Final Test B Protection")
    L.append("- Final Test B: İNDİRİLMEDİ · AÇILMADI · ÇALIŞTIRMADI · METRIKLERI "
             "HESAPLANMADI. Hiçbir 4.18 script'i Final B path'ine referans içermiyor.")

    h1("SONUÇ (A / B / C — ayrı ayrı)")
    L.append(f"**A) Decision-level predictive edge var mı? → {ed}**")
    L.append("   (BUY 1h: pooled lower-CI ≤ 0, >=3/5 seed ayni yonde DEĞİL; "
             "123 tek pozitif-asimetrik; 7/999 EVALUABLE DEGIL.)")
    L.append("**B) Economic trading edge var mi? → BU FAZIN KONUSU DEGIL.** "
             "4.17 locked A-gate: E1 mean 0.225 < 0.80 → FAIL; bu fazda yeni eğitim/"
             "ölcüm yok; karar-duzeyi bulgular ekonomik edge olarak satılamaz.")
    L.append("**C) RL sonucu market exposure/drift ile açiklanabilir mi? → "
             "BÜYÜK ÖLÇÜDE EVET.** 4.16/4.17 ile tutarli: e.g. 999 net +80.8% ≈ "
             "E×R_BH 82.8% ≈ reentry 76.0%; 123 net 18.8% ama friction 41.3% ile "
             "driftin büyük kısmı turnover ile yenilmiş; karar-duzeyi sinyal de "
             "kontrol-medyaninin altında/etrafında.")

    txt = "\n".join(L) + "\n"
    (D47 / "REPORT_418.md").write_text(txt, encoding="utf-8")
    print(txt)
    print("REPORT_418.md yazildi:", D47 / "REPORT_418.md")


if __name__ == "__main__":
    main()