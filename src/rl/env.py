"""
Faz 4 — Trading Gymnasium Environment (PPO/SAC).
Reward başlangıçta SADECE log portfolio return (Anayasa: tek, basit).
"""
import gymnasium as gym
import numpy as np
import pandas as pd

class TradingEnv(gym.Env):
    metadata={"render_modes":["human"]}
    def __init__(self, df: pd.DataFrame, fee: float=0.001, window: int=30):
        super().__init__()
        self.df=df.reset_index(drop=True)
        self.fee=fee
        self.window=window
        # obs: window * features (close, rsi, sma, atr, vb.)
        n_feat=len([c for c in df.columns if c not in ("date","open","high","low")])
        self.observation_space=gym.spaces.Box(low=-np.inf, high=np.inf, shape=(window, max(1,n_feat)), dtype=np.float32)
        self.action_space=gym.spaces.Discrete(3)  # 0 hold, 1 buy, 2 sell
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.pos=0  # 0 flat, 1 long
        self.entry_price=None
        self.equity=1.0
        self.t=self.window
        return self._obs(), {}

    def _obs(self):
        w=self.df.iloc[self.t-self.window:self.t]
        # sadece numeric kolonlar
        num=w.select_dtypes(include=[np.number]).values.astype(np.float32)
        return num

    def step(self, action):
        price=self.df.iloc[self.t]["close"]
        prev_equity=self.equity
        reward=0.0
        # basit execution
        if action==1 and self.pos==0:  # buy
            self.pos=1; self.entry_price=price*(1+self.fee)
        elif action==2 and self.pos==1:  # sell
            ret=np.log(price*(1-self.fee)/self.entry_price)
            self.equity*=np.exp(ret)
            reward=ret  # log portfolio return
            self.pos=0; self.entry_price=None

        self.t+=1
        terminated=self.t>=len(self.df)-1
        truncated=False
        # pozisyon taşırken mark-to-market reward yok — sadece kapanışta (basitlik için)
        return self._obs(), float(reward), terminated, truncated, {"equity": self.equity}
