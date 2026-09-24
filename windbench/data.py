"""Download the ENGIE La Haute Borne data and build the 15-minute plant series.

Output: data/processed/engie_lhb_15min.parquet with columns
  power_mw   plant net output, 15-min average (MW)
  era5_ws    ERA5 100 m wind speed at the block centre (m/s), the stand-in wind forecast
  available  False where turbine unavailability or curtailment touched the block
"""
import io
import urllib.request
import zipfile

import numpy as np
import pandas as pd

from .config import OPENOA_ZIP_URL, PLANTS, PROCESSED_DIR, RAW_DIR

REQUIRED = ["plant_data.csv", "era5_wind_la_haute_borne.csv"]


def download() -> None:
    """Fetch and unpack the OpenOA copy of the dataset (about 37 MB) unless it is already present."""
    if all((RAW_DIR / f).exists() for f in REQUIRED):
        print(f"raw data present in {RAW_DIR}")
        return
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"downloading {OPENOA_ZIP_URL}")
    with urllib.request.urlopen(OPENOA_ZIP_URL) as r:
        blob = r.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for member in z.namelist():
            if member.endswith(".csv") and not member.startswith("__MACOSX"):
                (RAW_DIR / member.split("/")[-1]).write_bytes(z.read(member))
    print(f"extracted to {RAW_DIR}")


def to_15min(p10: pd.Series) -> pd.Series:
    """10-min average power to 15-min average power.

    Each 10-min value is split into two 5-min halves; a 15-min block is the mean of its three
    5-min halves and is NaN unless all three are present.
    """
    p10 = p10.asfreq("10min")
    p5 = p10.resample("5min").ffill(limit=1)
    p5[p10.reindex(p5.index, method="ffill", limit=1).isna()] = np.nan
    return p5.resample("15min").mean().where(p5.resample("15min").count() == 3)


def _plant_table() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "plant_data.csv", parse_dates=["time_utc"]).set_index("time_utc")
    df.index = df.index.tz_convert(None)
    return df


def load_power(plant: pd.DataFrame) -> pd.Series:
    return plant["net_energy_kwh"] * 6 / 1000  # kWh per 10 min to MW


def load_era5_ws(index: pd.DatetimeIndex) -> pd.Series:
    """ERA5 100 m wind speed (hourly, instantaneous) interpolated to each block centre."""
    e = pd.read_csv(RAW_DIR / "era5_wind_la_haute_borne.csv", parse_dates=["datetime"])
    e = e.set_index("datetime").sort_index()["ws_100m"]
    centres = (index + pd.Timedelta("7.5min")).asi8
    return pd.Series(np.interp(centres, e.index.asi8, e.to_numpy()), index=index, name="era5_ws")


def load_available(plant: pd.DataFrame, index: pd.DatetimeIndex, cap: float) -> pd.Series:
    """False for blocks touched by unavailability or curtailment above 1% of full-output energy."""
    lost = (plant["availability_kwh"] + plant["curtailment_kwh"]) > 0.01 * cap * 1000 / 6
    # a block [t, t+15) overlaps the 10-min slots starting at t-10 (partly), t and t+10 (partly)
    affected = lost.resample("5min").ffill().resample("15min").max()
    return ~affected.reindex(index, fill_value=False).astype(bool)


def prepare() -> None:
    download()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    key = "engie_lhb"
    cap = PLANTS[key]["capacity"]
    plant = _plant_table()
    s15 = to_15min(load_power(plant))
    # net output can dip slightly below zero (idle consumption); drop physically impossible values
    s15[(s15 < -0.05 * cap) | (s15 > 1.05 * cap)] = np.nan
    df = s15.rename("power_mw").to_frame()
    df["era5_ws"] = load_era5_ws(df.index)
    df["available"] = load_available(plant, df.index, cap)
    df.to_parquet(PROCESSED_DIR / f"{key}_15min.parquet")
    print(f"{key}: {s15.index.min()} to {s15.index.max()}, {len(s15)} blocks, "
          f"{s15.isna().mean():.2%} missing, mean {s15.mean():.2f} MW, capacity factor {s15.mean() / cap:.1%}")


def load(plant: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / f"{plant}_15min.parquet")
