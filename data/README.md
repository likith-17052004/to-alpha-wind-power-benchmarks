# Data

This folder is filled by `python -m windbench prepare`, which downloads the ENGIE La Haute Borne dataset as redistributed in the example data of NREL's [OpenOA](https://github.com/NatLabRockies/OpenOA) library and builds the 15 minute plant series.

After preparation the folder contains:

1. `raw/engie/` the unpacked OpenOA files: plant meter data with availability and curtailment losses, turbine SCADA data and ERA5 and MERRA2 reanalysis.
2. `processed/engie_lhb_15min.parquet` the benchmark input: plant output in MW, ERA5 wind speed at 100 m, and an availability flag per 15 minute block.

The data were published by ENGIE under the French Open Licence 2.0 (Etalab), which allows reuse, including commercial reuse, with attribution. It is not committed to this repository.
