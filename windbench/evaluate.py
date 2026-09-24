"""Score the backtest: results/forecasts_<plant>.parquet to results/metrics.csv and metrics.json.

All errors are normalised by plant capacity (% of installed MW), the usual convention for wind.
CRPS is approximated from the 9 deciles (2 x mean pinball loss).

Two scorings: "all" blocks, and "available" = excluding target blocks touched by turbine
unavailability or curtailment (no model can forecast those). Confidence intervals and the
pairwise model comparison use a bootstrap over whole days, paired across models.
"""
import json

import numpy as np
import pandas as pd

from .config import PLANTS, RESULTS_DIR as RESULTS
from .data import load

QCOLS = [f"q{q:.1f}" for q in np.arange(1, 10) / 10]
QLEVELS = np.arange(1, 10) / 10


def per_group(g: pd.DataFrame, cap: float) -> pd.Series:
    y, med = g["y"].to_numpy(), g["q0.5"].to_numpy()
    q = g[QCOLS].to_numpy()
    e = med - y
    diff = y[:, None] - q
    pinball = np.maximum(QLEVELS * diff, (QLEVELS - 1) * diff).mean(axis=1)
    return pd.Series({
        "nMAE": 100 * np.abs(e).mean() / cap,
        "nRMSE": 100 * np.sqrt((e ** 2).mean()) / cap,
        "nBias": 100 * e.mean() / cap,
        "nCRPS": 100 * 2 * pinball.mean() / cap,
        "cov80": 100 * ((y >= g["q0.1"]) & (y <= g["q0.9"])).mean(),
        "n": len(g),
    })


def day_sums(f: pd.DataFrame):
    """Per (day, model) sums of absolute error, and per-day block counts (same for every model)."""
    day = f["origin"].dt.floor("D")
    ae = (f["q0.5"] - f["y"]).abs().groupby([f["model"], day]).sum().unstack(0)
    cnt = f[f["model"] == "persistence"].groupby(day[f["model"] == "persistence"]).size().reindex(ae.index)
    return ae, cnt.to_numpy()


def bootstrap(f: pd.DataFrame, cap: float, n: int = 2000, seed: int = 0):
    """Day-block bootstrap, paired across models (every model resampled on the same days).

    Returns (skill CIs vs persistence, pairwise nMAE differences row - column with 95% CI)."""
    rng = np.random.default_rng(seed)
    ae, cnt = day_sums(f)
    idx = rng.integers(0, len(ae), (n, len(ae)))
    nmae = {m: 100 * ae[m].to_numpy()[idx].sum(1) / cnt[idx].sum(1) / cap for m in ae.columns}
    point = {m: 100 * ae[m].sum() / cnt.sum() / cap for m in ae.columns}
    skill = {}
    for m in ae.columns.drop("persistence"):
        sk = 100 * (1 - nmae[m] / nmae["persistence"])
        skill[m] = {"skill": float(100 * (1 - point[m] / point["persistence"])),
                    "lo": float(np.percentile(sk, 2.5)), "hi": float(np.percentile(sk, 97.5))}
    models = sorted(ae.columns, key=lambda m: point[m])
    pair = {"models": models, "diff": [], "lo": [], "hi": []}
    for a in models:
        d = [nmae[a] - nmae[b] for b in models]
        pair["diff"].append([float(point[a] - point[b]) for b in models])
        pair["lo"].append([float(np.percentile(x, 2.5)) for x in d])
        pair["hi"].append([float(np.percentile(x, 97.5)) for x in d])
    return skill, pair


