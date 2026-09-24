"""Paths and experiment settings shared by every step."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "engie"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = Path(os.environ.get("WINDBENCH_RESULTS", ROOT / "results"))
DOCS_DIR = ROOT / "docs"

# ENGIE La Haute Borne, as redistributed with NREL's OpenOA examples (Etalab Open Licence 2.0)
OPENOA_ZIP_URL = "https://raw.githubusercontent.com/NatLabRockies/OpenOA/main/examples/data/la_haute_borne.zip"

PLANTS = {
    # capacity in MW; the test year is the last year of data, everything before it is history
    "engie_lhb": {"name": "ENGIE La Haute Borne", "capacity": 8.2,
                  "test_start": "2015-01-01", "test_end": "2016-01-01"},
}

# Real-time schedule: a run every 4 hours, forecasting the next 16 blocks of 15 minutes
HORIZON = 16
RUN_EVERY = "4h"
QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

# Context handling
MAX_CONTEXT = 4096       # longest history tried in tuning (about 43 days)
DEFAULT_CONTEXT = 2048   # about 21 days; used before tuning and by persistence
MAX_CTX_MISSING = 0.10   # a run is skipped if more than 10% of its default context is missing
BATCH = 64

# Tuning on a validation window inside the year before the test
VAL_START, VAL_END = "2014-10-01", "2015-01-01"
CONTEXT_GRID = [512, 1024, 2048, 4096]

# Model naming: "<model>" = setup A, "<model> + future wind" = setup B,
# "<model> + noisy wind" = setup B with a degraded wind forecast
FOUNDATION_MODELS = ["t0-alpha", "chronos-2", "timesfm-3.0"]
FUT_SUFFIX = " + future wind"
NOISY_SUFFIX = " + noisy wind"
MODELS = ["persistence", "power-curve", "power-curve" + NOISY_SUFFIX,
          "xgboost", "xgboost" + FUT_SUFFIX, "xgboost" + NOISY_SUFFIX]
for _m in FOUNDATION_MODELS:
    MODELS += [_m, _m + FUT_SUFFIX, _m + NOISY_SUFFIX]


def split_model_name(name: str) -> tuple[str, str | None]:
    """'t0-alpha + noisy wind' -> ('t0-alpha', 'noisy'). The power curve always uses wind."""
    if name.endswith(NOISY_SUFFIX):
        return name[: -len(NOISY_SUFFIX)], "noisy"
    if name.endswith(FUT_SUFFIX):
        return name[: -len(FUT_SUFFIX)], "era5"
    return name, ("era5" if name == "power-curve" else None)
