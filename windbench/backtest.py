"""Rolling-origin backtest that mimics Indian real-time scheduling.

Every 4 hours each model sees plant data up to the run time and forecasts the next 16 blocks
of 15 minutes (15 min to 4 h ahead). Input setups:

  A        past power only; the context ends at the run time, so it includes the actuals
           observed since the previous run
  B        past power plus the wind speed over the context and the next 4 hours (ERA5 100 m,
           standing in for a wind forecast), passed as a known-future covariate
  B noisy  as B, with the wind degraded into a realistic forecast (see covariates.py)

Foundation models use the history length and time-of-day choice picked for them on the
validation window (tune.py writes results/tuning.json). Output:
results/forecasts_<plant>.parquet with one row per (run, model, step) and timing.csv.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time

import numpy as np
import pandas as pd

from . import baselines
from .config import (DEFAULT_CONTEXT, HORIZON, MAX_CONTEXT, MAX_CTX_MISSING, MODELS, PLANTS,
                     QUANTILES, RESULTS_DIR, ROOT, RUN_EVERY, split_model_name)
from .covariates import calendar, noisy_horizon, noisy_window
from .data import load


def fill(a: np.ndarray) -> np.ndarray:
    return pd.Series(a).interpolate(limit_direction="both").to_numpy(np.float32)


class Origins:
    """The run times in [start, end) and every input a model may use at each of them."""

    def __init__(self, df: pd.DataFrame, start: str, end: str, limit: int | None = None):
        v = df["power_mw"].to_numpy(np.float32)
        self.w = df["era5_ws"].to_numpy(np.float32)
        self.index = df.index
        self.times, idx, ctx = [], [], []
        for t0 in pd.date_range(start, end, freq=RUN_EVERY, inclusive="left"):
            i = self.index.get_indexer([t0])[0]
            if i < MAX_CONTEXT or i + HORIZON > len(v):
                continue
            c, fut = v[i - MAX_CONTEXT:i], v[i:i + HORIZON]
            # the missing-data rule uses the default window, so the set of runs does not depend
            # on the history length being evaluated
            if np.isnan(fut).any() or np.isnan(c[-1]) or np.isnan(c[-DEFAULT_CONTEXT:]).mean() > MAX_CTX_MISSING:
                continue
            self.times.append(t0)
            idx.append(i)
            ctx.append(fill(c))  # identical gap-filled history for every model
            if limit and len(idx) == limit:
                break
        self.idx = np.array(idx)
        self.ctx_full = np.stack(ctx)
        self.y = np.stack([v[i:i + HORIZON] for i in self.idx])

    def ctx(self, length: int) -> np.ndarray:
        return self.ctx_full[:, -length:]

    def horizon_wind(self, wind: str) -> np.ndarray:
        """[B, HORIZON] wind over the forecast horizon: ERA5 or its degraded version."""
        if wind == "noisy":
            return np.stack([noisy_horizon(self.w, i, HORIZON) for i in self.idx])
        return self.w[self.idx[:, None] + np.arange(HORIZON)]

    def future(self, length: int, wind: str | None, cal: bool) -> np.ndarray | None:
        """Known-future covariates [B, F, length + HORIZON]: wind and/or time of day."""
        if not wind and not cal:
            return None
        rows = []
        for i in self.idx:
            f = []
            if wind == "noisy":
                f.append(noisy_window(self.w, i, length, HORIZON)[None])
            elif wind:
                f.append(self.w[i - length:i + HORIZON][None])
            if cal:
                f.append(calendar(self.index, i - length, i + HORIZON))
            rows.append(np.concatenate(f))
        return np.stack(rows).astype(np.float32)


def run_xgboost(plant: str, o: Origins, before: str, wind: str | None) -> np.ndarray:
    """Train and predict in a separate interpreter: XGBoost and PyTorch both bundle libomp,
    and loading both in one process segfaults on macOS."""
    with tempfile.TemporaryDirectory() as tmp:
        np.save(f"{tmp}/idx.npy", o.idx)
        subprocess.run([sys.executable, "-m", "windbench.xgb_model", plant, before, wind or "none",
                        f"{tmp}/idx.npy", f"{tmp}/out.npz", ",".join(map(str, QUANTILES))],
                       check=True, cwd=ROOT)
        r = np.load(f"{tmp}/out.npz")
        print(f"    xgboost trained on {int(r['n'])} hourly runs before {before}")
        return r["q"]


def model_config(tuning: dict, name: str, setup: str) -> dict:
    return tuning.get(name, {}).get(setup, {"context": DEFAULT_CONTEXT, "calendar": False})


def run_model(name: str, plant: str, o: Origins, df: pd.DataFrame, tuning: dict) -> np.ndarray:
    base, wind = split_model_name(name)
    before = PLANTS[plant]["test_start"]
    if base == "persistence":
        return baselines.persistence(o.ctx(DEFAULT_CONTEXT))
    if base == "power-curve":
        return baselines.fit_power_curve(df, before)(o.horizon_wind(wind))
    if base == "xgboost":
        return run_xgboost(plant, o, before, wind)
    from .foundation import RUNNERS  # imports PyTorch only when a foundation model runs
    c = model_config(tuning, base, "B" if wind else "A")
    return RUNNERS[base](o.ctx(c["context"]), o.future(c["context"], wind, c["calendar"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="+", default=MODELS, help="models to run (default: all)")
    ap.add_argument("--append", action="store_true", help="replace only these models in existing results")
    ap.add_argument("--quick", type=int, metavar="N", help="only the first N runs, for a smoke test")
    args = ap.parse_args(argv)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    tpath = RESULTS_DIR / "tuning.json"
    tuning = json.loads(tpath.read_text()) if tpath.exists() else {}
    if not tuning:
        print("no results/tuning.json: foundation models use the default history length")
    timing = []
    for plant, cfg in PLANTS.items():
        df = load(plant)
        o = Origins(df, cfg["test_start"], cfg["test_end"], limit=args.quick)
        print(f"[{plant}] {len(o.idx)} runs")
        frames = []
        for name in args.models:
            t = time.time()
            q = run_model(name, plant, o, df, tuning)
            dt = time.time() - t
            assert q.shape == (len(o.idx), HORIZON, len(QUANTILES)), (name, q.shape)
            q = np.sort(np.clip(q, 0, cfg["capacity"]), axis=2)  # physical bounds, monotone quantiles
            timing.append({"plant": plant, "model": name, "seconds": dt, "per_forecast_ms": 1000 * dt / len(o.idx)})
            print(f"  {name:28s} {dt:7.1f} s")
            fr = pd.DataFrame({"origin": np.repeat(o.times, HORIZON),
                               "step": np.tile(np.arange(1, HORIZON + 1), len(o.idx)),
                               "model": name, "y": o.y.ravel()})
            for j, ql in enumerate(QUANTILES):
                fr[f"q{ql:.1f}"] = q[:, :, j].ravel()
            frames.append(fr)
        new = pd.concat(frames)
        path = RESULTS_DIR / f"forecasts_{plant}.parquet"
        if args.append and path.exists():
            old = pd.read_parquet(path)
            new = pd.concat([old[~old["model"].isin(args.models)], new])
        new.to_parquet(path)
    timing = pd.DataFrame(timing)
    tp = RESULTS_DIR / "timing.csv"
    if args.append and tp.exists():
        old = pd.read_csv(tp)
        timing = pd.concat([old[~old["model"].isin(args.models)], timing])
    timing.to_csv(tp, index=False)


if __name__ == "__main__":
    main()
