"""Static charts for the README, rendered for GitHub's light and dark themes.

Reads results/metrics.csv and results/metrics.json; writes docs/figures/<name>_{light,dark}.png.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .config import DOCS_DIR, FUT_SUFFIX, NOISY_SUFFIX, PLANTS, RESULTS_DIR  # noqa: E402

PLANT = "engie_lhb"
OUT = DOCS_DIR / "figures"
THEMES = {
    "light": dict(bg="#ffffff", ink="#1f2328", muted="#59636e", grid="#e6e9ec",
                  t0="#2a78d6", t0b="#e87ba4", ch="#eb6834", tf="#1baf7a", xgb="#eda100", pers="#8a9095", curve="#4a5157"),
    "dark": dict(bg="#0d1117", ink="#e6edf3", muted="#9198a1", grid="#262c33",
                 t0="#3987e5", t0b="#d55181", ch="#d95926", tf="#199e70", xgb="#c98500", pers="#8f969b", curve="#b4bcc2"),
}
FAMILIES = [("t0-alpha", "t0-alpha", "t0"), ("t0-beta", "t0-beta", "t0b"), ("chronos-2", "Chronos-2", "ch"),
            ("timesfm-3.0", "TimesFM 3.0", "tf"), ("xgboost", "XGBoost", "xgb")]
STEP_TICKS = [1, 4, 8, 12, 16]
STEP_LABELS = ["15 min", "1 h", "2 h", "3 h", "4 h"]
EXAMPLE_FAMILY = "t0-alpha"  # drawn with future wind in the example day chart


def style(ax, th):
    ax.set_facecolor(th["bg"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(th["grid"])
    ax.tick_params(colors=th["muted"], labelsize=9, length=0)
    ax.grid(axis="y", color=th["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def new_fig(th, w, h, ncols=1, sharey=False):
    fig, axes = plt.subplots(1, ncols, figsize=(w, h), sharey=sharey, dpi=160)
    fig.patch.set_facecolor(th["bg"])
    axes = np.atleast_1d(axes)
    for ax in axes:
        style(ax, th)
    return fig, axes


def end_labels(ax, items, th, x, gap_frac=0.075):
    """Label line ends to the right of x. Labels are spread at least gap_frac of the y range
    apart, centred on the line ends, and joined to their line by a thin leader in its colour."""
    lo, hi = ax.get_ylim()
    gap = gap_frac * (hi - lo)
    items = sorted(items, key=lambda it: it[1])
    ys = [it[1] for it in items]
    for k in range(1, len(ys)):
        ys[k] = max(ys[k], ys[k - 1] + gap)
    shift = (np.mean([it[1] for it in items]) - np.mean(ys))  # keep the group centred on the lines
    ys = [y + shift for y in ys]
    x_text = x + 0.9
    for (text, y_line, color), y in zip(items, ys):
        ax.plot([x, x + 0.35, x_text - 0.1], [y_line, y, y], color=color, linewidth=1, clip_on=False)
        ax.text(x_text, y, text, va="center", fontsize=8.5, color=th["ink"], clip_on=False)


def save(fig, name, theme):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}_{theme}.png", facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def lead_time(m, th, theme):
    """nMAE at every step, setup A next to setup B."""
    fig, (a, b) = new_fig(th, 11, 4.2, ncols=2, sharey=True)
    steps = np.arange(1, 17)
    get = lambda model: m[(m.model == model) & (m.step > 0)].sort_values("step")["nMAE"].to_numpy()  # noqa: E731
    for ax, suffix, title in [(a, "", "A: past power only"), (b, FUT_SUFFIX, "B: past power and future wind")]:
        labels = []
        for fid, lab, key in FAMILIES:
            y = get(fid + suffix)
            ax.plot(steps, y, color=th[key], linewidth=2, solid_capstyle="round")
            labels.append((lab, y[-1], th[key]))
        base, blab, bkey, dash = (("persistence", "Persistence", "pers", (0, (1, 3))) if not suffix
                                  else ("power-curve", "Power curve", "curve", (0, (6, 2, 1, 2))))
        y = get(base)
        ax.plot(steps, y, color=th[bkey], linewidth=1.8, linestyle=dash)
        labels.append((blab, y[-1], th[bkey]))
        end_labels(ax, labels, th, 16)
        ax.set_title(title, loc="left", fontsize=11, color=th["ink"], fontweight="bold", pad=10)
        ax.set_xticks(STEP_TICKS, STEP_LABELS)
        ax.set_xlim(1, 16)
        ax.set_xlabel("lead time", color=th["muted"], fontsize=9)
    a.set_ylabel("nMAE, % of capacity", color=th["muted"], fontsize=9)
    fig.subplots_adjust(wspace=0.45)
    save(fig, "lead_time", theme)


def wind_gain(m, th, theme):
    """Setup B minus setup A at every step: what knowing the future wind is worth."""
    fig, (ax,) = new_fig(th, 8, 3.8)
    steps = np.arange(1, 17)
    get = lambda model: m[(m.model == model) & (m.step > 0)].sort_values("step")["nMAE"].to_numpy()  # noqa: E731
    labels = []
    for fid, lab, key in FAMILIES:
        d = get(fid + FUT_SUFFIX) - get(fid)
        ax.plot(steps, d, color=th[key], linewidth=2)
        labels.append((f"{lab} {d[-1]:+.2f}", d[-1], th[key]))
    ax.axhline(0, color=th["muted"], linewidth=1)
    end_labels(ax, labels, th, 16)
    ax.set_xticks(STEP_TICKS, STEP_LABELS)
    ax.set_xlim(1, 16)
    ax.set_xlabel("lead time", color=th["muted"], fontsize=9)
    ax.set_ylabel("change in nMAE, percentage points", color=th["muted"], fontsize=9)
    ax.set_title("Adding the future wind: below zero means it helped", loc="left", fontsize=11,
                 color=th["ink"], fontweight="bold", pad=10)
    save(fig, "wind_gain", theme)


def noisy_wind(m, th, theme):
    """Each model with no wind, a realistic noisy wind forecast and ERA5 wind."""
    o = m[m.step == 0].set_index("model")["nMAE"]
    rows = [(lab, key, o.get(fid), o[fid + NOISY_SUFFIX], o[fid + FUT_SUFFIX]) for fid, lab, key in FAMILIES]
    rows.sort(key=lambda r: r[3])
    fig, (ax,) = new_fig(th, 8, 1.0 + 0.6 * len(rows))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=th["grid"], linewidth=0.8)
    for k, (lab, key, a, n, e) in enumerate(rows):
        y = len(rows) - 1 - k
        ax.plot([e, a], [y, y], color=th[key], linewidth=2, alpha=0.35)
        ax.scatter([a], [y], s=60, facecolor=th["bg"], edgecolor=th[key], linewidth=2, zorder=3)
        ax.scatter([n], [y], s=60, marker="s", color=th[key], alpha=0.55, edgecolor=th[key], linewidth=1.5, zorder=3)
        ax.scatter([e], [y], s=60, color=th[key], edgecolor=th["bg"], linewidth=1.5, zorder=4)
    ax.axvline(o["persistence"], color=th["pers"], linewidth=1.5, linestyle=(0, (1, 3)))
    ax.annotate("persistence", (o["persistence"], len(rows) - 0.55), xytext=(-4, 0), textcoords="offset points",
                ha="right", fontsize=8.5, color=th["muted"])
    ax.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)], color=th["ink"], fontsize=9.5)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("nMAE, % of capacity (lower is better)", color=th["muted"], fontsize=9)
    ax.set_title("How much of the wind benefit survives a realistic forecast", loc="left", fontsize=11,
                 color=th["ink"], fontweight="bold", pad=24)
    for x, label, kw in [(0.0, "no wind", dict(facecolor=th["bg"], edgecolor=th["muted"], linewidth=2)),
                         (0.2, "noisy wind forecast", dict(marker="s", color=th["muted"], alpha=0.55)),
                         (0.47, "ERA5 wind", dict(color=th["muted"]))]:
        ax.scatter([x], [1.06], s=40, transform=ax.transAxes, clip_on=False, **kw)
        ax.text(x + 0.02, 1.06, label, transform=ax.transAxes, va="center", fontsize=8.5, color=th["muted"])
    save(fig, "noisy_wind", theme)


def example_day(ex, th, theme, fid=EXAMPLE_FAMILY):
    """One day of the six 4-hourly runs over the actual output."""
    lab, mkey = next((lab, key) for f, lab, key in FAMILIES if f == fid)
    fig, (ax,) = new_fig(th, 11, 3.8)
    act = pd.DataFrame(ex["actual"], columns=["t", "y"])
    act["t"] = pd.to_datetime(act["t"])
    ax.plot(act["t"], act["y"], color=th["ink"], linewidth=1.8, label="actual output")
    act_at = dict(zip(act["t"], act["y"]))
    for runs, key, kw in [(ex["runs"]["persistence"], "pers", dict(linestyle=(0, (1, 3)), linewidth=1.5)),
                          (ex["runs"][fid + FUT_SUFFIX], mkey, dict(linewidth=2))]:
        r = pd.DataFrame(runs, columns=["t", "run", "lo", "med", "hi"])
        r["t"] = pd.to_datetime(r["t"])
        for _, g in r.groupby("run"):
            t0 = g["t"].iloc[0] - pd.Timedelta("15min")
            ts = pd.concat([pd.Series([t0]), g["t"]]) if t0 in act_at else g["t"]
            pad = [act_at[t0]] if t0 in act_at else []
            if key == mkey:
                ax.fill_between(ts, pad + list(g["lo"]), pad + list(g["hi"]), color=th[key], alpha=0.18, linewidth=0)
                if pad:
                    ax.scatter([t0], pad, s=18, facecolor=th["bg"], edgecolor=th[key], linewidth=1.5, zorder=4)
            ax.plot(ts, pad + list(g["med"]), color=th[key], **kw)
    ax.plot([], [], color=th[mkey], linewidth=2, label=f"{lab} + future wind, median and 80% band")
    ax.plot([], [], color=th["pers"], linestyle=(0, (1, 3)), linewidth=1.5, label="persistence")
    day = pd.Timestamp(ex["day"])
    for h in range(0, 24, 4):
        ax.axvline(day + pd.Timedelta(hours=h), color=th["grid"], linewidth=1)
    ax.set_ylim(0, PLANTS[PLANT]["capacity"])
    ax.set_ylabel("output, MW", color=th["muted"], fontsize=9)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.set_title(f"Six real time runs on {ex['day']}, each issued at a grey line", loc="left", fontsize=11,
                 color=th["ink"], fontweight="bold", pad=10)
    leg = ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1), frameon=False, fontsize=8.5, ncol=3)
    for t in leg.get_texts():
        t.set_color(th["muted"])
    save(fig, "example_day", theme)


def main(argv=None):
    m = pd.read_csv(RESULTS_DIR / "metrics.csv")
    m = m[(m.plant == PLANT) & (m.scoring == "all")]
    ex = json.loads((RESULTS_DIR / "metrics.json").read_text())["examples"][PLANT]
    for theme, th in THEMES.items():
        lead_time(m, th, theme)
        wind_gain(m, th, theme)
        noisy_wind(m, th, theme)
        example_day(ex, th, theme)
    print(f"wrote {len(list(OUT.glob('*.png')))} figures to {OUT}")


if __name__ == "__main__":
    main()
