"""Command-line entry point: python -m windbench <step> [options].

Steps, in order:
  prepare   download the ENGIE data and build the 15-minute series
  tune      choose history length and time of day per foundation model (validation window)
  backtest  run every model over the test year (options: --models, --append, --quick N)
  evaluate  score the forecasts, bootstrap confidence intervals and pairwise tests
  report    build results/report.html and docs/index.html
  figures   render the README charts into docs/figures
  all       every step above in order
"""
import sys

STEPS = ["prepare", "tune", "backtest", "evaluate", "report", "figures"]


def run(step: str, argv: list[str]) -> None:
    if step == "prepare":
        from .data import prepare
        prepare()
    elif step == "tune":
        from .tune import main
        main(argv)
    elif step == "backtest":
        from .backtest import main
        main(argv)
    elif step == "evaluate":
        from .evaluate import main
        main(argv)
    elif step == "report":
        from .report import main
        main(argv)
    elif step == "figures":
        from .figures import main
        main(argv)
    else:
        raise SystemExit(f"unknown step {step!r}\n\n{__doc__}")


def cli() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    step, argv = sys.argv[1], sys.argv[2:]
    for s in (STEPS if step == "all" else [step]):
        print(f"\n=== {s} ===")
        run(s, argv if s == step else [])


if __name__ == "__main__":
    cli()
