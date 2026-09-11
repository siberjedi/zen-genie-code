"""Central time-conversion helpers (neutral, pandas-only).

Behavior lock: identical semantics to the phase10/phase11 `to_ms` copies
(Timedelta-division to integer ms; naive input treated as UTC).
Locked by tests/test_conventions.py (T1/T2).
No production call-site uses this module yet — migration needs separate
approval and must update the T3 locked map in the same change.
Circular-import risk: none (imports pandas only; nothing imports this yet).
"""
import numpy as np
import pandas as pd

_EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
_MS = pd.Timedelta("1ms")


def ensure_utc(d):
    """Naive -> UTC-localized; aware (any tz) -> converted to UTC (same instant).

    Accepts Series, DatetimeIndex, Timestamp, datetime. Unknown/naive inputs
    are never shifted, only localized.
    """
    if isinstance(d, pd.Series):
        return d.dt.tz_localize("UTC") if d.dt.tz is None else d.dt.tz_convert("UTC")
    if isinstance(d, pd.DatetimeIndex):
        return d.tz_localize("UTC") if d.tz is None else d.tz_convert("UTC")
    ts = pd.Timestamp(d)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def to_ms(d):
    """Unit-safe datetime -> integer milliseconds since epoch.

    Accepts whatever pd.to_datetime accepts (Series/Index/scalar/str).
    Series/DatetimeIndex -> int64 numpy array; scalars -> python int.
    Naive input is treated as UTC (locked legacy behavior, see T1/T2).
    """
    t = ensure_utc(pd.to_datetime(d))
    out = (t - _EPOCH) // _MS
    if isinstance(out, pd.Series):
        return out.to_numpy(dtype="int64")
    arr = np.asarray(out)
    if arr.ndim == 0:
        return int(arr)
    return arr.astype("int64")
