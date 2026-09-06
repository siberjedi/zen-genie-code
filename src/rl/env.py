"""Faz 4.1 — Hardened TradingEnv (eğitim bu görevde ÇALIŞTIRILMADI).

ENV_VERSION 4.1.0. v4.0'a göre farklar (audit B-sınıfı bulgular):
- Reward: realized-only yerine log(portfolio_t / portfolio_{t-1}); portfolio
  mark-to-market (mid close, slippage YOK) + fee/slippage DAHİL cash hesabı.
  Ek shaping YOK (drawdown/turnover penalty yok — protokol değişikliği olurdu).
- Slippage: LOCKED 5 bps, adverse yönde (alırken +, satarken -). Zero-slippage YOK.
- Obs: market penceresi + position geçmişi + equity geçmişi (hepsi nedensel).
- Episode sonu: açık pozisyon ZORUNLU likide edilir (fee/slippage'li, reward'a
  exact yansır). Sessiz düşürme YASAK.
- Guard'lar: invalid action sayacı, position invariant, bankruptcy truncate,
  turnover/fee sayaçları (log amaçlı, shaping değil).
- All-in tek-slot long korunuyor (belgeli limitasyon; B10: protokol multi-pair
  şart koşmuyor, değişiklik yapılmadı). SL/ROI YOK (baseline kuralları
  OTOMATİK EKLENMEDİ — talimat gereği).
"""
import gymnasium as gym
import numpy as np
import pandas as pd

ENV_VERSION = "4.3.0-h1"
REQUIRED_COLS = ("date", "open", "high", "low", "close")

BUY, SELL, HOLD = 1, 2, 0


class PositionInconsistencyError(RuntimeError):
    """amount>0 ⟺ pozisyon-açık invariantı bozuldu."""


