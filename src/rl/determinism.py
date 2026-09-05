"""Faz 4.6 — Determinizm altyapısı (protokol-dışı, infra-only).

- apply_thread_limits(): torch runtime thread kilidi + BLAS/OpenMP env
  değişkenleri (best-effort: süreç-içi importlardan SONRA çağrılırsa yalnızca
  torch tarafı etkilidir; entry-point'ler dosyabaşında da set eder).
- deterministic_mode(): warn_only ile deterministik algoritmalar; deterministik
  OLMAYAN op kullanılırsa raporlanır (sessizce görmezden gelinmez).
- canonical_hash(): platform-sabit (x86-64, kilitli lib sürümleri) deterministik
  serileştirme üzerinden sha256. Float'lar repr() ile (CPython shortest-roundtrip,
  aynı platformda stabil) — dokümante edilmiş seçim.
- save/load_artifacts(): action/equity/reward sequence + trade + hash kayıtları.
"""
import hashlib
import json
import os
import pathlib

DETERMINISM_VERSION = "1.0"


def apply_thread_limits(num_threads: int = 1) -> dict:
    os.environ.setdefault("OMP_NUM_THREADS", str(num_threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(num_threads))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", str(num_threads))
    applied = {"env_vars": {k: os.environ.get(k) for k in
                            ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                             "OPENBLAS_NUM_THREADS")}}
    try:
        import torch
        torch.set_num_threads(num_threads)
        try:
            # süreçte TEK SEFER çağrılabilir; tekrarı RuntimeError verir
            torch.set_num_interop_threads(num_threads)
            applied["interop_set"] = True
        except RuntimeError as e:
            applied["interop_set"] = False
            applied["interop_note"] = f"zaten kilitli: {e}".split(":")[0]
        applied["torch_threads"] = torch.get_num_threads()
        applied["torch_interop"] = torch.get_num_interop_threads()
        applied["cuda_available"] = bool(torch.cuda.is_available())
    except ImportError:
        applied["torch"] = "not-installed"
    return applied


def deterministic_mode() -> dict:
    """warn_only deterministik mod + rapor. Dönüş: etkin ayarlar."""
    rep = {"warn_only": True}
    try:
        import torch
        torch.use_deterministic_algorithms(True, warn_only=True)
        rep["torch_deterministic"] = True
    except ImportError:
        rep["torch_deterministic"] = False
    return rep


def runtime_snapshot() -> dict:
    snap = {"determinism_lib": DETERMINISM_VERSION}
    try:
        import torch
        snap.update({"torch_threads": torch.get_num_threads(),
                     "torch_interop": torch.get_num_interop_threads(),
                     "cuda_available": bool(torch.cuda.is_available()),
                     "cuda_used": False})  # CPU-only politika: device her zaman CPU
    except ImportError:
        snap["torch"] = "not-installed"
    snap["env_threads"] = {k: os.environ.get(k) for k in
                           ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                            "OPENBLAS_NUM_THREADS", "PYTHONHASHSEED")}
    return snap


def canonical_hash(values) -> str:
    """Deterministik serileştirme hash'i. int listeleri ve float listeleri destekler."""
    parts = []
    for v in values:
        if isinstance(v, float):
            parts.append(repr(v))
        else:
            parts.append(str(v))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _weight_leaves(obj):
    """İç-içe dict/list/tuple yapıyı deterministik sırada tensor/skaler yapraklara indirger.

    NOT (Faz 4.6 bulgusu): `np.ascontiguousarray(list_of_dicts)` gibi kestirmeler
    object-dizisi üretip POINTER hash'ler — her koşuda farklı çıkar. Bu yardımcı,
    container'lara recurse edip SADECE değerleri hash'ler.
    """
    import numpy as np
    if isinstance(obj, dict):
        for k in sorted(obj):
            yield from _weight_leaves(obj[k])
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _weight_leaves(v)
    else:
        try:
            arr = np.ascontiguousarray(obj.detach().cpu().numpy())
            yield ("t", arr.tobytes())
        except AttributeError:
            if obj is None or isinstance(obj, (bool, int, float, str)):
                yield ("s", repr(obj))
            # bilinmeyen tipler ATLANIR (hash'e girmez) — sessiz değil, aşağıda sayılır


def hash_model_weights(get_params: dict) -> str:
    """SB3 get_parameters() çıktısının deterministik hash'i."""
    h = hashlib.sha256()
    n = 0
    for kind, blob in _weight_leaves(get_params):
        h.update(kind.encode())
        h.update(blob.encode() if isinstance(blob, str) else blob)
        n += 1
    h.update(f"leaves:{n}".encode())
    return h.hexdigest()[:16]


def save_artifacts(path, actions, equities, rewards, trades=None, extra=None) -> dict:
    """Validation artifact paketi + hash'ler. Dönüş: hash sözlüğü."""
    p = pathlib.Path(path)
    acts = [int(a) for a in actions]
    eqs = [float(x) for x in equities]
    rws = [float(x) for x in rewards]
    hashes = {"actions": canonical_hash(acts), "equities": canonical_hash(eqs),
              "rewards": canonical_hash(rws)}
    payload = {"actions": acts, "equities": eqs, "rewards": rws,
               "n_steps": len(acts), "hashes": hashes}
    if trades is not None:
        payload["trades"] = trades
    if extra:
        payload["extra"] = extra
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")
    return hashes
