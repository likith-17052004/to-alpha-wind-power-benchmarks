# Code structure

The benchmark is a small Python package. Every step is run through one command line entry point, `python -m windbench <step>`, described in the [main README](../README.md#quick-start).

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

XGBoost is trained in a separate Python process because XGBoost and PyTorch each bundle their own OpenMP runtime, and loading both in one process crashes on macOS.
