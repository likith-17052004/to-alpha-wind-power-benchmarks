"""Zero-shot time-series foundation models behind one interface.

Each runner takes ctx [B, T] (past power) and fut [B, F, T + HORIZON] or None (known-future
covariates spanning context and horizon) and returns quantile forecasts [B, HORIZON, Q].
"""
import numpy as np
import torch

from .config import BATCH, HORIZON, QUANTILES

DEVICE = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
_CACHE = {}


def _load(name: str):
    if name not in _CACHE:
        if name == "t0-alpha":
            from t0 import T0Forecaster
            _CACHE[name] = T0Forecaster.from_pretrained("theforecastingcompany/t0-alpha").eval().to(DEVICE)
        elif name == "chronos-2":
            from chronos import Chronos2Pipeline
            _CACHE[name] = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map=DEVICE)
        elif name == "timesfm-3.0":
            from timesfm3 import TimesFM3Forecaster
            _CACHE[name] = TimesFM3Forecaster.from_pretrained("google/timesfm-3.0-pytorch", device=DEVICE)
        else:
            raise ValueError(f"unknown foundation model {name}")
    return _CACHE[name]


def run_t0(ctx, fut=None):
    m = _load("t0-alpha")
    out = []
    with torch.no_grad():
        for b in range(0, len(ctx), BATCH):
            x = torch.from_numpy(np.ascontiguousarray(ctx[b:b + BATCH])).to(DEVICE)
            kw = {} if fut is None else {"future_covariates": torch.from_numpy(fut[b:b + BATCH]).to(DEVICE)}
            out.append(m.predict(x, horizon=HORIZON, quantile_levels=QUANTILES, **kw).quantiles.float().cpu().numpy())
    return np.concatenate(out)


def run_chronos2(ctx, fut=None):
    p = _load("chronos-2")
    if fut is None:
        inputs = [c[None] for c in ctx]
    else:
        T = ctx.shape[1]
        inputs = [{"target": c,
                   "past_covariates": {f"x{k}": f[k, :T] for k in range(len(f))},
                   "future_covariates": {f"x{k}": f[k, T:] for k in range(len(f))}} for c, f in zip(ctx, fut)]
    q, _ = p.predict_quantiles(inputs, prediction_length=HORIZON, quantile_levels=QUANTILES, batch_size=BATCH)
    return np.stack([t[0].float().cpu().numpy() for t in q])


def run_timesfm3(ctx, fut=None):
    f = _load("timesfm-3.0")
    kw = {} if fut is None else {"past_future_covariates": list(fut)}
    outs = f.predict_batch(list(ctx), horizon=HORIZON, return_quantiles=True, **kw)
    return np.stack([np.asarray(o.quantiles, dtype=np.float32).reshape(HORIZON, -1) for o in outs])  # deciles


RUNNERS = {"t0-alpha": run_t0, "chronos-2": run_chronos2, "timesfm-3.0": run_timesfm3}
