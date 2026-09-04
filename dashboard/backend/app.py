"""
Zen-Genie Dashboard Backend — Faz 1 Dry-Run gözlem katmanı
- Hiçbir secret frontend'e sızmaz (freqtrade config filtrelenir)
- Gerçek para modu bloklu
- Veri: SQLite (read-only) + Binance public REST + Docker inspect + log tail
- Market Universe: Binance USDT spot marketleri otomatik keşif, hacim filtresi, TOP_N likit pariteler
  Freqtrade VolumePairList ile aynı mantık: quoteVolume 24h bazlı sıralama + min_value filtresi
  BaselineStrategy parametreleri DEĞİŞMEZ (RSI 30/70, SMA50/200)
"""
import sqlite3, json, pathlib, time, subprocess, shlex, os, psutil, datetime, re, logging, concurrent.futures
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
# CORE CAPITAL risk katmanı — strateji bağımsız, sadece muhasebe
try:
    import capital as capital_m
except Exception as e:
    try:
        import importlib.util as _ilu
        _cap_path = pathlib.Path(__file__).parent / "capital.py"
        if _cap_path.exists():
            _spec = _ilu.spec_from_file_location("capital", str(_cap_path))
            capital_m = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(capital_m)
        else:
            # fallback: src/risk/capital.py (host)
            _cap_path2 = pathlib.Path(__file__).parents[2] / "src" / "risk" / "capital.py"
            if _cap_path2.exists():
                _spec2 = _ilu.spec_from_file_location("capital", str(_cap_path2))
                capital_m = _ilu.module_from_spec(_spec2)
                _spec2.loader.exec_module(capital_m)
            else:
                capital_m = None
                logging.getLogger("zen-genie").warning(f"capital module not available: {e}")
    except Exception as e2:
        capital_m = None
        logging.getLogger("zen-genie").warning(f"capital module not available: {e} / {e2}")

_p = pathlib.Path(__file__).resolve()
try:
    ROOT = _p.parents[2] if len(_p.parents)>2 and (_p.parents[2]/"config").exists() else pathlib.Path("/app") if pathlib.Path("/app/config").exists() else _p.parents[2]
except:
    ROOT = pathlib.Path("/app")
if os.getenv("ZEN_ROOT"):
    ROOT = pathlib.Path(os.getenv("ZEN_ROOT"))
DB_PATH = ROOT / "freqtrade" / "user_data" / "tradesv3.dryrun.sqlite"
CONFIG_PATH = ROOT / "config" / "freqtrade.example.json"
STARTED_AT = ROOT / "experiments" / "phase_01_dryrun" / "STARTED_AT"
PHASE_LOCK = ROOT / "experiments" / "phase_01_dryrun" / "PHASE_LOCK.md"
LOG_DIR = ROOT / "freqtrade" / "user_data" / "logs"

BINANCE_TICKER = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_PRICE = "https://api.binance.com/api/v3/ticker/price"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_EXCHANGE_INFO = "https://api.binance.com/api/v3/exchangeInfo"

# Strategy parameters (read-only, from BaselineStrategy) — DEĞİŞTİRME
RSI_PERIOD = 14
RSI_BUY = 30
RSI_SELL = 70
SMA_FAST = 50
SMA_SLOW = 200

# Universe keşif sabitleri — freqtrade VolumePairList ile senkron
_UNIVERSE_CACHE: Dict[str, Any] = {"pairs": [], "ts": 0.0, "total_active": 0, "after_volume": 0, "last_refresh": None, "raw": []}
_STABLE_BLACKLIST = {"USDC","FDUSD","TUSD","BUSD","DAI","USDP","EURI","EUR","USD1","USTC","USDE","FRAX","LUSD","GUSD","USDD","PYUSD","RLUSD","XAUT","PAXG","EURI","WEETH","USDe"}
DEFAULT_TOP_N = 30
DEFAULT_MIN_VOLUME = 5000000  # USDT quoteVolume 24h, config ile override edilir
DEFAULT_REFRESH = 1800

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("zen-genie")

def _read_universe_config():
    """Freqtrade config'den VolumePairList ayarlarını oku — tek kaynak prensibi."""
    top_n = DEFAULT_TOP_N
    min_vol = DEFAULT_MIN_VOLUME
    refresh = DEFAULT_REFRESH
    try:
        j = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for pl in j.get("pairlists", []):
            if pl.get("method") == "VolumePairList":
                top_n = int(pl.get("number_assets", top_n))
                min_vol = float(pl.get("min_value", min_vol))
                refresh = int(pl.get("refresh_period", refresh))
                break
        # env override
        if os.getenv("UNIVERSE_TOP_N"):
            top_n = int(os.getenv("UNIVERSE_TOP_N"))
        if os.getenv("UNIVERSE_MIN_VOLUME"):
            min_vol = float(os.getenv("UNIVERSE_MIN_VOLUME"))
        if os.getenv("UNIVERSE_REFRESH"):
            refresh = int(os.getenv("UNIVERSE_REFRESH"))
    except Exception as e:
        logger.warning(f"[universe] config read failed, using defaults: {e}")
    return top_n, min_vol, refresh

def _is_spot_trading(sym: dict) -> bool:
    if sym.get("status") != "TRADING":
        return False
    if not sym.get("isSpotTradingAllowed"):
        return False
    # permissionSets yapısı: [['SPOT','MARGIN', ...], ...]
    perms = []
    for ps in sym.get("permissionSets", []):
        if isinstance(ps, list):
            perms.extend(ps)
        else:
            perms.append(ps)
    perms.extend(sym.get("permissions", []))
    if "SPOT" not in perms:
        return False
    if sym.get("quoteAsset") != "USDT":
        return False
    if sym.get("baseAsset") in _STABLE_BLACKLIST:
        return False
    # leveraged token filtrelemesi: exchangeInfo zaten SPOT dışındakileri eliyor, ek filtre yok
    return True

def _fetch_exchange_info_symbols() -> List[dict]:
    with httpx.Client(timeout=15) as c:
        r = c.get(BINANCE_EXCHANGE_INFO)
        r.raise_for_status()
        data = r.json()
        return data.get("symbols", [])

def _fetch_tickers_map() -> Dict[str, dict]:
    with httpx.Client(timeout=12) as c:
        r = c.get(BINANCE_TICKER)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, dict):
            arr = [arr]
        m = {}
        for t in arr:
            try:
                m[t["symbol"]] = t
            except:
                continue
        return m

