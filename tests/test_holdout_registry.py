"""FIX-2: holdout registry consistency (featherless, deterministik).

Ne YAPAR: HOLDOUT_REGISTRY.md'deki 4 pencere/tarih/statü/tüketici kaydını
p5_splits kilitli sabitleriyle karşılaştırır.
Ne YAPMAZ: holdout dosyası AÇMAZ (feather/hash/read yok), model eğitmez,
statü değiştirmez, otomatik-düzeltme yapmaz. Başarısızlık = registry VEYA
kod tarafında incelenmesi gereken tutarsızlık demektir.
Not: registry tarihleri GÜN-granülerdir; saat belirtilmişse aynen
denetlenir, belirtilmemişse eksiklik UYARI olarak raporlanır (tarih
tutarlılığı etkilenmez).
Calistir: py -m pytest tests/test_holdout_registry.py -q
"""
import pathlib
import re
import sys
import warnings

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.freqai import p5_splits as p5

REGISTRY = ROOT / "experiments" / "phase_05_ml" / "holdout" / "HOLDOUT_REGISTRY.md"
EXPECTED_STATUS = {"FINAL_P5": "CONSUMED", "FINAL_A": "CONSUMED",
                   "FINAL_B": "CONSUMED", "FINAL_C": "UNTOUCHED"}
CLOSED_SET = {"CONSUMED", "UNTOUCHED"}


def _parse_registry():
    text = REGISTRY.read_text(encoding="utf-8")
    sections = {}
    for m in re.finditer(r"##\s+(FINAL_[ABC]|FINAL_P5)\b(.*?)(?=\n## |\Z)",
                         text, re.S):
        name, body = m.group(1), m.group(2)
        dm = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:→|->)\s*(\d{4}-\d{2}-\d{2})"
                       r"(?:\s+(\d{2}:\d{2}))?", body)
        sm = re.search(r"Durum:\s*\*\*(\w+)\*\*", body)
        assert dm and sm, f"bolum parse edilemedi: {name}"
        stated = dm.group(3) is not None
        sections[name] = {"start": dm.group(1), "end": dm.group(2),
                          "end_hm": dm.group(3) if stated else None,
                          "time_stated": stated,
                          "status": sm.group(1), "body": body}
    return sections


def test_registry_file_exists():
    assert REGISTRY.is_file(), "registry dosyasi yok"


def test_windows_match_protected():
    sections = _parse_registry()
    assert set(sections) == {n for n, _, _ in p5.PROTECTED}, \
        f"pencere kumesi uyumsuz: {sorted(sections)}"
    for name, start, end in p5.PROTECTED:
        rec = sections[name]
        assert rec["start"] == start.strftime("%Y-%m-%d"), f"{name} baslangic"
        assert rec["end"] == end.strftime("%Y-%m-%d"), f"{name} bitis"
        if rec["time_stated"]:
            assert rec["end_hm"] == end.strftime("%H:%M"), f"{name} bitis-saati"
        else:
            warnings.warn(f"{name}: bitis-saati registry'de belirtilmemis "
                          f"(sabit: {end.strftime('%H:%M')}) — presizyon eksigi, "
                          f"tutanak icin kaydedildi")


def test_status_closed_set_and_expected():
    sections = _parse_registry()
    for name, rec in sections.items():
        assert rec["status"] in CLOSED_SET, f"{name}: acik-kume disi statu"
        assert rec["status"] == EXPECTED_STATUS[name], \
            f"{name}: beklenen {EXPECTED_STATUS[name]}, kayitta {rec['status']} " \
            f"(mesru tuketim ise registry+M.20 + bu test birlikte guncellenir)"


def test_consumed_have_consumer_records():
    sections = _parse_registry()
    for name, rec in sections.items():
        if rec["status"] != "CONSUMED":
            continue
        body = rec["body"]
        assert re.search(r"(Phase\s+\d|M\.20)", body), \
            f"{name}: tuketici-deney referansi yok"
        assert re.search(r"\.(json|csv|md)\b|RESULT|rapor|koşu", body), \
            f"{name}: tuketim artefakt/rapor referansi yok"


def test_untouched_state_no_use():
    sections = _parse_registry()
    for name, rec in sections.items():
        if rec["status"] != "UNTOUCHED":
            continue
        assert re.search("ÇALIŞTIRILMADI|kullanım kanıtı yok|açılmadı",
                         rec["body"]), \
            f"{name}: kullanilmama kaniti yok"