class TradingEnv(gym.Env):
    """Cash-bazlı, all-in, long-only, tek-slot trading env (spot, 1x zımni)."""
    metadata = {"render_modes": ["human"]}

    def __init__(self, df: pd.DataFrame, fee: float = 0.001,
                 slippage_bps: float = 5, window: int = 30,
                 initial_capital: float = 100.0, price_col: str = "close",
                 reward_mode: str = "mtm"):
        super().__init__()
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"eksik OHLC kolonları: {missing}")
        if price_col not in df.columns:
            raise ValueError(f"price_col yok: {price_col}")
        if not (0 <= fee < 1):
            raise ValueError(f"fee aralık dışı: {fee}")
        if slippage_bps < 0:
            raise ValueError(f"slippage negatif: {slippage_bps}")
        if window < 1:
            raise ValueError(f"window>=1 olmalı: {window}")
        if initial_capital <= 0:
            raise ValueError("initial_capital>0 olmalı")
        if reward_mode not in ("mtm", "realized"):
            raise ValueError(f"reward_mode mtm/realized olmalı: {reward_mode}")
        self.price_col = price_col
        self.reward_mode = reward_mode
        self.cost_basis = None
        self.df = df.reset_index(drop=True)
        if len(self.df) <= window:
            raise ValueError(f"veri ({len(self.df)}) window'dan ({window}) uzun olmalı")
        self.fee = float(fee)
        self.slip = float(slippage_bps) / 10000.0
        self.window = int(window)
        self.initial_capital = float(initial_capital)
        self.market_cols = [c for c in self.df.columns
                            if c not in ("date", "open", "high", "low", self.price_col)]
        if not self.market_cols:
            raise ValueError("obs için numerik kolon yok (close dahil)")
        n_feat = len(self.market_cols) + 2  # + position, equity_norm
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(window, n_feat), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(3)  # 0 hold, 1 buy, 2 sell
        self.reset()

    # -- state --
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.cash = self.initial_capital
        self.amount = 0.0
        self.entry_price = None
        self.t = self.window
        self._prev_pf = self.initial_capital
        self.pos_hist = [0] * self.window
        self.eq_hist = [self.initial_capital] * self.window
        self.peak = self.initial_capital
        self.invalid_actions = 0
        self.entries = 0
        self.roundtrips = 0
        self.fees_paid = 0.0
        self.forced_close = False
        self.cost_basis = None
        return self._obs(), {}

    def _check_invariant(self):
        long = self.amount > 0
        if long == (self.cash > 0) and (self.amount > 0 or self.cash > 0):
            # all-in: iki taraf da pozitif olamaz; ikisi de sıfır olamaz (bankrupt hariç)
            raise PositionInconsistencyError(
                f"cash={self.cash} amount={self.amount}")
        if (self.amount > 0) != (self.entry_price is not None):
            raise PositionInconsistencyError("entry_price/amount uyumsuzluğu")

    def _obs(self):
        w = self.df.iloc[self.t - self.window:self.t]
        market = w[self.market_cols].select_dtypes(
            include=[np.number]).values.astype(np.float32)
        pos = np.array(self.pos_hist[-self.window:], dtype=np.float32).reshape(-1, 1)
        eq = (np.array(self.eq_hist[-self.window:], dtype=np.float32)
              / np.float32(self.initial_capital)).reshape(-1, 1)
        obs = np.concatenate([market, pos, eq], axis=1).astype(np.float32)
        assert obs.shape == (self.window, len(self.market_cols) + 2)
        return obs

    def _portfolio(self, price: float) -> float:
        return self.cash + self.amount * price

    def step(self, action):
        if action not in (BUY, SELL, HOLD):
            self.invalid_actions += 1
            action = HOLD
        price = float(self.df.iloc[self.t][self.price_col])
        # -- execute (muhasebe her iki reward modunda BİREBİR aynı) --
        executed_buy = False
        executed_sell = False
        if action == BUY:
            if self.amount > 0 or self.cash <= 0:
                self.invalid_actions += 1  # long iken buy / boş kasayla buy
            else:
                if self.reward_mode == "realized":
                    self.cost_basis = float(self.cash)
                exec_p = price * (1 + self.slip)
                fee_paid = self.cash * self.fee
                self.amount = (self.cash - fee_paid) / exec_p
                self.fees_paid += fee_paid
                self.cash = 0.0
                self.entry_price = exec_p
                self.entries += 1
                executed_buy = True
        elif action == SELL:
            if self.amount <= 0:
                self.invalid_actions += 1  # flat iken sell
            else:
                exec_p = price * (1 - self.slip)
                proceeds = self.amount * exec_p
                fee_paid = proceeds * self.fee
                self.cash = proceeds - fee_paid
                self.fees_paid += fee_paid
                self.amount = 0.0
                self.entry_price = None
                self.roundtrips += 1
                executed_sell = True
        self._check_invariant()
        pf = self._portfolio(price)
        if self.reward_mode == "mtm":
            reward = float(np.log(pf / self._prev_pf)) if self._prev_pf > 0 else 0.0
        else:  # realized-only: BUY/HOLD/flat -> 0; SELL -> log(proceeds/cost_basis)
            if executed_sell:
                basis = self.cost_basis if self.cost_basis else self._prev_pf
                reward = float(np.log(self.cash / basis)) if basis and basis > 0 and self.cash > 0 else 0.0
                self.cost_basis = None
            else:
                reward = 0.0
        self._prev_pf = pf
        self.pos_hist.append(1 if self.amount > 0 else 0)
        self.eq_hist.append(pf)
        self.peak = max(self.peak, pf)
        self.t += 1
        # -- episode sonu: zorunlu likidasyon (sessiz düşürme YASAK) --
        if self.t >= len(self.df) - 1 and self.amount > 0:
            fpx = float(self.df.iloc[len(self.df) - 1][self.price_col]) * (1 - self.slip)
            proceeds = self.amount * fpx
            fee_paid = proceeds * self.fee
            self.cash = proceeds - fee_paid
            self.fees_paid += fee_paid
            self.amount = 0.0
            self.entry_price = None
            if self.reward_mode == "mtm":
                reward += float(np.log(self.cash / pf)) if pf > 0 else 0.0
            else:
                basis = self.cost_basis if self.cost_basis else pf
                reward += float(np.log(self.cash / basis)) if basis and basis > 0 and self.cash > 0 else 0.0
                self.cost_basis = None
            self._prev_pf = self.cash
            self.pos_hist.append(0)
            self.eq_hist.append(self.cash)
            self.roundtrips += 1
            self.forced_close = True
        terminated = self.t >= len(self.df) - 1
        truncated = bool(self._prev_pf <= 0)  # validity guard (long-only'de ~imkansız)
        dd = (self._prev_pf - self.peak) / self.peak if self.peak > 0 else 0.0
        info = {"equity": self._prev_pf, "position": 1 if self.amount > 0 else 0,
                "invalid_actions": self.invalid_actions, "entries": self.entries,
                "roundtrips": self.roundtrips, "fees_paid": self.fees_paid,
                "forced_close": self.forced_close, "drawdown": dd}
        return self._obs(), reward, terminated, truncated, info

    def render(self):
        return f"equity={self._prev_pf:.2f} pos={1 if self.amount > 0 else 0}"

    def action_masks(self) -> np.ndarray:
        """Faz 4.11 — state-dependent valid-action maskesi (sb3-contrib kontratı).

        FLAT → [HOLD, BUY]  = [True, True, False]
        LONG → [HOLD, SELL] = [True, False, True]
        HOLD her iki durumda mevcut. Saf state fonksiyonu (deterministik,
        side-effect YOK); step() davranışı DEĞİŞMEDİ.
        """
        if self.amount > 0:
            return np.array([True, False, True], dtype=bool)
        return np.array([True, True, False], dtype=bool)