def get_universe(force_refresh: bool = False) -> List[str]:
    """
    Binance USDT spot universe keşfi:
    1) exchangeInfo -> aktif / SPOT / TRADING USDT pariteleri
    2) ticker/24hr -> quoteVolume ile likidite filtresi + sıralama
    3) TOP_N likit pariteyi seç, BTC/ETH garanti et
    4) 30dk cache (VolumePairList refresh_period)
    Dönüş: ["BTC/USDT", "ETH/USDT", ...] formatında
    """
    top_n, min_vol, refresh = _read_universe_config()
    now = time.time()
    if not force_refresh and _UNIVERSE_CACHE["pairs"] and (now - _UNIVERSE_CACHE["ts"] < refresh):
        return _UNIVERSE_CACHE["pairs"]
    try:
        t0 = time.time()
        symbols = _fetch_exchange_info_symbols()
        active = [s for s in symbols if _is_spot_trading(s)]
        # sadece USDT quote
        active = [s for s in active if s["symbol"].endswith("USDT")]
        tickers = _fetch_tickers_map()
        # hacim filtresi + sıralama
        scored = []
        for s in active:
            sym = s["symbol"]
            t = tickers.get(sym)
            if not t:
                continue
            try:
                qv = float(t.get("quoteVolume", 0))
            except:
                qv = 0
            if qv < min_vol:
                continue
            scored.append((sym, qv))
        scored.sort(key=lambda x: x[1], reverse=True)
        selected_syms = [sym for sym, _ in scored[:top_n]]
        # BTC/ETH garantisi (eğer min_vol yüzünden elenmişse ve aktifte varsa ekle)
        for must in ["BTCUSDT","ETHUSDT"]:
            if must not in selected_syms:
                # aktifte var mı kontrol et
                if any(s["symbol"]==must for s in active):
                    # hacmi düşük olsa bile ekle ama TOP_N aşmasın -> en düşük hacimliyi çıkar
                    if len(selected_syms) >= top_n:
                        selected_syms = selected_syms[:top_n-1]
                    selected_syms.append(must)
        # sembolden pair formatına
        pairs = []
        for sym in selected_syms:
            # BTCUSDT -> BTC/USDT ; genelde quote USDT 4 harf
            base = sym[:-4]
            pairs.append(f"{base}/USDT")
        # hacim sırasını koru (ticker sıralaması)
        # Eğer hiç sonuç yoksa fallback BTC/ETH
        if not pairs:
            pairs = ["BTC/USDT","ETH/USDT"]
            logger.warning("[universe] boş universe, fallback BTC/ETH")
        _UNIVERSE_CACHE.update({
            "pairs": pairs,
            "ts": now,
            "total_active": len(active),
            "after_volume": len(scored),
            "last_refresh": datetime.datetime.utcnow().isoformat()+"Z",
            "raw": selected_syms,
            "min_vol": min_vol,
            "top_n": top_n,
            "refresh": refresh,
            "duration": time.time()-t0
        })
        logger.info(f"[universe] refresh: active={len(active)} after_volume>={min_vol:.0f}={len(scored)} selected={len(pairs)} top_n={top_n} duration={(time.time()-t0):.2f}s symbols={','.join(selected_syms[:8])}...")
        return pairs
    except Exception as e:
        logger.error(f"[universe] keşif hatası: {e} — cache/fallback kullanılıyor")
        if _UNIVERSE_CACHE["pairs"]:
            return _UNIVERSE_CACHE["pairs"]
        # son çare: config whitelist veya BTC/ETH
        try:
            cfg = safe_config()
            wl = cfg.get("exchange", {}).get("pair_whitelist", [])
            if wl:
                return wl
        except:
            pass
        return ["BTC/USDT","ETH/USDT"]

def calculate_indicators(closes: list):
    """TA-Lib Wilder RSI(14) + SMA50/SMA200 — Freqtrade ile birebir."""
    if len(closes) < SMA_SLOW:
        return {"rsi": None, "sma50": None, "sma200": None}
    import numpy as np
    closes = np.array(closes, dtype=float)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.zeros(len(closes))
    avg_loss = np.zeros(len(closes))
    avg_gain[RSI_PERIOD] = np.mean(gains[:RSI_PERIOD])
    avg_loss[RSI_PERIOD] = np.mean(losses[:RSI_PERIOD])
    for i in range(RSI_PERIOD+1, len(closes)):
        avg_gain[i] = (avg_gain[i-1]*(RSI_PERIOD-1) + gains[i-1]) / RSI_PERIOD
        avg_loss[i] = (avg_loss[i-1]*(RSI_PERIOD-1) + losses[i-1]) / RSI_PERIOD
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    rsi_val = float(rsi[-1]) if len(rsi) > 0 else None
    sma50 = float(np.mean(closes[-SMA_FAST:])) if len(closes) >= SMA_FAST else None
    sma200 = float(np.mean(closes[-SMA_SLOW:])) if len(closes) >= SMA_SLOW else None
    return {"rsi": rsi_val, "sma50": sma50, "sma200": sma200}

