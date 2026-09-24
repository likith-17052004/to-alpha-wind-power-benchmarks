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
EXAMPLE_FAMILIES = ("t0-alpha", "t0-beta")  # one panel each, with future wind, in the example day chart


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
    """How much knowing the wind over the next 4 hours cuts each model's own error, by lead time."""
    fig, (ax,) = new_fig(th, 8.5, 4.4)
    steps = np.arange(1, 17)
    get = lambda model: m[(m.model == model) & (m.step > 0)].sort_values("step")["nMAE"].to_numpy()  # noqa: E731
    labels, finals = [], []
    for fid, lab, key in FAMILIES:
        without, with_wind = get(fid), get(fid + FUT_SUFFIX)
        cut = 100 * (without - with_wind) / without  # % of the model's own error removed
        ax.plot(steps, cut, color=th[key], linewidth=2.2, solid_capstyle="round")
        labels.append((f"{lab}  {cut[-1]:.0f}%", cut[-1], th[key]))
        finals.append(cut[-1])
    ax.axhline(0, color=th["muted"], linewidth=1)
    ax.text(16, 0.6, "no benefit", ha="right", va="bottom", fontsize=8.5, color=th["muted"])
    ax.set_ylim(-5, max(finals) + 3)
    ax.set_yticks(np.arange(0, max(finals) + 3, 5))
    end_labels(ax, labels, th, 16)
    ax.annotate("15 min ahead: the latest measured\npower already says almost everything",
                xy=(1.1, 1), xytext=(1.6, 12.5), fontsize=8.5, color=th["muted"], va="center",
                arrowprops=dict(arrowstyle="-", color=th["muted"], linewidth=0.8,
                                connectionstyle="angle3,angleA=0,angleB=80"))
    ax.set_xticks(STEP_TICKS, STEP_LABELS)
    ax.set_xlim(1, 16)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("how far ahead the forecast is", color=th["muted"], fontsize=9)
    ax.set_ylabel("error removed by the wind forecast", color=th["muted"], fontsize=9)
    fig.text(ax.get_position().x0, 0.99,
             f"A wind forecast barely helps at 15 minutes, but cuts error by {min(finals):.0f} to "
             f"{max(finals):.0f}% at 4 hours", fontsize=11.5, color=th["ink"], fontweight="bold", va="top")
    fig.text(ax.get_position().x0, 0.925, "Each model with the wind speed for the next 4 hours, compared with "
             "the same model using past power only. Higher is better.", fontsize=9, color=th["muted"], va="top")
    fig.subplots_adjust(top=0.84)
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


def example_day(ex, th, theme, fids=EXAMPLE_FAMILIES):
    """One day of the six 4-hourly runs over the actual output: one panel per model, same axes."""
    act = pd.DataFrame(ex["actual"], columns=["t", "y"])
    act["t"] = pd.to_datetime(act["t"])
    act_at = dict(zip(act["t"], act["y"]))
    cap = PLANTS[PLANT]["capacity"]
    day = pd.Timestamp(ex["day"])
    fig, axes = plt.subplots(len(fids), 1, figsize=(11, 2.9 * len(fids)), sharex=True, sharey=True, dpi=160)
    fig.patch.set_facecolor(th["bg"])
    for ax, fid in zip(np.atleast_1d(axes), fids):
        style(ax, th)
        lab, mkey = next((lab, key) for f, lab, key in FAMILIES if f == fid)
        ax.plot(act["t"], act["y"], color=th["ink"], linewidth=1.8)
        errs = []
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
                    errs += [abs(m - act_at[t]) for t, m in zip(g["t"], g["med"]) if t in act_at]
                ax.plot(ts, pad + list(g["med"]), color=th[key], **kw)
        for h in range(0, 24, 4):
            ax.axvline(day + pd.Timedelta(hours=h), color=th["grid"], linewidth=1)
        ax.set_title(f"{lab} + future wind", loc="left", fontsize=10, color=th[mkey], fontweight="bold", pad=6)
        ax.set_title(f"this day: {100 * np.mean(errs) / cap:.1f}% nMAE", loc="right", fontsize=8.5,
                     color=th["muted"], pad=6)
        ax.set_ylim(0, cap)
        ax.set_ylabel("output, MW", color=th["muted"], fontsize=9)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    fig.text(axes[0].get_position().x0, 0.965, f"Six real time runs on {ex['day']}, each issued at a grey line",
             fontsize=11, color=th["ink"], fontweight="bold")
    handles = [plt.Line2D([], [], color=th["ink"], linewidth=1.8),
               plt.Line2D([], [], color=th["muted"], linewidth=2),
               plt.Rectangle((0, 0), 1, 1, color=th["muted"], alpha=0.25, linewidth=0),
               plt.Line2D([], [], color=th["pers"], linestyle=(0, (1, 3)), linewidth=1.5)]
    leg = axes[-1].legend(handles, ["actual output", "forecast median", "80% band", "persistence"],
                          loc="upper left", bbox_to_anchor=(0, -0.14), frameon=False, fontsize=8.5, ncol=4)
    for t in leg.get_texts():
        t.set_color(th["muted"])
    fig.subplots_adjust(hspace=0.28, top=0.9)
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