def example_day(f: pd.DataFrame, s: pd.Series) -> dict:
    """The test day with the largest swings, as six consecutive 4-hour real-time runs."""
    p = f[f.model == "persistence"]
    days = p.groupby(p["origin"].dt.floor("D")).size()
    full = days[days == 6 * 16].index
    swing = s.groupby(s.index.floor("D")).apply(lambda x: x.diff().abs().sum()).reindex(full)
    day = swing.idxmax()
    g = f[f["origin"].dt.floor("D") == day].copy()
    g["t"] = g["origin"] + pd.to_timedelta((g["step"] - 1) * 15, "min")
    actual = s.loc[day - pd.Timedelta("6h"): day + pd.Timedelta("1D") - pd.Timedelta("15min")]
    return {"day": str(day.date()),
            "actual": [[str(t), round(float(v), 3)] for t, v in actual.items() if pd.notna(v)],
            "runs": {m: [[str(r.t), r.origin.strftime("%H:%M"), round(r["q0.1"], 3), round(r["q0.5"], 3), round(r["q0.9"], 3)]
                         for _, r in gm.iterrows()] for m, gm in g.groupby("model")}}


def main(argv=None):
    rows, cis, pairs, examples, excluded = [], {}, {}, {}, {}
    for plant, cfg in PLANTS.items():
        f = pd.read_parquet(RESULTS / f"forecasts_{plant}.parquet").reset_index(drop=True)
        cap = cfg["capacity"]
        d = load(plant)
        examples[plant] = example_day(f, d["power_mw"])
        t = f["origin"] + pd.to_timedelta((f["step"] - 1) * 15, "min")
        f["available"] = d["available"].reindex(t).to_numpy()
        excluded[plant] = float(100 * (1 - f.loc[f.model == "persistence", "available"].mean()))
        cis[plant], pairs[plant] = {}, {}
        for scoring, g in [("all", f), ("available", f[f["available"]])]:
            cis[plant][scoring], pairs[plant][scoring] = bootstrap(g, cap)
            by_step = g.groupby(["model", "step"]).apply(per_group, cap=cap, include_groups=False).reset_index()
            overall = g.groupby("model").apply(per_group, cap=cap, include_groups=False).reset_index()
            overall["step"] = 0  # 0 = all 16 steps pooled
            m = pd.concat([by_step, overall])
            pers = m[m.model == "persistence"].set_index("step")
            for k in ["nMAE", "nRMSE"]:
                m[f"skill_{k}"] = 100 * (1 - m[k] / m["step"].map(pers[k]))
            m.insert(0, "scoring", scoring)
            m.insert(0, "plant", plant)
            rows.append(m)
    out = pd.concat(rows)
    out.to_csv(RESULTS / "metrics.csv", index=False)
    timing = pd.read_csv(RESULTS / "timing.csv")
    tpath = RESULTS / "tuning_grid.csv"
    payload = {"metrics": out.round(4).to_dict(orient="records"),
               "timing": timing.round(3).to_dict(orient="records"),
               "skill_ci": cis, "pairwise": pairs, "examples": examples, "excluded_pct": excluded,
               "tuning": json.loads((RESULTS / "tuning.json").read_text()) if (RESULTS / "tuning.json").exists() else {},
               "tuning_grid": pd.read_csv(tpath).round(4).to_dict(orient="records") if tpath.exists() else [],
               "plants": PLANTS}
    (RESULTS / "metrics.json").write_text(json.dumps(payload, default=str))
    pd.set_option("display.width", 200)
    print(f"excluded (unavailable/curtailed) blocks: {excluded}")
    for sc in ["all", "available"]:
        o = out[(out.step == 0) & (out.scoring == sc)].drop(columns=["step", "scoring"]).sort_values("nMAE")
        print(f"\n== scoring: {sc}\n" + o.round(2).to_string(index=False))
    for plant in PLANTS:
        print(f"\n{plant} nMAE (% of capacity) by step, all blocks")
        a = out[(out.plant == plant) & (out.step > 0) & (out.scoring == "all")]
        print(a.pivot(index="step", columns="model", values="nMAE").round(2).T[[1, 2, 4, 8, 12, 16]].to_string())


if __name__ == "__main__":
    main()