def get_pair_data(pair: str, ticker_map: Optional[Dict[str, dict]] = None, open_map: Optional[Dict[str, int]] = None):
    """Freqtrade ile birebir aynı: TA-Lib Wilder RSI + SMA, son KAPALI mum üzerinden sinyal. ticker_map verilirse tek çağrı tasarrufu."""
    sym = pair.replace("/","")
    try:
        # ticker_map varsa onu kullan, yoksa tek çağrı (geri uyumluluk)
        if ticker_map is not None and sym in ticker_map:
            ticker = ticker_map[sym]
        else:
            with httpx.Client(timeout=8) as c:
                ticker = c.get(BINANCE_TICKER, params={"symbol": sym}).json()
        # klines her zaman fetch (5m, 250)
        with httpx.Client(timeout=8) as c:
            kl = c.get(BINANCE_KLINES, params={"symbol": sym, "interval":"5m", "limit":250}).json()
        if not isinstance(kl, list) or len(kl) < SMA_SLOW+1:
            return {"pair": pair, "error": "insufficient klines", "signal": "BEKLE"}
        kl_closed = kl[:-1]
        closes_all = [float(k[4]) for k in kl]
        closes = [float(k[4]) for k in kl_closed]
        cur = float(ticker.get("lastPrice", closes_all[-1] if closes_all else 0))
        def ch(n):
            if len(closes_all) > n and closes_all[-n-1] != 0:
                return (cur / closes_all[-n-1] - 1) * 100
            return None
        ind = calculate_indicators(closes)
        rsi = ind["rsi"]
        sma50 = ind["sma50"]
        sma200 = ind["sma200"]
        signal = "BEKLE"
        if rsi is not None and sma50 is not None and sma200 is not None:
            if rsi < RSI_BUY and sma50 > sma200:
                signal = "AL"
            elif rsi > RSI_SELL:
                signal = "SAT"
        try:
            last_close_ms = int(kl_closed[-1][6])
            last_candle = datetime.datetime.utcfromtimestamp(last_close_ms/1000).strftime("%H:%M:%S UTC")
            next_candle = datetime.datetime.utcfromtimestamp((last_close_ms+5*60*1000)/1000).strftime("%H:%M:%S UTC")
        except:
            last_candle = None
            next_candle = "sonraki 5m candle"
        # Pozisyon durumu — open_map varsa lookup, yoksa DB sorgu
        position = "YOK"
        try:
            if open_map is not None:
                cnt = open_map.get(pair, 0)
                if cnt and cnt>0:
                    position = f"VAR ({cnt})"
            else:
                con = db_connect()
                cur2 = con.cursor()
                cur2.execute("SELECT count(*) FROM trades WHERE pair=? AND is_open=1", (pair,))
                cnt = cur2.fetchone()[0]
                if cnt and cnt>0:
                    position = f"VAR ({cnt})"
                con.close()
        except:
            pass
        return {
            "pair": pair,
            "price": cur,
            "change_1m": None,
            "change_5m": ch(1),
            "change_15m": ch(3),
            "change_1h": ch(12),
            "change_24h": float(ticker.get("priceChangePercent", 0) or 0),
            "volume": float(ticker.get("volume", 0) or 0),
            "quoteVolume": float(ticker.get("quoteVolume", 0) or 0),
            "high": float(ticker.get("highPrice", 0) or 0),
            "low": float(ticker.get("lowPrice", 0) or 0),
            "rsi": round(rsi, 2) if rsi is not None else None,
            "sma50": round(sma50, 2) if sma50 is not None else None,
            "sma200": round(sma200, 2) if sma200 is not None else None,
            "signal": signal,
            "signal_source": "Freqtrade BaselineStrategy (TA-Lib Wilder RSI)",
            "last_evaluation": last_candle,
            "next_evaluation": next_candle,
            "position": position,
            "klines": [{"t": k[0], "c": float(k[4])} for k in kl[-72:]],
        }
    except Exception as e:
        return {"pair": pair, "price": binance_price(pair), "error": str(e)[:200], "klines": [], "signal": "BEKLE"}

def get_timeframe_stats(pair: str):
    """1S/1G/1H/1Ay/1Y kartları için — sadece görsel, trading'i etkilemez."""
    sym = pair.replace("/","")
    tfs = [
        ("1S", "1m", 60, "Son 1 saat"),
        ("1G", "1h", 24, "Son 24 saat"),
        ("1H", "4h", 42, "Son 1 hafta"),
        ("1Ay", "1d", 30, "Son 1 ay"),
        ("1Y", "1d", 365, "Son 1 yil"),
    ]
    out = []
    for label, interval, limit, desc in tfs:
        try:
            with httpx.Client(timeout=6) as c:
                kl = c.get(BINANCE_KLINES, params={"symbol": sym, "interval": interval, "limit": limit}).json()
                if not isinstance(kl, list) or len(kl) < 2:
                    out.append({"label": label, "desc": desc, "change": None, "klines": []})
                    continue
                closes = [float(k[4]) for k in kl]
                first = closes[0]
                last = closes[-1]
                change = (last / first - 1) * 100 if first else 0
                klines = [{"t": k[0], "c": float(k[4])} for k in kl[-30:]]
                out.append({"label": label, "desc": desc, "interval": interval, "change": round(change, 2), "klines": klines, "last": last, "first": first})
        except Exception as e:
            out.append({"label": label, "desc": desc, "change": None, "klines": [], "error": str(e)[:80]})
    return out

app = FastAPI(title="Zen-Genie Dashboard API", version="1.0.0-faz1-locked")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173","http://localhost:3000","http://127.0.0.1:5173","http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/market")
def market():
    """Tüm universe için sinyal hesapla — paralel, gerçek taranan sayı loglanır."""
    scan_start = time.time()
    pairs = get_universe()
    # tek çağrı ile tüm ticker'ları al (rate-limit dostu)
    try:
        tickers = _fetch_tickers_map()
    except Exception as e:
        logger.warning(f"[market] ticker map fetch failed: {e}")
        tickers = {}
    # open trades map — tek DB sorgu
    open_map: Dict[str,int] = {}
    try:
        con = db_connect()
        cur = con.cursor()
        # group by pair
        cur.execute("SELECT pair, count(*) as cnt FROM trades WHERE is_open=1 GROUP BY pair")
        for row in cur.fetchall():
            open_map[row["pair"]] = int(row["cnt"])
        con.close()
    except:
        pass
    # paralel sinyal hesabi
    data: List[dict] = []
    max_workers = min(12, len(pairs)) or 4
    start_fetch = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut2pair = {ex.submit(get_pair_data, p, tickers, open_map): p for p in pairs}
        for fut in concurrent.futures.as_completed(fut2pair):
            p = fut2pair[fut]
            try:
                res = fut.result(timeout=15)
                # pair alanı yoksa ekle
                if "pair" not in res:
                    res["pair"] = p
                data.append(res)
            except Exception as e:
                data.append({"pair": p, "error": str(e)[:200], "signal": "BEKLE", "klines": []})
    # orijinal sırayı koru (universe sort = volume desc)
    order = {p:i for i,p in enumerate(pairs)}
    data.sort(key=lambda x: order.get(x.get("pair",""), 999))
    buys = sum(1 for d in data if d.get("signal")=="AL")
    sells = sum(1 for d in data if d.get("signal")=="SAT")
    waits = len(data)-buys-sells
    duration = time.time() - scan_start
    # log: kaç tarandı, kaç BUY — gereksinim
    logger.info(f"[scan] taranan={len(pairs)} AL={buys} SAT={sells} BEKLE={waits} süre={duration:.2f}s active={_UNIVERSE_CACHE.get('total_active')} after_volume={_UNIVERSE_CACHE.get('after_volume')} min_vol={_UNIVERSE_CACHE.get('min_vol')}")
    return {
        "pairs": data,
        "count": len(pairs),
        "watched": f"İzlenen Pariteler: {len(pairs)}",
        "scanned": len(pairs),
        "buys": buys,
        "sells": sells,
        "waits": waits,
        "total_active": _UNIVERSE_CACHE.get("total_active"),
        "after_volume": _UNIVERSE_CACHE.get("after_volume"),
        "last_refresh": _UNIVERSE_CACHE.get("last_refresh"),
        "min_volume": _UNIVERSE_CACHE.get("min_vol"),
        "top_n": _UNIVERSE_CACHE.get("top_n"),
        "scan_duration": round(duration,2),
        # BUY listesini ayrıca döndür — dashboard kolay filtrelesin
        "buy_pairs": [d["pair"] for d in data if d.get("signal")=="AL"],
    }

