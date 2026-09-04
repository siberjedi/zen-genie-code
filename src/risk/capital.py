"""
CORE CAPITAL + USDT Reserve — strateji/signal'den tamamen bağımsız risk katmanı.

- CORE CAPITAL kilitli başlangıç sermayesi (örn. 100 USDT), config/capital.json'da tanımlı, asla trading sinyali ile değişmez.
- Harvesting: gerçekleşmiş net kâr (closed trades close_profit_abs toplamı) belirlenen periyotta, belirlenen oranda USDT rezervine aktarılır.
- Trading sermayesi = CORE + (realized - harvested) + unrealized? Ama CORE korunur, kâr ayrıştırılır.
- Toplam özkaynak = CORE + realized + unrealized (rezerv dahil).
- Ayrı gösterim: reserve_balance, realized_profit, total_equity.

Bu modül sadece DB ve config okur, strategy'ye dokunmaz.
"""
import json
import pathlib
import time
import datetime
import sqlite3
from typing import Dict, Any, Optional

# Path resolution — hem host hem container uyumlu
_p = pathlib.Path(__file__).resolve()
try:
    ROOT = _p.parents[2] if len(_p.parents) > 2 and (_p.parents[2] / "config").exists() else pathlib.Path("/app") if pathlib.Path("/app/config").exists() else _p.parents[2]
except:
    ROOT = pathlib.Path("/app")
import os
if os.getenv("ZEN_ROOT"):
    ROOT = pathlib.Path(os.getenv("ZEN_ROOT"))

CONFIG_PATH = ROOT / "config" / "capital.json"
# freqtrade config'den dry_run_wallet fallback için
FREQ_CONFIG_PATH = ROOT / "config" / "freqtrade.example.json"
# state persistence — writable data dizini öncelikli, sonra trades dizini
STATE_PATH_WRITABLE = ROOT / "data" / "capital_state.json"
STATE_PATH = ROOT / "freqtrade" / "user_data" / "capital_state.json"
# Alternatif: config/capital_state.json (yedek)
STATE_PATH_ALT = ROOT / "config" / "capital_state.json"
DB_PATH = ROOT / "freqtrade" / "user_data" / "tradesv3.dryrun.sqlite"
# Tüm olası state yolları (yazma için writable öncelikli)
STATE_PATHS_ALL = [STATE_PATH_WRITABLE, STATE_PATH, STATE_PATH_ALT, pathlib.Path("/tmp/capital_state.json")]

DEFAULT_CORE = 100.0
DEFAULT_RATIO = 0.5
DEFAULT_PERIOD = "daily"
DEFAULT_THRESHOLD = 1.0

