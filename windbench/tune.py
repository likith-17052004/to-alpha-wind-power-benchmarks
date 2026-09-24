"""Give each foundation model the same validation budget XGBoost had.

On the validation window (October to December 2014, a run every 4 hours) pick, per model and per
setup, the history length and whether to add time of day as a known-future input, by nMAE of the
median. The test year is never touched. Writes results/tuning.json and results/tuning_grid.csv.
"""
import json

import numpy as np
import pandas as pd

from .backtest import Origins
from .config import CONTEXT_GRID, FOUNDATION_MODELS, PLANTS, RESULTS_DIR, VAL_END, VAL_START
from .data import load


def main(argv=None):
    from .foundation import RUNNERS

    plant = "engie_lhb"
    cap = PLANTS[plant]["capacity"]
    o = Origins(load(plant), VAL_START, VAL_END)
    print(f"validation: {len(o.idx)} runs from {VAL_START} to {VAL_END}")
    best_all, grid = {}, []
    for name in FOUNDATION_MODELS:
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
    (RESULTS_DIR / "tuning.json").write_text(json.dumps(best_all, indent=2))
    pd.DataFrame(grid).to_csv(RESULTS_DIR / "tuning_grid.csv", index=False)
    print(json.dumps(best_all, indent=2))


if __name__ == "__main__":
    main()
