# Code structure

The benchmark is a small Python package. Every step is run through one command line entry point, `python -m windbench <step>`, described in the [main README](../README.md#running-the-benchmark).

<table>
  <thead><tr><th>Path</th><th>Contents</th></tr></thead>
  <tbody>
    <tr><td><code>config.py</code></td><td>paths, plant settings, schedule, quantiles and model names</td></tr>
    <tr><td><code>data.py</code></td><td>download and preparation of the 15 minute plant series</td></tr>
    <tr><td><code>covariates.py</code></td><td>time of day and the noisy wind forecast</td></tr>
    <tr><td><code>baselines.py</code></td><td>persistence and the power curve</td></tr>
    <tr><td><code>foundation.py</code></td><td>t0-alpha, t0-beta, Chronos-2 and TimesFM 3.0 behind one interface</td></tr>
    <tr><td><code>xgb_model.py</code></td><td>XGBoost features, training and prediction</td></tr>
    <tr><td><code>tune.py</code></td><td>validation tuning of the foundation models</td></tr>
    <tr><td><code>backtest.py</code></td><td>the rolling 4 hourly backtest</td></tr>
    <tr><td><code>evaluate.py</code></td><td>metrics, bootstrap intervals and pairwise tests</td></tr>
    <tr><td><code>report.py</code></td><td>builds the interactive HTML report from <code>templates/report.html</code></td></tr>
    <tr><td><code>figures.py</code></td><td>renders the README charts for light and dark themes</td></tr>
    <tr><td><code>../results/</code></td><td>metrics, tuning choices and timings from the published run</td></tr>
    <tr><td><code>../docs/index.html</code></td><td>the interactive report, served by GitHub Pages</td></tr>
    <tr><td><code>../docs/figures/</code></td><td>the charts shown in the main README</td></tr>
  </tbody>
</table>

## Command options

1. `python -m windbench tune --models t0-beta` tunes only the named foundation models and keeps the saved choices of the others.
2. `python -m windbench backtest --models persistence "t0-alpha + future wind"` runs only the named model variants. Variant names are the model name alone for setup A, with ` + future wind` for setup B and with ` + noisy wind` for the realistic wind test.
3. `--append` replaces only those variants in the existing results instead of starting over.
4. `--quick 24` runs only the first 24 forecasts, as a quick check that everything works.
5. Set the `WINDBENCH_RESULTS` environment variable to write results to another folder.

The first run downloads the model weights from Hugging Face. Results can differ from the committed ones by about 0.00001 MW because of floating point differences between devices.

## Notes

XGBoost is trained in a separate Python process because XGBoost and PyTorch each bundle their own OpenMP runtime, and loading both in one process crashes on macOS.
