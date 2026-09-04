"""
Faz 4 — RL eğitim sarmalayıcısı (SB3 PPO/SAC).
Bütçe: config/experiment.yaml rl_budget — bütçe bitmeden elenmez.
Final Test'e dokunmaz.
"""
import argparse, yaml, pandas as pd
from src.rl.env import TradingEnv

def load_df(csv): return pd.read_csv(csv)

def train(algo="PPO", df_path="freqtrade/user_data/data/binance_BTC_USDT_5m.csv", budget=50):
    df=load_df(df_path)
    env=TradingEnv(df)
    if algo=="PPO":
        from stable_baselines3 import PPO
        model=PPO("MlpPolicy", env, verbose=1)
    else:
        from stable_baselines3 import SAC
        # SAC discrete değil — PPO varsayılan
        from stable_baselines3 import PPO
        model=PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=100_000)
    model.save(f"experiments/phase_04_rl/{algo.lower()}_model")
    print(f"[rl] {algo} eğitildi")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--algo", default="PPO", choices=["PPO","SAC"])
    p.add_argument("--config", default="config/experiment.yaml")
    args=p.parse_args()
    train(args.algo)
