# WindBench

**Can time series foundation models replace a wind farm's real time power forecast?**

WindBench compares three zero shot time series foundation models (t0-alpha, Chronos-2 and TimesFM 3.0) with a gradient boosted model trained on the plant's own history (XGBoost) and two simple baselines, on a real wind farm, run the way Indian real time scheduling works: every 4 hours, forecast the next 16 blocks of 15 minutes.

Everything runs on a laptop. The full benchmark (tuning, 15 model variants, 2,189 forecast runs each) takes under an hour on an Apple M5.

**Interactive report:** [likith-17052004.github.io/to-alpha-wind-power-benchmarks](https://likith-17052004.github.io/to-alpha-wind-power-benchmarks/) (or open [`docs/index.html`](docs/index.html) locally) with every metric, a lead time explorer, pairwise significance tests and a day of real time runs.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/lead_time_dark.png">
  <img alt="Forecast error at every lead time from 15 minutes to 4 hours, for past power only and for past power plus future wind" src="docs/figures/lead_time_light.png">
</picture>

## Key findings

1. **With past power alone, nothing meaningfully beats persistence.** Every model, foundation or trained, improves on holding the last value flat by only 2.6 to 4.3 percent, and within that group most differences are not statistically significant.
2. **Knowing the wind over the next 4 hours is what matters.** Adding it cuts every model's error by 0.55 to 0.97 percentage points of capacity, and the gain grows with lead time.
3. **Zero shot foundation models match a model trained on the plant.** With future wind, TimesFM 3.0 is the most accurate model (5.80% nMAE), significantly better than XGBoost (6.00%). t0-alpha (6.09%) is statistically indistinguishable from XGBoost.
4. **Forecast quality decides the ranking among deployable models.** With a realistic, noisy wind forecast, Chronos-2 and XGBoost tie (6.31% and 6.30%) while t0-alpha, which leans most on the wind input, keeps only about half of its gain (6.44%).
5. **None of them is ready to replace an operational forecast as is.** The best models still miss by about 7.3% of capacity on average at 4 hours ahead, and large errors come from real weather ramps that no model anticipates.

## Results

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/wind_gain_dark.png">
  <img alt="Change in error from adding the future wind, at every lead time, per model" src="docs/figures/wind_gain_light.png">
</picture>

ENGIE La Haute Borne wind farm (4 turbines, 8.2 MW), test year 2015, one run every 4 hours, 2,189 runs per model. nMAE is the mean absolute error of the median forecast as a percentage of installed capacity; skill is the reduction in that error versus persistence.

<table>
  <thead>
    <tr><th>Setup</th><th>Model</th><th>nMAE %</th><th>Skill vs persistence</th><th>nMAE at 15 min</th><th>nMAE at 4 h</th><th>ms per run</th></tr>
  </thead>
  <tbody>
    <tr><td rowspan="5">B: past power and future wind</td><td>TimesFM 3.0 (zero shot)</td><td><b>5.80</b></td><td><b>17.7%</b></td><td><b>2.63</b></td><td>7.37</td><td>34</td></tr>
    <tr><td>XGBoost (trained on the plant)</td><td>6.00</td><td>14.8%</td><td>2.87</td><td><b>7.31</b></td><td>8</td></tr>
    <tr><td>t0-alpha (zero shot)</td><td>6.09</td><td>13.6%</td><td>2.81</td><td>7.68</td><td>96</td></tr>
    <tr><td>Chronos-2 (zero shot)</td><td>6.19</td><td>12.1%</td><td>2.75</td><td>8.02</td><td>41</td></tr>
    <tr><td>Power curve (baseline)</td><td>7.70</td><td>minus 9.2%</td><td>7.52</td><td>7.59</td><td>0</td></tr>
    <tr><td rowspan="5">A: past power only</td><td>Chronos-2 (zero shot)</td><td><b>6.75</b></td><td><b>4.3%</b></td><td>2.78</td><td><b>9.03</b></td><td>44</td></tr>
    <tr><td>TimesFM 3.0 (zero shot)</td><td>6.77</td><td>3.9%</td><td><b>2.68</b></td><td>9.06</td><td>90</td></tr>
    <tr><td>t0-alpha (zero shot)</td><td>6.81</td><td>3.4%</td><td>2.72</td><td>9.10</td><td>25</td></tr>
    <tr><td>XGBoost (trained on the plant)</td><td>6.87</td><td>2.6%</td><td>2.84</td><td>9.10</td><td>7</td></tr>
    <tr><td>Persistence (baseline)</td><td>7.05</td><td>0%</td><td>2.72</td><td>9.62</td><td>0</td></tr>
  </tbody>
</table>

**With a realistic wind forecast** (setup B with the wind degraded by timing, level and drift errors):

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/noisy_wind_dark.png">
  <img alt="Error of each model with no wind, a noisy wind forecast and ERA5 wind" src="docs/figures/noisy_wind_light.png">
</picture>

<table>
  <thead>
    <tr><th>Model</th><th>A: no wind</th><th>B: noisy wind</th><th>B: ERA5 wind</th><th>Share of the wind gain kept</th></tr>
  </thead>
  <tbody>
    <tr><td>TimesFM 3.0</td><td>6.77</td><td><b>6.08</b></td><td>5.80</td><td>72%</td></tr>
    <tr><td>XGBoost</td><td>6.87</td><td>6.30</td><td>6.00</td><td>66%</td></tr>
    <tr><td>Chronos-2</td><td>6.75</td><td>6.31</td><td>6.19</td><td>78%</td></tr>
    <tr><td>t0-alpha</td><td>6.81</td><td>6.44</td><td>6.09</td><td>52%</td></tr>
  </tbody>
</table>

**What a real time run looks like.** Each 4 hourly run of t0-alpha with future wind starts from the last measured block (open circle) and forecasts the next 4 hours with an 80% band. The forecasts follow the level well but, like every model here, miss the sharp ramps.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/example_day_dark.png">
  <img alt="Six consecutive 4 hourly t0-alpha runs over the actual output on 1 April 2015" src="docs/figures/example_day_light.png">
</picture>

Excluding the 4.4% of blocks affected by turbine outages or curtailment lowers every error by about 0.04 points and leaves the ranking unchanged. The interactive report adds error at every step from 15 minutes to 4 hours, a pairwise significance matrix, the tuning choices and a day of real time runs.

## How the benchmark works

**Schedule.** A forecast is issued at 00, 04, 08, 12, 16 and 20 UTC. Each run sees the plant's actual output up to the moment it is issued, including the 16 blocks measured since the previous run, and predicts the next 16 blocks of 15 minutes. Errors are scored per block, as a percentage of installed capacity, similar to how Indian deviation settlement measures wind deviations.

**Input setups.**

1. **A: past power only.** The plant's own output history and nothing else.
2. **B: past power and future wind.** The same history plus the wind speed over the next 4 hours. ERA5 reanalysis at 100 m stands in for the wind forecast a plant would receive.
3. **B with noisy wind.** A sensitivity test in which ERA5 is degraded into something closer to an operational forecast: per run a timing error of up to one hour, a level bias and an error that drifts over the horizon. Every model sees the identical noisy series, and XGBoost is trained on equally noisy wind.

**Models.**

<table>
  <thead><tr><th>Model</th><th>Kind</th><th>Size</th><th>Weights license</th></tr></thead>
  <tbody>
    <tr><td><a href="https://huggingface.co/theforecastingcompany/t0-alpha">t0-alpha</a> (The Forecasting Company)</td><td>zero shot foundation model</td><td>102M</td><td>Apache 2.0</td></tr>
    <tr><td><a href="https://huggingface.co/amazon/chronos-2">Chronos-2</a> (Amazon)</td><td>zero shot foundation model</td><td>120M</td><td>Apache 2.0</td></tr>
    <tr><td><a href="https://huggingface.co/google/timesfm-3.0-pytorch">TimesFM 3.0</a> (Google)</td><td>zero shot foundation model</td><td>330M</td><td>TimesFM Non Commercial License</td></tr>
    <tr><td>XGBoost</td><td>trained on the plant's 2014 history</td><td>400 trees</td><td>Apache 2.0</td></tr>
    <tr><td>Persistence</td><td>last value held flat</td><td></td><td></td></tr>
    <tr><td>Power curve</td><td>ERA5 wind mapped to power, fitted on 2014</td><td></td><td></td></tr>
  </tbody>
</table>

**Fairness.** Every model gets the same test runs, the same inputs within a setup and the same scoring. Each model also gets the same validation budget on October to December 2014, and the 2015 test year is never used to choose anything:

1. The foundation models choose their history length (512, 1,024, 2,048 or 4,096 blocks) and whether to receive the time of day, which XGBoost always has, as a known future input.
2. XGBoost's design was chosen on the same split. It predicts the change from the last observed block, so it starts from the latest actual value, and it leaves out day of year, which with a single training year only memorises that year's weather.

**Statistics.** Confidence intervals come from a bootstrap over whole days, paired across models, so every comparison is made on the same resampled days. The probabilistic score (nCRPS) and the 80% interval coverage are computed from the nine forecast deciles.

## Quick start

Requires Python 3.10 or newer and about 3 GB of disk for the model weights. On an Apple Silicon Mac the foundation models run on the GPU through MPS; CUDA and CPU also work.

```bash
git clone https://github.com/likith-17052004/to-alpha-wind-power-benchmarks.git
cd to-alpha-wind-power-benchmarks
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m windbench all
```

`all` runs the six steps below in order. They can also be run one at a time:

<table>
  <thead><tr><th>Command</th><th>What it does</th><th>Time on an Apple M5</th></tr></thead>
  <tbody>
    <tr><td><code>python -m windbench prepare</code></td><td>downloads the ENGIE data (37 MB) and builds the 15 minute series</td><td>under a minute</td></tr>
    <tr><td><code>python -m windbench tune</code></td><td>picks history length and time of day per foundation model on the validation window</td><td>about 20 minutes</td></tr>
    <tr><td><code>python -m windbench backtest</code></td><td>runs all 15 model variants over the 2015 test year</td><td>about 20 minutes</td></tr>
    <tr><td><code>python -m windbench evaluate</code></td><td>scores the forecasts, bootstraps confidence intervals and pairwise tests</td><td>about a minute</td></tr>
    <tr><td><code>python -m windbench report</code></td><td>builds <code>results/report.html</code> and <code>docs/index.html</code></td><td>seconds</td></tr>
    <tr><td><code>python -m windbench figures</code></td><td>renders the README charts into <code>docs/figures</code></td><td>seconds</td></tr>
  </tbody>
</table>

Useful backtest options: `--models` runs a subset (for example `--models persistence "t0-alpha + future wind"`), `--append` replaces only those models in the existing results, and `--quick 24` runs only the first 24 forecasts as a smoke test. Set `WINDBENCH_RESULTS` to write results to another folder.

The first run downloads the model weights from Hugging Face. Your results can differ from the committed ones by about 0.00001 MW because of floating point differences between devices.

## Repository layout

<table>
  <thead><tr><th>Path</th><th>Contents</th></tr></thead>
  <tbody>
    <tr><td><code>windbench/config.py</code></td><td>paths, plant settings, schedule, quantiles and model names</td></tr>
    <tr><td><code>windbench/data.py</code></td><td>download and preparation of the 15 minute plant series</td></tr>
    <tr><td><code>windbench/covariates.py</code></td><td>time of day and the noisy wind forecast</td></tr>
    <tr><td><code>windbench/baselines.py</code></td><td>persistence and the power curve</td></tr>
    <tr><td><code>windbench/foundation.py</code></td><td>t0-alpha, Chronos-2 and TimesFM 3.0 behind one interface</td></tr>
    <tr><td><code>windbench/xgb_model.py</code></td><td>XGBoost features, training and prediction</td></tr>
    <tr><td><code>windbench/tune.py</code></td><td>validation tuning of the foundation models</td></tr>
    <tr><td><code>windbench/backtest.py</code></td><td>the rolling 4 hourly backtest</td></tr>
    <tr><td><code>windbench/evaluate.py</code></td><td>metrics, bootstrap intervals and pairwise tests</td></tr>
    <tr><td><code>windbench/report.py</code></td><td>builds the interactive HTML report from <code>templates/report.html</code></td></tr>
    <tr><td><code>windbench/figures.py</code></td><td>renders the README charts for light and dark themes</td></tr>
    <tr><td><code>results/</code></td><td>metrics, tuning choices and timings from the published run</td></tr>
    <tr><td><code>docs/index.html</code></td><td>the interactive report, served by GitHub Pages</td></tr>
    <tr><td><code>docs/figures/</code></td><td>the charts shown in this README</td></tr>
  </tbody>
</table>

XGBoost is trained in a separate Python process because XGBoost and PyTorch each bundle their own OpenMP runtime, and loading both in one process crashes on macOS.

## Limitations

1. **One plant, one test year.** An 8.2 MW inland site in France in 2015. The ranking may not carry over to other sites, climates or schedules.
2. **Possible pretraining exposure.** The dataset ships with a widely used open source library, so it may be part of some foundation models' training data. That would flatter the foundation models, not XGBoost. Only data from an unseen plant rules this out.
3. **ERA5 is not a forecast.** It is a reanalysis of what actually happened, so setup B is an optimistic upper bound. The noisy wind test narrows the gap but is not a substitute for archived operational forecasts.
4. **Zero shot only.** The foundation models are not fine tuned on the plant, which is where they would usually gain most.
5. **TimesFM 3.0 cannot be deployed commercially.** Its weights are licensed for non commercial use only; it is included as a research reference.

## Data and licenses

The wind farm data is the ENGIE La Haute Borne dataset, published by ENGIE under the French Open Licence 2.0 (Etalab) and redistributed in the example data of NREL's [OpenOA](https://github.com/NatLabRockies/OpenOA). It is downloaded at run time and not stored in this repository.

Model weights are downloaded from Hugging Face and remain under their own licenses: t0-alpha and Chronos-2 under Apache 2.0, TimesFM 3.0 under the TimesFM Non Commercial License. The forecasts in `results/` were produced for non commercial research and benchmarking.

## License

The code is released under the [MIT License](LICENSE). Data and model weights keep their own licenses, listed above.

## Acknowledgements

Thanks to ENGIE for opening the La Haute Borne data, to the OpenOA maintainers for keeping it available, and to The Forecasting Company, Amazon and Google for releasing their models.