CHUNK_SIZE = 5000  # Faz 4.4 kilitli seçim (4.3'teki 5-10k aralığından; max episode
# çeşitliliği + ~17 günlük anlamlı ufuk; deterministik sıralı partition).


class ChunkedTradingEnv(TradingEnv):
    """Eğitim-episode'larını chunk'lara bölen sarmalayıcı (Faz 4.4).

    - chunk_size mumluk ardışık dilimler; reset başına deterministik rotasyon.
    - Chunk sonu = base forced-liquidation (ekonomik exact) + terminated=True;
      bootstrap GEREKMEZ (getiri tamamen realize). Bedel: max hold = chunk
      uzunluğu (belgeli trade-off). Sessiz pozisyon düşürme YOK.
    - Validation DEĞERLENDİRMESİ chunk'lanmaz (tam-pencere, karşılaştırılabilirlik).
    """

    def __init__(self, df: pd.DataFrame, chunk_size: int = CHUNK_SIZE, **kw):
        if chunk_size < 1000:
            raise ValueError(f"chunk_size>=1000 olmalı: {chunk_size}")
        self.full = df.reset_index(drop=True)
        self.chunk_size = int(chunk_size)
        bounds = []
        for s in range(0, len(self.full), self.chunk_size):
            e = min(s + self.chunk_size, len(self.full))
            if e - s >= kw.get("window", 30) + 1:
                bounds.append((s, e))
        if not bounds:
            raise ValueError("chunk üretilemedi (veri kısa)")
        self.bounds = bounds
        self.chunk_idx = -1
        super().__init__(self.full.iloc[bounds[0][0]:bounds[0][1]], **kw)

    def reset(self, seed=None, options=None):
        self.chunk_idx = (self.chunk_idx + 1) % len(self.bounds)
        s, e = self.bounds[self.chunk_idx]
        self.df = self.full.iloc[s:e].reset_index(drop=True)
        obs, info = super().reset(seed=seed, options=options)
        info["chunk"] = self.chunk_idx
        return obs, info