def _load_json(path: pathlib.Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def load_capital_config() -> Dict[str, Any]:
    """config/capital.json oku, yoksa freqtrade dry_run_wallet'tan CORE al."""
    cfg = _load_json(CONFIG_PATH, {})
    core = cfg.get("core_capital")
    if core is None:
        try:
            j = json.loads(FREQ_CONFIG_PATH.read_text(encoding="utf-8"))
            core = float(j.get("dry_run_wallet", DEFAULT_CORE))
        except:
            core = DEFAULT_CORE
    harvest = cfg.get("harvest", {})
    protection = cfg.get("protection", {})
    # protection defaults: lock 50% of profit above core, trailing equity highwater
    return {
        "core_capital": float(core),
        "core_locked_at": cfg.get("core_locked_at", "2026-08-31T00:00:00Z"),
        "core_note": cfg.get("core_note", ""),
        "harvest_ratio": float(harvest.get("ratio", DEFAULT_RATIO)),
        "harvest_period": harvest.get("period", DEFAULT_PERIOD),
        "harvest_threshold": float(harvest.get("threshold", DEFAULT_THRESHOLD)),
        "harvest_auto_enabled": bool(harvest.get("auto_enabled", True)),
        "protection_lock_ratio": float(protection.get("lock_ratio", 0.5)),
        "protection_trailing": bool(protection.get("trailing", True)),
        "protection_mode": protection.get("mode", "equity_highwater"),
        "protection_buffer_pct": float(protection.get("buffer_pct", 0)),
        "protection_note": protection.get("note", ""),
        "reserve_currency": cfg.get("reserve_currency", "USDT"),
        "is_strategy_independent": True,
        "_raw": cfg,
    }

def load_state() -> Dict[str, Any]:
    """capital_state.json oku, yoksa init. Writable öncelikli."""
    for p in STATE_PATHS_ALL:
        try:
            if p.exists():
                j = json.loads(p.read_text(encoding="utf-8"))
                return {
                    "core_capital": float(j.get("core_capital", 0)),
                    "reserve_balance": float(j.get("reserve_balance", 0)),
                    "total_harvested": float(j.get("total_harvested", 0)),
                    "last_harvest_realized": float(j.get("last_harvest_realized", 0)),
                    "last_harvest_at": j.get("last_harvest_at"),
                    "last_harvest_amount": float(j.get("last_harvest_amount", 0)),
                    "harvest_history": j.get("harvest_history", []),
                    "created_at": j.get("created_at"),
                    # trailing protection fields (yeni)
                    "high_water_mark": float(j.get("high_water_mark", j.get("core_capital", 0)) or 0),
                    "locked_profit": float(j.get("locked_profit", j.get("reserve_balance", 0)) or 0),
                    "protection_threshold": float(j.get("protection_threshold", j.get("core_capital", 0)) or 0),
                    "protection_history": j.get("protection_history", []),
                }
        except Exception:
            continue
    cfg = load_capital_config()
    core = float(cfg["core_capital"])
    return {
        "core_capital": core,
        "reserve_balance": 0.0,
        "total_harvested": 0.0,
        "last_harvest_realized": 0.0,
        "last_harvest_at": None,
        "last_harvest_amount": 0.0,
        "harvest_history": [],
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "high_water_mark": core,
        "locked_profit": 0.0,
        "protection_threshold": core,
        "protection_history": [],
    }

def save_state(state: Dict[str, Any]) -> None:
    """Atomic write — writable öncelikli, tüm yollar denenir."""
    state["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    if not state.get("core_capital"):
        cfg = load_capital_config()
        state["core_capital"] = cfg["core_capital"]
    # writable'a yazmayı dene, olmazsa diğerleri
    saved = False
    for p in STATE_PATHS_ALL:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(p)
            saved = True
            # writable'a yazıldıysa diğerlerine de yedekle (best-effort)
            if p == STATE_PATH_WRITABLE:
                continue
        except Exception:
            continue
    if not saved:
        # son çare tmp
        try:
            pathlib.Path("/tmp/capital_state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        except:
            pass

def _get_realized_from_db() -> float:
    """Freqtrade DB'den kümülatif gerçekleşmiş net kâr (close_profit_abs)."""
    try:
        if not DB_PATH.exists():
            return 0.0
        # try dashboard's robust db_connect first (container'da WAL ile başa çıkar)
        try:
            import importlib.util as _ilu
            _app_path = ROOT / "dashboard" / "backend" / "app.py"
            if not _app_path.exists():
                _app_path = pathlib.Path("/app/app.py")
            if _app_path.exists():
                _spec = _ilu.spec_from_file_location("_cap_app2", str(_app_path))
                _mod = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                con = _mod.db_connect()
                cur = con.cursor()
                cur.execute("SELECT COALESCE(SUM(close_profit_abs),0) FROM trades WHERE is_open=0")
                v = cur.fetchone()[0]
                con.close()
                return float(v or 0)
        except Exception:
            pass
        import shutil, tempfile
        try:
            con = sqlite3.connect(str(DB_PATH), timeout=5)
            cur = con.cursor()
            cur.execute("SELECT COALESCE(SUM(close_profit_abs),0) FROM trades WHERE is_open=0")
            v = cur.fetchone()[0]
            con.close()
            return float(v or 0)
        except Exception:
            pass
        try:
            con = sqlite3.connect(f"file:{DB_PATH}?mode=ro&nolock=1", uri=True, timeout=2)
            cur = con.cursor()
            cur.execute("SELECT COALESCE(SUM(close_profit_abs),0) FROM trades WHERE is_open=0")
            v = cur.fetchone()[0]
            con.close()
            return float(v or 0)
        except Exception:
            pass
        tmp = pathlib.Path(tempfile.gettempdir()) / f"zen-capital-{DB_PATH.name}.ro.sqlite"
        try:
            src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=2)
            dst = sqlite3.connect(str(tmp))
            src.backup(dst)
            dst.close()
            src.close()
            con = sqlite3.connect(str(tmp), timeout=2)
            cur = con.cursor()
            cur.execute("SELECT COALESCE(SUM(close_profit_abs),0) FROM trades WHERE is_open=0")
            v = cur.fetchone()[0]
            con.close()
            return float(v or 0)
        except Exception:
            return 0.0
    except Exception:
        return 0.0

def _get_unrealized_from_db() -> float:
    """Açık pozisyonların unrealized toplamı — dashboard open_positions ile aynı: bulk ticker."""
    try:
        if not DB_PATH.exists():
            return 0.0
        import httpx
        # get open trades — try dashboard's db_connect if available (container uyumlu)
        rows = []
        try:
            import importlib.util as _ilu2
            _app_path = ROOT / "dashboard" / "backend" / "app.py"
            if not _app_path.exists():
                _app_path = pathlib.Path("/app/app.py")
            if _app_path.exists():
                _spec = _ilu2.spec_from_file_location("_cap_app", str(_app_path))
                _mod = _ilu2.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                con = _mod.db_connect()
                cur = con.cursor()
                cur.execute("SELECT pair, amount, open_rate FROM trades WHERE is_open=1")
                rows = cur.fetchall()
                con.close()
            else:
                raise Exception("no app")
        except Exception:
            # fallback: simple
            import shutil, tempfile
            try:
                con = sqlite3.connect(str(DB_PATH), timeout=5)
                cur = con.cursor()
                cur.execute("SELECT pair, amount, open_rate FROM trades WHERE is_open=1")
                rows = cur.fetchall()
                con.close()
            except Exception:
                try:
                    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro&nolock=1", uri=True, timeout=2)
                    cur = con.cursor()
                    cur.execute("SELECT pair, amount, open_rate FROM trades WHERE is_open=1")
                    rows = cur.fetchall()
                    con.close()
                except Exception:
                    return 0.0
        if not rows:
            return 0.0
        # bulk ticker — tek çağrı, rate-limit dostu (open_positions ile aynı)
        try:
            with httpx.Client(timeout=8) as c:
                r = c.get("https://api.binance.com/api/v3/ticker/24hr")
                r.raise_for_status()
                arr = r.json()
                tickers = {x["symbol"]: float(x.get("lastPrice", 0)) for x in arr if "symbol" in x}
        except Exception:
            tickers = {}
        unreal = 0.0
        for pair, amount, open_rate in rows:
            try:
                sym = pair.replace("/", "")
                cur_price = tickers.get(sym)
                if cur_price is None:
                    # fallback single price
                    with httpx.Client(timeout=4) as c2:
                        r2 = c2.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": sym})
                        r2.raise_for_status()
                        cur_price = float(r2.json()["price"])
                else:
                    cur_price = float(cur_price)
                unreal += (cur_price - float(open_rate)) * float(amount)
            except Exception:
                continue
        return unreal
    except Exception:
        return 0.0

def _period_due(last_at: Optional[str], period: str, now: datetime.datetime) -> bool:
    if not last_at:
        return True
    try:
        last = datetime.datetime.fromisoformat(last_at.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=datetime.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)
        delta = (now - last).total_seconds()
        if period == "daily":
            return delta >= 86400
        if period == "weekly":
            return delta >= 7 * 86400
        if period == "hourly":
            return delta >= 3600
        if period == "always" or period == "on_profit":
            return True
        # default daily
        return delta >= 86400
    except Exception:
        return True

def compute_capital_view(auto_harvest_check: bool = True) -> Dict[str, Any]:
    """
    Ana görünüm — CORE, REALIZED, RESERVE, TRADING, TOTAL EQUITY + TRAILING PROTECTION.
    Strateji/signal'den tamamen bağımsız risk katmanı.
    - CORE kilitli, asla değişmez.
    - Equity = CORE + realized + unrealized
    - HighWaterMark = max(equity) → trailing
    - LockedProfit = (HWM - CORE) * lock_ratio → asla azalmaz (profit lock)
    - ProtectionThreshold = CORE + LockedProfit → core artık risk altında değil, üstü trading'de kullanılabilir.
    """
    cfg = load_capital_config()
    state = load_state()
    core = float(state.get("core_capital") or cfg["core_capital"])
    if not state.get("core_capital"):
        state["core_capital"] = core
        save_state(state)

    total_realized = _get_realized_from_db()
    unrealized = _get_unrealized_from_db() if auto_harvest_check else 0
    total_equity = core + total_realized + unrealized

    # --- Trailing principal protection ---
    lock_ratio = float(cfg.get("protection_lock_ratio", 0.5))
    # high water mark — en yüksek equity
    prev_hwm = float(state.get("high_water_mark", core) or core)
    high_water_mark = max(prev_hwm, total_equity, core)
    # locked profit — asla geri gitmez (trailing)
    prev_locked = float(state.get("locked_profit", state.get("reserve_balance", 0)) or 0)
    # profit above core at HWM
    profit_at_hwm = max(0, high_water_mark - core)
    new_locked = profit_at_hwm * lock_ratio
    # trailing: locked sadece artar
    locked_profit = max(prev_locked, new_locked)
    protection_threshold = core + locked_profit
    # buffer
    buffer_pct = float(cfg.get("protection_buffer_pct", 0) or 0)
    if buffer_pct:
        protection_threshold = protection_threshold * (1 - buffer_pct/100)

    # state güncelle — HWM ve locked (theoretical) trailing olarak güncelle
    prev_threshold = float(state.get("protection_threshold", core) or core)
    needs_save = False
    if high_water_mark > prev_hwm or locked_profit > prev_locked or abs(protection_threshold - prev_threshold) > 1e-9:
        state["high_water_mark"] = high_water_mark
        state["locked_profit"] = locked_profit  # theoretical, HWM bazlı
        state["protection_threshold"] = protection_threshold
        needs_save = True
        # protection history (theoretical)
        ph = state.get("protection_history", [])
        ph.append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "equity": total_equity,
            "high_water_mark": high_water_mark,
            "locked_profit": locked_profit,
            "protection_threshold": protection_threshold,
            "incremental_locked": locked_profit - prev_locked,
            "realized_profit": total_realized,
        })
        state["protection_history"] = ph[-50:]
    # actual reserve — sadece gerçekleşmiş net kârdan karşılanır, asla locked'tan fazla olamaz
    # Kural: actual_reserve <= min(locked_profit_theoretical, max(realized_profit,0)*lock_ratio)
    # Önceki bug: reserve=locked ile senkronize ediliyordu, realized=0 iken bile 0.29 gösteriyordu — düzeltildi
    prev_reserve = float(state.get("reserve_balance", 0) or 0)
    realized_cap = max(total_realized, 0) * lock_ratio
    actual_reserve_target = min(locked_profit, realized_cap)
    # trailing + bug düzeltme: eğer prev_reserve realized_cap'tan büyükse (bug), doğrudan target'a düzelt
    if prev_reserve > realized_cap + 1e-9:
        actual_reserve = actual_reserve_target
        # bug düzeltme için her zaman güncelle (azalma olabilir)
        if abs(actual_reserve - prev_reserve) > 1e-9:
            state["reserve_balance"] = actual_reserve
            needs_save = True
    else:
        # normal trailing: asla azalmaz
        actual_reserve = max(prev_reserve, actual_reserve_target)
        if actual_reserve > prev_reserve + 1e-9:
            state["reserve_balance"] = actual_reserve
            needs_save = True
    if needs_save:
        save_state(state)

    # auto harvest check (eski harvest, strateji bağımsız)
    pending_harvestable = 0.0
    should_harvest_flag = False
    incremental = total_realized - float(state.get("last_harvest_realized", 0))
    if cfg["harvest_auto_enabled"] and incremental > 0:
        if incremental >= cfg["harvest_threshold"]:
            if _period_due(state.get("last_harvest_at"), cfg["harvest_period"], datetime.datetime.now(datetime.timezone.utc)):
                should_harvest_flag = True
                pending_harvestable = incremental * cfg["harvest_ratio"]
            else:
                pending_harvestable = incremental * cfg["harvest_ratio"]
        else:
            pending_harvestable = 0

    reserve = float(state.get("reserve_balance", 0))  # actual reserve — asla locked ile senkronize değil, sadece realized'dan beslenir
    total_harvested = float(state.get("total_harvested", 0))
    unharvested = total_realized - total_harvested
    trading_capital = core + max(0, unharvested)
    equity_vs_core_pct = ((total_equity / core - 1) * 100) if core else 0

    # next harvest due estimation
    next_due = None
    if state.get("last_harvest_at"):
        try:
            last = datetime.datetime.fromisoformat(state["last_harvest_at"].replace("Z", "+00:00"))
            if cfg["harvest_period"] == "daily":
                nxt = last + datetime.timedelta(days=1)
            elif cfg["harvest_period"] == "weekly":
                nxt = last + datetime.timedelta(weeks=1)
            elif cfg["harvest_period"] == "hourly":
                nxt = last + datetime.timedelta(hours=1)
            else:
                nxt = None
            if nxt:
                next_due = nxt.isoformat().replace("+00:00", "Z")
        except:
            pass

    # protection status
    distance_to_protection = total_equity - protection_threshold
    # core artık risk altında değil mi? equity >= core ise evet
    core_protected = total_equity >= core
    # net pozitif hedef: total_equity > core ?
    net_positive = total_equity > core
    protection_status = "protected" if total_equity >= protection_threshold else "at_risk" if total_equity < core else "watch"

    return {
        "core_capital": core,
        "core_locked_at": cfg["core_locked_at"],
        "core_note": cfg["core_note"],
        "realized_profit": total_realized,
        "unharvested_profit": max(0, unharvested),
        "reserve_balance": reserve,  # actual reserve — asla locked ile senkronize değil
        "actual_reserve": reserve,  # alias, dashboard için açık
        "total_harvested": total_harvested,
        "unrealized_pnl": unrealized,
        "trading_capital": trading_capital,
        "total_equity": total_equity,
        "equity_vs_core_pct": equity_vs_core_pct,
        # trailing protection — teorik vs gerçek ayrımı
        "high_water_mark": high_water_mark,
        "locked_profit": locked_profit,  # theoretical, HWM bazlı
        "locked_profit_theoretical": locked_profit,
        "actual_reserve": reserve,
        "protection_threshold": protection_threshold,  # CORE + locked_theoretical
        "protection_status": protection_status,
        "core_protected": core_protected,
        "net_positive": net_positive,
        "distance_to_protection": distance_to_protection,
        "protection": {
            "lock_ratio": lock_ratio,
            "trailing": cfg.get("protection_trailing", True),
            "mode": cfg.get("protection_mode", "equity_highwater"),
            "buffer_pct": buffer_pct,
            "high_water_mark": high_water_mark,
            "locked_profit": locked_profit,
            "locked_profit_theoretical": locked_profit,
            "actual_reserve": reserve,
            "threshold": protection_threshold,
            "threshold_theoretical": protection_threshold,
            "distance": distance_to_protection,
            "status": protection_status,
            "core_protected": core_protected,
            "net_positive": net_positive,
            "realized_profit": total_realized,
            "note": cfg.get("protection_note", ""),
        },
        "harvest": {
            "ratio": cfg["harvest_ratio"],
            "period": cfg["harvest_period"],
            "threshold": cfg["harvest_threshold"],
            "auto_enabled": cfg["harvest_auto_enabled"],
            "last_harvest_at": state.get("last_harvest_at"),
            "last_harvest_realized": state.get("last_harvest_realized", 0),
            "last_harvest_amount": state.get("last_harvest_amount", 0),
            "pending_harvestable": pending_harvestable,
            "incremental_since_last": incremental,
            "should_harvest": should_harvest_flag,
            "next_harvest_due": next_due,
        },
        "is_strategy_independent": True,
        "state_created_at": state.get("created_at"),
        "reserve_currency": cfg["reserve_currency"],
    }

