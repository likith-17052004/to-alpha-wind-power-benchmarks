"""windbench: real-time wind power forecasting benchmark for time-series foundation models.

Keep this module free of heavy imports: the XGBoost step runs in its own interpreter and
must never load PyTorch (both bundle libomp, and sharing a process segfaults on macOS).
"""
