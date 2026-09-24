"""Supervised XGBoost baseline, trained on the plant's own history (the year before the test).

One multi-quantile model shared across the 16 steps (the step is a feature). The target is the
change from the last observed block, so every forecast is anchored to the latest actual value.
Features use data available at the run time only:
  A: 16 recent power lags, rolling means and spread, time of day;
  B: A plus the ERA5 wind over the forecast horizon (the same input the foundation models get).
     In the noisy-wind run the wind is degraded in training and test alike, as a real model
     would be trained on archived forecasts.

The design (change target, no day of year, one shared model) was chosen on a validation split
inside 2014 (train Jan to Sep, validate Oct to Dec), never on the test year. Day of year is left
out because with one training year the trees memorise that year's weather by date.

This module is also a small command-line tool: the backtest calls it in a separate interpreter,
because XGBoost and PyTorch cannot share a process on macOS.
"""
import numpy as np
import pandas as pd

from .config import HORIZON
from .covariates import noisy_window

LAGS = 16  # last 4 hours of 15-min blocks
PARAMS = dict(n_estimators=400, learning_rate=0.05, max_depth=6, min_child_weight=20,
              subsample=0.8, colsample_bytree=0.8, tree_method="hist")


def features(df: pd.DataFrame, idx: np.ndarray, wind: str | None) -> pd.DataFrame:
    """One row per (origin index i, step h). Origin i means the run is issued at the start of
    block i, so the most recent observed block is i - 1. wind: None, "era5" or "noisy"."""
    p = df["power_mw"].to_numpy(np.float32)
    w = df["era5_ws"].to_numpy(np.float32)
    t = df.index
    i = np.repeat(idx, HORIZON)
    h = np.tile(np.arange(1, HORIZON + 1), len(idx))
    tgt = i + h - 1
    X = {"step": h}
    for k in range(1, LAGS + 1):
        X[f"lag{k}"] = p[i - k]
    for win in (4, 16, 96):
        X[f"mean{win}"] = np.array([np.nanmean(p[j - win:j]) for j in idx]).repeat(HORIZON)
    X["std16"] = np.array([np.nanstd(p[j - 16:j]) for j in idx]).repeat(HORIZON)
    X["d1"] = X["lag1"] - X["lag2"]
    X["d4"] = X["lag1"] - X["lag5"]
    hod = (t[tgt].hour + t[tgt].minute / 60).to_numpy()
    X["hod_sin"], X["hod_cos"] = np.sin(2 * np.pi * hod / 24), np.cos(2 * np.pi * hod / 24)
    if wind:
        if wind == "noisy":  # the whole series comes from the same degraded forecast
            win = np.stack([noisy_window(w, j, 1, HORIZON) for j in idx])
            now, hw = win[:, 0], win[:, 1:]
        else:
            now, hw = w[idx - 1], w[idx[:, None] + np.arange(HORIZON)]
        X["ws_target"] = hw.ravel()
        X["ws_now"] = now.repeat(HORIZON)
        X["ws_delta"] = X["ws_target"] - X["ws_now"]
        X["ws_target_cubed"] = np.minimum(X["ws_target"], 15) ** 3
        X["ws_horizon_mean"] = hw.mean(1).repeat(HORIZON)
    return pd.DataFrame(X)


def train_origins(df: pd.DataFrame, before: str, stride: int = 4) -> np.ndarray:
    """Hourly origins before the test year whose 4-hour target window is complete."""
    end = df.index.get_indexer([pd.Timestamp(before)])[0]
    p = df["power_mw"].to_numpy()
    idx = np.arange(96, end - HORIZON + 1, stride)
    ok = [not np.isnan(p[j:j + HORIZON]).any() and not np.isnan(p[j - LAGS:j]).any() for j in idx]
    return idx[np.array(ok)]


def fit(Xtr: pd.DataFrame, ytr: np.ndarray, quantiles, change_target: bool = True):
    import xgboost as xgb
    y = ytr - (Xtr["lag1"].to_numpy() if change_target else 0)
    return xgb.XGBRegressor(objective="reg:quantileerror", quantile_alpha=np.asarray(quantiles),
                            random_state=0, **PARAMS).fit(Xtr, y)


def predict(m, X: pd.DataFrame, change_target: bool = True) -> np.ndarray:
    return m.predict(X) + (X["lag1"].to_numpy()[:, None] if change_target else 0)


def fit_predict(df: pd.DataFrame, test_idx: np.ndarray, before: str, quantiles, wind: str | None):
    """Train on origins before `before`; return quantile forecasts [len(test_idx), HORIZON, Q]."""
    tr = train_origins(df, before)
    Xtr = features(df, tr, wind)
    ytr = np.stack([df["power_mw"].to_numpy()[j:j + HORIZON] for j in tr]).ravel()
    m = fit(Xtr, ytr, quantiles)
    q = predict(m, features(df, test_idx, wind))
    return q.reshape(len(test_idx), HORIZON, len(quantiles)).astype(np.float32), len(tr)


if __name__ == "__main__":
    import sys

    from .data import load

    plant, before, wind, idx_path, out_path, qs = sys.argv[1:7]
    q, n = fit_predict(load(plant), np.load(idx_path), before, [float(x) for x in qs.split(",")],
                       None if wind == "none" else wind)
    np.savez(out_path, q=q, n=n)
