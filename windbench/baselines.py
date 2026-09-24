"""Simple reference forecasts: persistence (setup A) and an empirical power curve (setup B)."""
import numpy as np
import pandas as pd

from .config import HORIZON, QUANTILES


def persistence(ctx: np.ndarray) -> np.ndarray:
    """Hold the last observed block flat: [B, T] -> [B, HORIZON, Q]."""
    return np.repeat(ctx[:, -1:, None], HORIZON, axis=1).repeat(len(QUANTILES), axis=2)


def fit_power_curve(df: pd.DataFrame, before: str):
    """Wind to power curve from data before the test year: per 0.5 m/s bin, the deciles of
    observed power. Returns f(ws [N, H]) -> [N, H, Q]."""
    train = df.loc[:before].iloc[:-1].dropna(subset=["power_mw", "era5_ws"])
    bins = np.arange(0, train["era5_ws"].max() + 0.5, 0.5)
    b = np.digitize(train["era5_ws"], bins)
    table = train.groupby(b)["power_mw"].quantile(QUANTILES).unstack()
    table = table.reindex(range(1, len(bins) + 1)).interpolate(limit_direction="both")
    centres = bins + 0.25
    return lambda ws: np.stack([np.interp(ws, centres, table[q].to_numpy()) for q in QUANTILES], axis=-1)
