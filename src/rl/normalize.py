"""Faz 4.4 — Train-fit normalizer (leakage-safe).

- fit: SADECE train çerçevesi (mean/std per kolon).
- transform: train'den öğrenilmiş istatistikle HERHANGİ çerçeveye (val/test).
- Binary kolonlar (position) normalize EDİLMEZ (çağıran seçer; env obs'undaki
  position/equity_norm'a dokunulmaz — ölçekleri zaten ~0/1).
- Artifact: kolonlar + mean/std + train_range + hash (metadata'ya girer).
"""
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

NORMALIZER_VERSION = "1.0"


class FitNormalizer:
    def __init__(self, columns: list):
        self.columns = list(columns)
        self.means_: dict = {}
        self.stds_: dict = {}
        self.train_range_: str | None = None

    def fit(self, df: pd.DataFrame, train_range: str = "") -> "FitNormalizer":
        for c in self.columns:
            v = df[c].astype(float)
            self.means_[c] = float(v.mean())
            s = float(v.std(ddof=1))
            self.stds_[c] = s if s > 0 else 1.0
        self.train_range_ = train_range
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.means_:
            raise ValueError("fit edilmemiş normalizer")
        out = df.copy()
        for c in self.columns:
            out[c] = (df[c].astype(float) - self.means_[c]) / self.stds_[c]
        return out

    def artifact_hash(self) -> str:
        blob = json.dumps({"cols": self.columns, "means": self.means_,
                           "stds": self.stds_, "range": self.train_range_,
                           "v": NORMALIZER_VERSION}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def save(self, path) -> str:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"columns": self.columns, "means": self.means_,
                                 "stds": self.stds_, "train_range": self.train_range_,
                                 "version": NORMALIZER_VERSION,
                                 "hash": self.artifact_hash()}, indent=2),
                     encoding="utf-8")
        return self.artifact_hash()

    @staticmethod
    def load(path) -> "FitNormalizer":
        d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        n = FitNormalizer(d["columns"])
        n.means_, n.stds_, n.train_range_ = d["means"], d["stds"], d["train_range"]
        return n
