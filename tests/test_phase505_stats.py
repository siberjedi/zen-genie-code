"""Phase 5 — İstatistik modülü testleri (phase505_stats.py).

Kapsam: BH-FDR (bilinen örnek), decile tablo, Kendall tau sürekliliği,
PSS/edge/CI, Cohen d + power, arm gate mantığı.
Calistir: py -3 tests/test_phase505_stats.py
"""
import pathlib
import sys

TESTROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TESTROOT))
sys.path.insert(0, str(TESTROOT / "scripts"))

import numpy as np

from phase505_stats import (benjamini_hochberg, ece, kendall_decile_order,
                            decile_table, pss_stats, fdr_family, arm_gate,
                            select_candidate, seed_direction_consistency,
                            cell_metrics, ALPHA)

PASSED = []


def check(name, cond, detail=""):
    PASSED.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


print("== phase505 ==")
# BH-FDR: adım-yukarı (B-H) formülü, bilinen örnek
ps = [0.01, 0.04, 0.03, 0.4, 0.2, 0.05]
qs = benjamini_hochberg(ps)
# beklenen: step-down running min; qs orijinal sırada [0.05,0.05,0.05,0.60,0.24,0.05]
qs_exp = [0.05000000000000001, 0.05000000000000001, 0.05000000000000001,
          0.6000000000000001, 0.24000000000000005, 0.05000000000000001]
check("BH beklenen değerler", all(abs(a - b) < 1e-9 for a, b in zip(qs, qs_exp)),
      f"qs={np.round(qs,4)}")
pairs = sorted(zip(ps, qs))
check("BH p-sıralı q non-decreasing", all(pairs[i][1] <= pairs[i + 1][1] + 1e-9
      for i in range(len(pairs) - 1)))
check("BH tek p", abs(benjamini_hochberg([0.001])[0] - 0.001) < 1e-9)

# decile tablosu: yükselen puan -> yükselen mean return -> tau~1
rng = np.random.default_rng(7)
score = rng.normal(0, 1, 1000)
future = 0.5 * score + rng.normal(0, 0.1, 1000)
dt = decile_table(score, future)
check("10 dilim", len(dt) == 10)
means = np.array([d["mean"] for d in dt])
check("decile süreklilik tau>0", kendall_decile_order(dt) > 0.9, f"tau={kendall_decile_order(dt)}")
check("top decile p_gt_0 > bottom", dt[-1]["p_gt_0"] > dt[0]["p_gt_0"])

# PSS
pss = pss_stats(score, future, cost=0.003)
check("PSS pozitif", pss["pss"] > 0)
check("edge/cost meta doğru", abs(pss["edge_over_cost"] - pss["pss"] / 0.003) < 1e-9)
check("Cohen d > 0", pss["cohens_d"] > 0)
check("p_test < alpha", pss["p_test"] < ALPHA)
check("CI alt uc", pss["ci95_net"][0] < pss["ci95_net"][1])
# sabit puan -> argsort stable ilk %10 (sıralama yok) -> PSS = o dilimin mean - C
const_s = np.full(500, 0.5)
fr2 = rng.normal(0, 0.001, 500)
pss_c = pss_stats(const_s, fr2, cost=0.003)
k_c = int(np.ceil(500 * 0.10))
check("constant puan PSS~ilk%10 mean-C", abs(pss_c["pss"] - (fr2[:k_c].mean() - 0.003)) < 1e-6)

# cell_metrics sınıflandırma
y_cls = (future > 0).astype(float)
cm = cell_metrics(score, y_cls, future, "L1", "B0", "M2", cell_id="E001")
check("cell_metrics anahtarlar", {"auc", "logloss", "brier", "ece", "rank_ic",
                                  "kendall_tau", "pss", "deciles"} <= set(cm.keys()))
check("auc [0,1]", 0 <= cm["auc"] <= 1)

# ECE: mükemmel kalibre -> 0
perfect_y = np.array([0, 1] * 250, float)
perfect_p = np.array([0.5, 0.5] * 250, float)
check("ECE mükemmel = 0", abs(ece(perfect_p, perfect_y, 10)) < 1e-6)

# arm gate mantığı: iki hücre birleşik -> gate pass
g_cells = []
for i, blk in enumerate(("B0", "B1")):
    g_cells.append({"cell_id": f"E{10+i}", "block": blk, "label": "L1", "model": f"M3",
                    "auc": 0.6, "rank_ic": 0.02, "kendall_tau": 0.5,
                    "pss": {"p_test": 0.001, "q": 0.01, "pss": 0.01,
                            "edge_over_cost": 2.0, "pss_positive": True,
                            "edge_ge_1.2": True, "cohens_d": 0.4, "power": 0.9}})
fam = fdr_family(g_cells, "primary_L1")
g = arm_gate(fam, "primary_L1")
check("arm gate pass (>=2 blok, >=2 model destek+edge+d/power)", g["gate_pass"] and g["d_d_power"])
check("candidate cell var", len(g["candidate_cells"]) >= 1, f"{g['candidate_cells']}")

# select_candidate: argmax(edge/cost), tie-break küçük id
c1 = {"cell_id": "X09", "pss": {"edge_over_cost": 1.5}}
c2 = {"cell_id": "X02", "pss": {"edge_over_cost": 2.0}}
g2 = {"gate_pass": True, "candidate_cells": ["X09", "X02"]}
g_no = {"gate_pass": False, "candidate_cells": []}
check("select argmax edge", select_candidate([g2, g_no], [c1, c2]) == "X02")

# seed yön tutarlılığı
sr = {"42": {"Q": {"pss": 0.01}}, "7": {"Q": {"pss": 0.005}},
      "123": {"Q": {"pss": -0.001}}}
sc = seed_direction_consistency("Q", sr)
check("seed dir 2/3", sc["pass"] and abs(sc["frac"] - round(2 / 3, 3)) < 1e-9)

print()
fails = [n for n, c in PASSED if not c]
print(f"TOPLAM: {len(PASSED)} test, {len(fails)} hatalı")
assert not fails, fails
print("ALL PASS")