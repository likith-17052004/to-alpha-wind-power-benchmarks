"""Give each foundation model the same validation budget XGBoost had.

On the validation window (October to December 2014, a run every 4 hours) pick, per model and per
setup, the history length and whether to add time of day as a known-future input, by nMAE of the
median. The test year is never touched. Writes results/tuning.json and results/tuning_grid.csv;
with --models, only those models are re-tuned and the others keep their saved choices.
"""
import argparse
import json

import numpy as np
import pandas as pd

from .backtest import Origins
from .config import CONTEXT_GRID, FOUNDATION_MODELS, PLANTS, RESULTS_DIR, VAL_END, VAL_START
from .data import load


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="+", default=FOUNDATION_MODELS, choices=FOUNDATION_MODELS,
                    help="foundation models to tune (default: all)")
    args = ap.parse_args(argv)
    from .foundation import RUNNERS

    plant = "engie_lhb"
    cap = PLANTS[plant]["capacity"]
    o = Origins(load(plant), VAL_START, VAL_END)
    print(f"validation: {len(o.idx)} runs from {VAL_START} to {VAL_END}")
    best_all, grid = {}, []
    for name in args.models:
        best_all[name] = {}
        for setup, wind in [("A", None), ("B", "era5")]:
            best = None
            for ctx_len in CONTEXT_GRID:
                for cal in (False, True):
                    q = RUNNERS[name](o.ctx(ctx_len), o.future(ctx_len, wind, cal))
                    med = np.clip(q[:, :, q.shape[2] // 2], 0, cap)
                    nmae = float(100 * np.abs(med - o.y).mean() / cap)
                    grid.append({"model": name, "setup": setup, "context": ctx_len, "calendar": cal, "nMAE": nmae})
                    print(f"  {name:12s} {setup} history {ctx_len:5d} time of day {cal!s:5s} nMAE {nmae:.3f}")
                    if best is None or nmae < best["nMAE"]:
                        best = {"context": ctx_len, "calendar": cal, "nMAE": nmae}
            best_all[name][setup] = best
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    tpath, gpath = RESULTS_DIR / "tuning.json", RESULTS_DIR / "tuning_grid.csv"
    grid = pd.DataFrame(grid)
    if set(args.models) != set(FOUNDATION_MODELS):  # keep the saved choices of every other model
        saved = json.loads(tpath.read_text()) if tpath.exists() else {}
        best_all = {**saved, **best_all}
        if gpath.exists():
            old = pd.read_csv(gpath, float_precision="round_trip")
            grid = pd.concat([old[~old["model"].isin(args.models)], grid])
    order = {m: k for k, m in enumerate(FOUNDATION_MODELS)}
    best_all = {m: best_all[m] for m in sorted(best_all, key=lambda m: order.get(m, len(order)))}
    grid = grid.sort_values("model", key=lambda s: s.map(order), kind="stable")
    tpath.write_text(json.dumps(best_all, indent=2))
    grid.to_csv(gpath, index=False)
    print(json.dumps(best_all, indent=2))


if __name__ == "__main__":
    main()