@app.get("/api/market/timeframes")
def market_timeframes(limit: int = Query(6, ge=1, le=30)):
    """Çoklu zaman dilimi kartları — görsel. Varsayılan 6 parite (yük önleme). Paralel fetch."""
    pairs = get_universe()
    pairs = pairs[:limit]
    # paralel: her parite için zaman dilimi istatistiğini ayrı thread'de çek
    def _wrap(p):
        return {"pair": p, "timeframes": get_timeframe_stats(p)}
    res: List[dict] = []
    max_w = min(6, len(pairs)) or 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as ex:
        fut2pair = {ex.submit(_wrap, p): p for p in pairs}
        # order korumak için dict
        tmp: Dict[str, dict] = {}
        for fut in concurrent.futures.as_completed(fut2pair):
            p = fut2pair[fut]
            try:
                tmp[p] = fut.result(timeout=20)
            except Exception as e:
                tmp[p] = {"pair": p, "timeframes": [], "error": str(e)[:200]}
        # orijinal volum sırasını koru
        res = [tmp[p] for p in pairs if p in tmp]
    return {"pairs": res, "count": len(res), "universe_total": len(get_universe())}

@app.get("/api/universe")
def universe():
    """Universe debug/inspect — hangi pariteler izleniyor, hangi filtre aktif."""
    pairs = get_universe()
    top_n, min_vol, refresh = _read_universe_config()
    return {
        "pairs": pairs,
        "count": len(pairs),
        "watched": f"İzlenen Pariteler: {len(pairs)}",
        "config": {"top_n": top_n, "min_volume": min_vol, "refresh_period": refresh, "quote": "USDT", "stable_blacklist": sorted(list(_STABLE_BLACKLIST))},
        "cache": {k: _UNIVERSE_CACHE.get(k) for k in ["total_active","after_volume","last_refresh","duration","min_vol","top_n","refresh"]},
        "sma": {"fast": SMA_FAST, "slow": SMA_SLOW, "rsi_buy": RSI_BUY, "rsi_sell": RSI_SELL, "note": "BaselineStrategy değişmedi"},
    }

# ── helpers ──
def safe_config():
    try:
        j = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        safe = {k: j.get(k) for k in ["max_open_trades","stake_currency","stake_amount","dry_run","dry_run_wallet","trading_mode","exchange","pairlists","bot_name","timeframe","strategy"]}
        if "exchange" in j:
            safe["exchange"] = {"name": j["exchange"].get("name"), "pair_whitelist": j["exchange"].get("pair_whitelist",[])}
        # pairlists içinde VolumePairList varsa onu da expose et
        if "pairlists" in j:
            safe["pairlists"] = j["pairlists"]
            # universe özeti
            try:
                top_n, min_vol, refresh = _read_universe_config()
                safe["universe"] = {"top_n": top_n, "min_volume": min_vol, "refresh": refresh}
            except:
                pass
        safe["live_trading"] = "DISABLED"
        return safe
    except Exception as e:
        return {"error": str(e), "live_trading":"DISABLED"}

def db_connect():
    if not DB_PATH.exists():
        raise HTTPException(503, f"DB not found: {DB_PATH}")
    import shutil, tempfile
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro&nolock=1", uri=True, check_same_thread=False, timeout=2)
        con.execute("SELECT 1 FROM trades LIMIT 1")
        con.row_factory = sqlite3.Row
        return con
    except Exception:
        pass
    try:
        tmp = pathlib.Path(tempfile.gettempdir()) / f"zen-genie-{DB_PATH.name}.ro.sqlite"
        try:
            src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=2)
            dst = sqlite3.connect(str(tmp))
            src.backup(dst)
            dst.close(); src.close()
        except Exception:
            shutil.copy2(DB_PATH, tmp)
        con = sqlite3.connect(str(tmp), check_same_thread=False, timeout=2)
        con.row_factory = sqlite3.Row
        return con
    except Exception as e:
        raise HTTPException(503, f"DB open failed: {e}")

def docker_status():
    try:
        out = subprocess.check_output(shlex.split("docker inspect -f {{.State.Status}} ai-trader-dryrun"), text=True, stderr=subprocess.STDOUT, timeout=3).strip()
        running = subprocess.check_output(shlex.split("docker inspect -f {{.State.Running}} ai-trader-dryrun"), text=True, timeout=3).strip()=="true"
        started = subprocess.check_output(shlex.split("docker inspect -f {{.State.StartedAt}} ai-trader-dryrun"), text=True, timeout=3).strip()
        return {"status": out, "running": running, "started_at": started}
    except Exception as e:
        try:
            if DB_PATH.exists():
                age = time.time() - DB_PATH.stat().st_mtime
                if age < 600:
                    started = ""
                    try: started = datetime.datetime.fromtimestamp(STARTED_AT.stat().st_mtime).isoformat()
                    except: pass
                    return {"status":"running (fallback)","running":True,"started_at":started,"note":"docker CLI yok — DB fallback"}
            return {"status":"unknown","running": False if "No such object" in str(e) else True, "error":str(e)[:200]}
        except Exception as e2:
            return {"status":"unknown","running":False,"error":str(e)[:200]}

