"""Faz 3 — Veri ayrımı + Final Test A guard (kilitli, 2026-09-04).

Kaynak: `config/experiment.yaml:10-16` (phase_02_walkforward splitleri Faz 3 için de geçerli).
- TRAIN:      2020-01-01 -> 2022-12-31  (model + 5-fold CV burada)
- VALIDATION: 2023-01-01 -> 2023-06-30  (model SEÇİMİ yalnızca burada)
- FINAL_A:    2023-07-01 -> 2023-12-31  (YASAK: tuning/seçim/değerlendirme yok;
              yalnızca önceden kilitlenmiş pipeline'ın son değerlendirmesi için)
"""
import pandas as pd

TRAIN_START = pd.Timestamp("2020-01-01")
TRAIN_END = pd.Timestamp("2022-12-31")
VAL_START = pd.Timestamp("2023-01-01")
VAL_END = pd.Timestamp("2023-06-30")
FINAL_A_START = pd.Timestamp("2023-07-01")
FINAL_A_END = pd.Timestamp("2023-12-31")

N_FOLDS = 5
SEEDS = [42, 7, 123, 2026, 999]

TF_MINUTES = 5  # 5m timeframe


def slice_frame(df: pd.DataFrame, start, end, date_col: str = "date",
                horizon: int | None = None) -> pd.DataFrame:
    """Pencere dilimi + label-sınır kuralı (kilitli, 2026-09-04).

    Label H mum geleceğe baktığı için, kullanılabilir satırlar
    `end - H*5m` ile sınırlıdır. Böylece train label'ları validation'a,
    validation label'ları Final Test A'ya TAŞMAZ (son 12 mum atılır).
    """
    if horizon is None:
        from .labels import LABEL_HORIZON
        horizon = LABEL_HORIZON
    ts = pd.to_datetime(df[date_col])
    cutoff = pd.Timestamp(end) - pd.Timedelta(minutes=horizon * TF_MINUTES)
    m = (ts >= pd.Timestamp(start)) & (ts <= cutoff)
    return df.loc[m].reset_index(drop=True)


class FinalTestLeakError(AssertionError):
    """Final Test A'ya erişim denemesi."""


def assert_no_final_leak(dates: pd.Series, context: str = "") -> None:
    """Serideki herhangi bir tarih FINAL_A aralığındaysa ABORT."""
    ts = pd.to_datetime(dates)
    bad = ts[(ts >= FINAL_A_START) & (ts <= FINAL_A_END)]
    if len(bad):
        raise FinalTestLeakError(
            f"FINAL_TEST_A sizintisi [{context}]: {len(bad)} satir "
            f"({bad.min()} -> {bad.max()}) aralikta. ABORT.")
    if (ts > VAL_END).any():
        raise FinalTestLeakError(
            f"VAL sonrasi veri [{context}]: max {ts.max()} > {VAL_END.date()}. ABORT.")


def split_train_val(df: pd.DataFrame, date_col: str = "date"):
    """Çerçeveyi TRAIN/VAL olarak böl (FINAL_A guard dahil)."""
    assert_no_final_leak(df[date_col], "split-girdi")
    ts = pd.to_datetime(df[date_col])
    train = df[(ts >= TRAIN_START) & (ts <= TRAIN_END)].reset_index(drop=True)
    val = df[(ts >= VAL_START) & (ts <= VAL_END)].reset_index(drop=True)
    if len(train) == 0 or len(val) == 0:
        raise ValueError(f"bos split: train={len(train)} val={len(val)}")
    return train, val


def calendar_folds() -> pd.DataFrame:
    """5 expanding takvim fold'u (yalnızca TRAIN aralığında, deterministik).

    TimeSeriesSplit ruhu: test pencereleri Train'in son ~910 gününü kapsar,
    her fold'un train'i baştan genişler. Veri okumaz; sonuçlara dokunmaz.
    """
    import datetime
    start = TRAIN_START.date()
    end = TRAIN_END.date()
    total_days = (end - start).days + 1  # 1096
    test_len = total_days // (N_FOLDS + 1)  # 182
    rows = []
    for k in range(N_FOLDS):
        test_start = start + datetime.timedelta(days=total_days - (N_FOLDS - k) * test_len)
        test_end = test_start + datetime.timedelta(days=test_len - 1)
        rows.append({"fold": k,
                     "train_start": str(start), "train_end": str(test_start - datetime.timedelta(days=1)),
                     "test_start": str(test_start), "test_end": str(test_end)})
    folds = pd.DataFrame(rows)
    # guard: hiçbir test FINAL_A'ya değemez
    assert (pd.to_datetime(folds["test_end"]) < FINAL_A_START).all()
    return folds