def harvest(manual: bool = False, force_amount: Optional[float] = None) -> Dict[str, Any]:
    """
    Kârın koruma payını rezerve aktar — strateji bağımsız.
    Manuel veya periyot tetiklemeli.
    Returns updated view.
    """
    cfg = load_capital_config()
    state = load_state()
    total_realized = _get_realized_from_db()
    last_realized = float(state.get("last_harvest_realized", 0))
    incremental = total_realized - last_realized
    if incremental <= 0 and not manual:
        return {"harvested": 0, "reason": "no_incremental_profit", "view": compute_capital_view(auto_harvest_check=False)}

    # amount to harvest
    if force_amount is not None:
        harvest_amount = float(force_amount)
    else:
        # only harvest if threshold met, unless manual
        if not manual and incremental < cfg["harvest_threshold"]:
            return {"harvested": 0, "reason": f"incremental {incremental:.4f} < threshold {cfg['harvest_threshold']}", "view": compute_capital_view(auto_harvest_check=False)}
        harvest_amount = incremental * cfg["harvest_ratio"]
        # period check (skip if manual)
        if not manual and not _period_due(state.get("last_harvest_at"), cfg["harvest_period"], datetime.datetime.now(datetime.timezone.utc)):
            return {"harvested": 0, "reason": "period_not_due", "view": compute_capital_view(auto_harvest_check=False)}

    if harvest_amount <= 0:
        return {"harvested": 0, "reason": "harvest_amount_zero", "view": compute_capital_view(auto_harvest_check=False)}

    # update state
    new_reserve = float(state.get("reserve_balance", 0)) + harvest_amount
    new_total_harvested = float(state.get("total_harvested", 0)) + harvest_amount
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    state["reserve_balance"] = new_reserve
    state["total_harvested"] = new_total_harvested
    state["last_harvest_at"] = now_iso
    state["last_harvest_realized"] = total_realized
    state["last_harvest_amount"] = harvest_amount
    # history
    hist = state.get("harvest_history", [])
    hist.append({
        "timestamp": now_iso,
        "incremental_realized": incremental,
        "harvested": harvest_amount,
        "ratio": cfg["harvest_ratio"],
        "reserve_after": new_reserve,
        "total_realized_after": total_realized,
        "manual": manual,
    })
    # keep last 50
    state["harvest_history"] = hist[-50:]
    save_state(state)
    view = compute_capital_view(auto_harvest_check=False)
    view["last_harvest"] = {
        "harvested": harvest_amount,
        "incremental": incremental,
        "reserve_after": new_reserve,
        "manual": manual,
        "timestamp": now_iso,
    }
    return {"harvested": harvest_amount, "view": view}