def last_heartbeat():
    try:
        logs = subprocess.check_output(shlex.split("docker logs --tail 200 ai-trader-dryrun"), text=True, stderr=subprocess.STDOUT, timeout=3)
        m = list(re.finditer(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*heartbeat.*RUNNING", logs, re.I))
        if m: return m[-1].group(1)
        lines = [l for l in logs.splitlines() if l.strip()]
        if lines:
            mm = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", lines[-1])
            if mm: return mm.group(1)
        return None
    except:
        try:
            if DB_PATH.exists():
                return datetime.datetime.fromtimestamp(DB_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except: pass
        return None

def binance_price(pair="BTCUSDT"):
    sym = pair.replace("/","")
    try:
        with httpx.Client(timeout=5) as c:
            r = c.get(BINANCE_PRICE, params={"symbol": sym})
            r.raise_for_status()
            return float(r.json()["price"])
    except: return None

def wallet_history():
    try:
        con=db_connect()
        cur=con.cursor()
        cur.execute("SELECT * FROM wallet_history ORDER BY id DESC LIMIT 1")
        row=cur.fetchone()
        con.close()
        if row: return dict(row)
    except: pass
    return None

# ── endpoints ──
@app.get("/api/status")
def status():
    cfg = safe_config()
    dock = docker_status()
    hb = last_heartbeat()
    strategy = "BaselineStrategy"
    uptime = None
    try:
        started = datetime.datetime.fromisoformat(dock.get("started_at","").replace("Z","+00:00"))
        uptime = (datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()
    except: pass
    # universe pair sayısı
    try:
        uni = get_universe()
        uni_count = len(uni)
    except:
        uni_count = len(cfg.get("exchange",{}).get("pair_whitelist",[]))
    return {
        "bot_status": "RUNNING" if dock.get("running") else "STOPPED",
        "container_status": dock.get("status"),
        "heartbeat": hb,
        "uptime_seconds": uptime,
        "strategy": strategy,
        "trading_mode": "DRY-RUN",
        "exchange": cfg.get("exchange",{}).get("name","binance"),
        "pairs": get_universe(),
        "pairs_count": uni_count,
        "live_trading": "DISABLED",
        "config_safe": cfg,
        "universe": {"count": uni_count, "last_refresh": _UNIVERSE_CACHE.get("last_refresh")},
    }

@app.get("/api/portfolio")
def portfolio():
    cfg = safe_config()
    starting = float(cfg.get("dry_run_wallet",10))
    con=db_connect()
    cur=con.cursor()
    cur.execute("SELECT COALESCE(SUM(close_profit_abs),0) as realized, COUNT(*) as cnt FROM trades WHERE is_open=0")
    r=cur.fetchone()
    realized = float(r["realized"] or 0)
    cur.execute("SELECT pair, amount, open_rate, stake_amount FROM trades WHERE is_open=1")
    opens = [dict(row) for row in cur.fetchall()]
    con.close()
    btc_price = binance_price("BTC/USDT") or 0
    unreal=0.0
    btc_hold=0.0
    for o in opens:
        cur_price = binance_price(o["pair"]) or o["open_rate"]
        try:
            unreal += (cur_price - o["open_rate"])*float(o["amount"])
            if o["pair"].startswith("BTC"): btc_hold+=float(o["amount"])
        except: pass
    current_value = starting + realized + unreal
    total_pnl = realized + unreal
    # capital rezerv bilgisi ekle (strateji bağımsız)
    capital_info = None
    try:
        if capital_m:
            capital_info = capital_m.compute_capital_view(auto_harvest_check=False)
    except Exception:
        capital_info = None
    return {
        "starting_balance": starting,
        "current_balance": current_value,
        "current_value": current_value,
        "realized_pnl": realized,
        "unrealized_pnl": unreal,
        "total_pnl": total_pnl,
        "return_pct": (total_pnl/starting*100) if starting else 0,
        "btc_holdings": btc_hold,
        "btc_price": btc_price,
        "open_trades_count": len(opens),
        "capital": capital_info,  # CORE/RESERVE ayrımı için
    }

@app.get("/api/capital")
def capital_view():
    """CORE CAPITAL + RESERVE — strateji bağımsız risk katmanı. DB realized + config core + state reserve."""
    if capital_m is None:
        raise HTTPException(503, "capital module not available")
    try:
        view = capital_m.compute_capital_view(auto_harvest_check=True)
        return view
    except Exception as e:
        logger.error(f"capital view error: {e}")
        raise HTTPException(500, str(e))

@app.post("/api/capital/harvest")
def capital_harvest(force: bool = Query(False, description="period/threshold bypass"), amount: Optional[float] = Query(None, description="manuel harvest miktarı, boşsa ratio ile hesaplanır")):
    """Kârın koruma payını rezerve aktar — strateji/signal'den bağımsız, sadece muhasebe. Dry-run sanal."""
    if capital_m is None:
        raise HTTPException(503, "capital module not available")
    try:
        # force bypass period/threshold
        if force and amount is None:
            # force harvest pending amount
            res = capital_m.harvest(manual=True)
        elif amount is not None:
            res = capital_m.harvest(manual=True, force_amount=amount)
        else:
            # normal harvest (period/threshold kontrollü)
            res = capital_m.harvest(manual=False)
            # eğer period_not_due ise ve force değilse, manual=False ile 0 döner — kullanıcı manuel isterse force=true kullanmalı
            if res.get("harvested", 0) == 0 and not force:
                # otomatik 0 ise bilgilendir, ama yine de view döndür
                pass
        return res
    except Exception as e:
        logger.error(f"capital harvest error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/capital/history")
def capital_history(limit: int = Query(20, ge=1, le=100)):
    if capital_m is None:
        raise HTTPException(503, "capital module not available")
    try:
        state = capital_m.load_state()
        hist = state.get("harvest_history", [])[-limit:]
        return {"history": hist, "count": len(hist), "reserve_balance": state.get("reserve_balance", 0)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/open_positions")
def open_positions():
    """AÇIK POZİSYONLAR — doğrudan Freqtrade DB (trades is_open=1) + Binance güncel fiyat. Dashboard tahmini değil."""
    cfg = safe_config()
    starting = float(cfg.get("dry_run_wallet", 10))
    try:
        tradable_ratio = float(cfg.get("tradable_balance_ratio", 0.99))
    except:
        tradable_ratio = 0.99
    max_open = int(cfg.get("max_open_trades", 3))
    # fees / stake logic: DB'deki stake_amount doğrudan kullanılır
    try:
        con = db_connect()
        cur = con.cursor()
        cur.execute("SELECT id, pair, amount, open_rate, stake_amount, open_date, fee_open, fee_close, strategy, enter_tag, is_short FROM trades WHERE is_open=1 ORDER BY open_date ASC")
        rows = [dict(r) for r in cur.fetchall()]
        # dinamik wallet: Freqtrade gerçek bakiye mantığı = starting + realized (portfolio ile tutarlı)
        try:
            cur.execute("SELECT COALESCE(SUM(close_profit_abs),0) FROM trades WHERE is_open=0")
            realized = float(cur.fetchone()[0] or 0)
        except:
            realized = 0.0
        con.close()
    except Exception as e:
        raise HTTPException(500, f"DB trades read failed: {e}")
    # güncel fiyatları tek çağrıda al (rate-limit dostu)
    try:
        tickers = _fetch_tickers_map()
    except:
        tickers = {}
    positions: List[Dict[str, Any]] = []
    total_invested = 0.0
    total_value = 0.0
    total_unrealized = 0.0
    for r in rows:
        pair = r["pair"]
        sym = pair.replace("/", "")
        amount = float(r["amount"] or 0)
        open_rate = float(r["open_rate"] or 0)
        stake = float(r["stake_amount"] or (amount * open_rate))
        base_ccy = pair.split("/")[0] if "/" in pair else ""
        # güncel fiyat Binance ticker'dan
        t = tickers.get(sym, {})
        try:
            current_price = float(t.get("lastPrice", open_rate)) if t else binance_price(pair) or open_rate
        except:
            current_price = open_rate
        # hesaplamalar — Freqtrade mantığı: value = amount * current, P/L = (current-open)*amount (fee hariç, net için fee eklenebilir)
        try:
            value = amount * current_price
            unrealized_abs = (current_price - open_rate) * amount
            unrealized_pct = ((current_price / open_rate - 1) * 100) if open_rate else 0
        except:
            value = stake
            unrealized_abs = 0
            unrealized_pct = 0
        # süre
        duration_s = None
        try:
            od = datetime.datetime.fromisoformat(r["open_date"].replace("Z", ""))
            duration_s = (datetime.datetime.now() - od).total_seconds()
        except:
            pass
        total_invested += stake
        total_value += value
        total_unrealized += unrealized_abs
        # side — BaselineStrategy can_short=False → tümü LONG, ama DB is_short'e göre
        is_short = bool(r.get("is_short")) if r.get("is_short") is not None else False
        side = "SHORT" if is_short else "LONG"
        positions.append({
            "id": r["id"],
            "pair": pair,
            "base_currency": base_ccy,
            "amount": amount,
            "open_rate": open_rate,
            "current_price": current_price,
            "stake_amount": stake,
            "open_date": r["open_date"],
            "value": value,
            "unrealized_abs": unrealized_abs,
            "unrealized_pct": unrealized_pct,
            "duration_seconds": duration_s,
            "fee_open": r.get("fee_open"),
            "strategy": r.get("strategy"),
            "enter_tag": r.get("enter_tag"),
            "is_open": 1,
            "status": "AÇIK",
            "side": side,
            "is_short": is_short,
        })
    wallet = starting + realized
    tradable = wallet * tradable_ratio
    free_balance = tradable - total_invested
    # wallet - invested de göster (kullanıcı free'yi wallet bazlı görmek isteyebilir)
    free_simple = wallet - total_invested
    return {
        "positions": positions,
        "count": len(positions),
        "summary": {
            "wallet": wallet,
            "starting_balance": starting,
            "realized_profit": realized,
            "tradable_balance": tradable,
            "tradable_ratio": tradable_ratio,
            "total_invested": total_invested,
            "total_value": total_value,
            "free_balance": free_balance,
            "free_balance_simple": free_simple,
            "total_unrealized_abs": total_unrealized,
            "total_unrealized_pct": (total_unrealized / total_invested * 100) if total_invested else 0,
            "open_count": len(positions),
            "max_open_trades": max_open,
            "open_label": f"{len(positions)}/{max_open}",
        },
    }

@app.get("/api/price")
def price(pair: str = Query("BTC/USDT")):
    sym = pair.replace("/","")
    try:
        with httpx.Client(timeout=6) as c:
            ticker = c.get(BINANCE_TICKER, params={"symbol": sym}).json()
            kl = c.get(BINANCE_KLINES, params={"symbol": sym, "interval":"5m", "limit":72}).json()
            closes = [float(k[4]) for k in kl] if isinstance(kl,list) else []
            cur = float(ticker.get("lastPrice", closes[-1] if closes else 0))
            def ch(n):
                if len(closes)>n and closes[-n-1]!=0:
                    return (cur/closes[-n-1]-1)*100
                return None
            return {
                "pair": pair,
                "price": cur,
                "change_1m": None,
                "change_5m": ch(1),
                "change_15m": ch(3),
                "change_1h": ch(12),
                "change_24h": float(ticker.get("priceChangePercent",0)),
                "volume": float(ticker.get("volume",0)),
                "high": float(ticker.get("highPrice",0)),
                "low": float(ticker.get("lowPrice",0)),
                "klines": [{"t":k[0],"o":float(k[1]),"h":float(k[2]),"l":float(k[3]),"c":float(k[4]),"v":float(k[5])} for k in kl[-72:]] if isinstance(kl,list) else [],
            }
    except Exception as e:
        return {"pair": pair, "price": binance_price(pair), "error": str(e), "klines":[]}

@app.get("/api/trades")
def trades(status: str = Query("all", enum=["all","open","closed"]), limit: int=100, pair: Optional[str]=None):
    con=db_connect(); cur=con.cursor()
    q="SELECT id,pair,is_open,amount,open_rate,close_rate,open_date,close_date,close_profit,close_profit_abs,fee_open,fee_close,exit_reason,strategy,enter_tag FROM trades"
    wh=[]
    if status=="open": wh.append("is_open=1")
    elif status=="closed": wh.append("is_open=0")
    if pair: wh.append(f"pair='{pair}'")
    if wh: q+=" WHERE "+" AND ".join(wh)
    q+=" ORDER BY id DESC LIMIT ?"
    cur.execute(q, (limit,))
    rows=[dict(r) for r in cur.fetchall()]
    for r in rows:
        try:
            od=datetime.datetime.fromisoformat(r["open_date"].replace("Z",""))
            cd=datetime.datetime.fromisoformat(r["close_date"].replace("Z","")) if r["close_date"] else None
            r["duration_seconds"]=(cd-od).total_seconds() if cd else (datetime.datetime.now()-od).total_seconds()
        except: r["duration_seconds"]=None
        r["fee"] = (r["fee_open"] or 0)+(r["fee_close"] or 0)
        r["side"]="LONG"
        r["gross_pnl"]=r["close_profit_abs"]
        r["net_pnl"]=r["close_profit_abs"]
    con.close()
    return {"trades": rows, "count": len(rows)}

@app.get("/api/performance")
def performance():
    con=db_connect(); cur=con.cursor()
    cur.execute("SELECT close_date, close_profit_abs, close_profit FROM trades WHERE is_open=0 ORDER BY close_date ASC")
    rows=[dict(r) for r in cur.fetchall()]
    con.close()
    start=10.0
    try: start=float(safe_config().get("dry_run_wallet",10))
    except: pass
    eq=[]; cum=0; peak=start; dd=[]
    for r in rows:
        cum+=float(r["close_profit_abs"] or 0)
        val=start+cum
        eq.append({"date":r["close_date"], "equity":val, "cum_pnl":cum})
        peak=max(peak,val)
        dd.append({"date":r["close_date"], "drawdown": (val-peak)/peak*100 if peak else 0})
    if rows:
        profits=[float(r["close_profit_abs"] or 0) for r in rows]
        wins=[p for p in profits if p>0]; losses=[p for p in profits if p<=0]
        win_rate=len(wins)/len(rows) if rows else 0
        avg_win=sum(wins)/len(wins) if wins else 0
        avg_loss=sum(losses)/len(losses) if losses else 0
        gross_w=sum(wins); gross_l=abs(sum(losses)) if losses else 0
        pf=gross_w/gross_l if gross_l else (float("inf") if gross_w>0 else 0)
        total_fees=0
        max_dd=min([d["drawdown"] for d in dd]) if dd else 0
        import math, statistics, datetime
        # DÜZELTME 2026-09-04: Eski per-trade `close_profit` +365 (6.02) şişirme.
        # Doğru: günlük return üzerinden annualize (365). Trade frekansı ≠ günlük.
        daily_rets=[]
        try:
            daily_map={}
            for r in rows:
                try:
                    d=r["close_date"][:10]
                    daily_map[d]=daily_map.get(d,0)+float(r["close_profit"] or 0)
                except: pass
            if daily_map:
                dates=sorted(daily_map.keys())
                d0=datetime.date.fromisoformat(dates[0])
                d1=datetime.date.fromisoformat(dates[-1])
                cur=d0
                while cur <= d1:
                    daily_rets.append(daily_map.get(cur.isoformat(), 0.0))
                    cur+=datetime.timedelta(days=1)
        except:
            daily_rets=[]
        sharpe=None; sortino=None
        if len(daily_rets)>2 and statistics.pstdev(daily_rets)!=0:
            try:
                ann=365
                sharpe=float((sum(daily_rets)/len(daily_rets))/(statistics.pstdev(daily_rets) or 1)*math.sqrt(ann))
                downside=[r for r in daily_rets if r<0]
                if downside and len(downside)>1 and statistics.pstdev(downside)!=0:
                    sortino=float((sum(daily_rets)/len(daily_rets))/(statistics.pstdev(downside))*math.sqrt(ann))
            except: pass
        # Eski per-trade değeri artık güvenilir değil (6.02 şişmişti) — fallback yok, daily boşsa None kalır
        stats={"total_trades":len(rows),"winning":len(wins),"losing":len(losses),"win_rate":win_rate,"profit_factor":pf,"avg_win":avg_win,"avg_loss":avg_loss,"largest_win":max(profits) if profits else 0,"largest_loss":min(profits) if profits else 0,"avg_trade":sum(profits)/len(profits) if profits else 0,"total_fees":total_fees,"max_drawdown":max_dd,"sharpe":sharpe,"sortino":sortino,"turnover":len(rows)}
    else:
        stats={"total_trades":0,"winning":0,"losing":0,"win_rate":None,"profit_factor":None,"avg_win":None,"avg_loss":None,"largest_win":None,"largest_loss":None,"avg_trade":None,"total_fees":0,"max_drawdown":0,"sharpe":None,"sortino":None,"turnover":0}
        dd=[]
    daily={}
    for r in rows:
        try:
            d=r["close_date"][:10]
            daily[d]=daily.get(d,0)+float(r["close_profit_abs"] or 0)
        except: pass
    daily_list=[{"date":k,"pnl":v} for k,v in sorted(daily.items())]
    return {"equity":eq, "drawdown":dd, "daily":daily_list, "stats":stats, "raw_count":len(rows)}

@app.get("/api/experiment")
def experiment():
    locked=False; started=None; elapsed=None
    try:
        txt=PHASE_LOCK.read_text(encoding="utf-8") if PHASE_LOCK.exists() else ""
        locked="LOCK" in txt
    except: txt=""
    try:
        if STARTED_AT.exists():
            started=STARTED_AT.read_text(encoding="utf-8").strip()
            mtime=STARTED_AT.stat().st_mtime
            elapsed=time.time()-mtime
    except: pass
    required=7*86400
    pct=min(100, (elapsed/required*100) if elapsed else 0)
    ver={"passed":8,"total":9}
    try:
        import subprocess as sp, shlex
        out=sp.check_output(shlex.split("py -3 scripts/verify_dryrun.py"), text=True, stderr=subprocess.STDOUT, cwd=str(ROOT))
        m=re.search(r"(\d+)/(\d+) ge", out)
        if m: ver={"passed":int(m.group(1)), "total":int(m.group(2))}
    except: pass
    return {
        "phase":"PHASE 1 — DRY RUN",
        "status":"RUNNING",
        "locked": locked,
        "lock_text": "Phase 1 → LOCKED" if locked else "UNLOCKED",
        "started_at": started,
        "elapsed_seconds": elapsed,
        "elapsed_human": f"{int(elapsed//86400)}d {int((elapsed%86400)//3600)}h {int((elapsed%3600)//60)}m" if elapsed else None,
        "required_seconds": required,
        "progress_pct": pct,
        "observation": f"{elapsed/86400:.2f} / 7 days" if elapsed else "0 / 7 days",
        "verification": ver,
    }

@app.get("/api/health")
def health():
    dock=docker_status()
    db_ok=DB_PATH.exists()
    db_write=None
    if db_ok:
        try: db_write=datetime.datetime.fromtimestamp(DB_PATH.stat().st_mtime).isoformat()
        except: pass
    hb=last_heartbeat()
    api_ok=True
    try:
        with httpx.Client(timeout=3) as c:
            c.get(BINANCE_PRICE, params={"symbol":"BTCUSDT"}).raise_for_status()
    except: api_ok=False
    disk=psutil.disk_usage(str(ROOT)).percent if hasattr(psutil,"disk_usage") else None
    mem=psutil.virtual_memory().percent if hasattr(psutil,"virtual_memory") else None
    cpu=psutil.cpu_percent(interval=0.5) if hasattr(psutil,"cpu_percent") else None
    up=None
    try: up=time.time()-psutil.boot_time()
    except: pass
    def level(ok): return "Healthy" if ok else "Error"
    def warn_level(v, thr):
        if v is None: return "Healthy"
        return "Warning" if v>thr else "Healthy"
    uni_count = len(_UNIVERSE_CACHE.get("pairs",[])) or len(get_universe())
    return {
        "items":[
            {"name":"Docker container","status": level(dock.get("running")), "detail": dock.get("status")},
            {"name":"Freqtrade heartbeat","status": level(hb is not None), "detail": hb or "missing"},
            {"name":"SQLite database","status": level(db_ok), "detail": str(DB_PATH) + (f" last:{db_write}" if db_write else "")},
            {"name":"Database last write","status": level(db_write is not None), "detail": db_write},
            {"name":"API connection","status": level(api_ok), "detail":"Binance REST"},
            {"name":"Market universe","status": level(api_ok and uni_count>0), "detail": f"{uni_count} USDT pairs (VolumePairList TOP {uni_count})"},
            {"name":"Market data","status": level(api_ok), "detail": f"Universe {uni_count} pairs — BTC/ETH dahil"},
            {"name":"Disk usage","status": warn_level(disk,85), "detail": f"{disk:.1f}%" if disk is not None else "N/A", "value":disk},
            {"name":"Memory usage","status": warn_level(mem,85), "detail": f"{mem:.1f}%" if mem is not None else "N/A", "value":mem},
            {"name":"CPU usage","status": warn_level(cpu,85), "detail": f"{cpu:.1f}%" if cpu is not None else "N/A", "value":cpu},
            {"name":"Uptime","status":"Healthy","detail": f"{up/3600:.1f}h" if up else "N/A"},
        ]
    }

@app.get("/api/logs")
def logs(lines: int=200, level: str=Query("all", enum=["all","error","warning","info"])):
    try:
        raw=subprocess.check_output(shlex.split(f"docker logs --tail {lines} ai-trader-dryrun"), text=True, stderr=subprocess.STDOUT, timeout=4)
        if level!="all":
            raw="\n".join([l for l in raw.splitlines() if level.upper() in l.upper()])
        if raw.strip():
            return {"logs": raw.splitlines()[-lines:], "count": len(raw.splitlines())}
    except Exception as e:
        pass
    try:
        raw2 = subprocess.check_output(shlex.split(f"docker logs --tail {lines} ai-trader-dryrun"), text=True, stderr=subprocess.STDOUT, timeout=4, cwd=str(ROOT))
        if raw2.strip():
            if level!="all": raw2="\n".join([l for l in raw2.splitlines() if level.upper() in l.upper()])
            return {"logs": raw2.splitlines()[-lines:], "count": len(raw2.splitlines())}
    except: pass
    try:
        files=list(LOG_DIR.glob("*.log"))
        if files:
            txt=files[0].read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:]
            if level!="all": txt=[l for l in txt if level.upper() in l.upper()]
            return {"logs": txt, "count": len(txt)}
    except: pass
    return {"logs":[f"[fallback] logs via docker unavailable — container {docker_status().get('status')} — check docker ps on host"], "count":1}

@app.get("/api/alerts")
def alerts():
    h=health(); s=status(); ex=experiment()
    alerts=[]
    now=datetime.datetime.now().isoformat()
    if s["bot_status"]!="RUNNING":
        alerts.append({"time":now,"level":"error","msg":"Bot stopped"})
    if not any(i["status"]=="Healthy" for i in h["items"] if i["name"]=="Freqtrade heartbeat"):
        alerts.append({"time":now,"level":"warning","msg":"Heartbeat missing"})
    if not DB_PATH.exists():
        alerts.append({"time":now,"level":"error","msg":"Database unavailable"})
    try:
        con=db_connect(); cur=con.cursor()
        cur.execute("SELECT id, pair, open_date FROM trades ORDER BY id DESC LIMIT 1")
        r=cur.fetchone()
        if r: alerts.append({"time":r["open_date"],"level":"info","msg":f"Last trade {r['pair']} #{r['id']}"})
        con.close()
    except: pass
    if ex.get("elapsed_seconds",0) and ex["elapsed_seconds"]>7*86400:
        alerts.append({"time":now,"level":"info","msg":"7-day observation complete — ready for Phase 2"})
    perf=performance()
    dd=perf["stats"].get("max_drawdown")
    if dd is not None and dd < -15:
        alerts.append({"time":now,"level":"warning","msg":f"Large drawdown {dd:.1f}%"})
    # universe BUY alerts
    try:
        m = market()
        if m.get("buys",0) > 0:
            alerts.append({"time": now, "level":"info","msg": f"{m['buys']} BUY sinyali ({', '.join(m['buy_pairs'][:5])}) — max_open_trades={s['config_safe'].get('max_open_trades',3)}"})
    except: pass
    return {"alerts": alerts[:20]}

@app.post("/api/control/{action}")
def control(action: str):
    if action not in ("start","stop","restart","pause","resume"):
        raise HTTPException(400,"unknown action")
    if (ROOT/"config"/"freqtrade.live.json").exists():
        raise HTTPException(403,"LIVE TRADING DISABLED")
    try:
        if action=="start": out=subprocess.check_output(shlex.split("docker compose up -d"), text=True, cwd=str(ROOT))
        elif action=="stop": out=subprocess.check_output(shlex.split("docker compose stop freqtrade"), text=True, cwd=str(ROOT))
        elif action=="restart": out=subprocess.check_output(shlex.split("docker compose restart freqtrade"), text=True, cwd=str(ROOT))
        elif action in ("pause","resume"):
            out="pause/resume via API not configured — use stop/start"
        return {"ok":True, "output": out[-1000:]}
    except Exception as e:
        raise HTTPException(500,str(e))

@app.get("/")
def root(): return {"ok":True, "service":"zen-genie-dashboard", "phase":"1-locked", "live_trading":"DISABLED"}
