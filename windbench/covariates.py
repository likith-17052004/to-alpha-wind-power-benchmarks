"""Known-future inputs shared by the backtest, the tuning run and XGBoost.

calendar: time of day as sin and cos, known for any future block.

noisy wind: ERA5 degraded into something closer to a real wind forecast, for the sensitivity
test. Per run, a timing error (up to 1 h either way) and a level bias (sd 10%) apply to the whole
covariate window, past and future, as they would when the past values come from the same
forecast product. On top, a multiplicative error drifts over the horizon only, starting from
zero at the run time (AR(1), phi 0.8, innovation sd 6%), so the series stays continuous at the
run time. The noise is seeded by the origin index, so every model sees the identical forecast.
"""
import numpy as np
import pandas as pd

MAX_SHIFT = 4        # blocks, so 1 hour
BIAS_SD = 0.10
AR_PHI, AR_SD = 0.8, 0.06


def calendar(index: pd.DatetimeIndex, start: int, stop: int) -> np.ndarray:
    """[2, stop - start] time of day as sin/cos for blocks start .. stop - 1 (block centre)."""
    t = index[start:stop] + pd.Timedelta("7.5min")
    hod = (t.hour + t.minute / 60).to_numpy()
    return np.stack([np.sin(2 * np.pi * hod / 24), np.cos(2 * np.pi * hod / 24)]).astype(np.float32)


def noisy_window(w: np.ndarray, i: int, length: int, horizon: int) -> np.ndarray:
    """Degraded ERA5 wind for blocks i - length .. i + horizon - 1, as issued at origin i."""
    rng = np.random.default_rng(i)
    shift = int(rng.integers(-MAX_SHIFT, MAX_SHIFT + 1))
    bias = rng.normal(0, BIAS_SD)
    base = w[np.clip(np.arange(i - length, i + horizon) + shift, 0, len(w) - 1)]
    e = np.zeros(length + horizon)
    for h in range(horizon):  # the drift grows from zero at the run time
        e[length + h] = AR_PHI * e[length + h - 1] + rng.normal(0, AR_SD)
    return np.maximum(base * (1 + bias + e), 0).astype(np.float32)


def noisy_horizon(w: np.ndarray, i: int, horizon: int) -> np.ndarray:
    return noisy_window(w, i, 0, horizon)
