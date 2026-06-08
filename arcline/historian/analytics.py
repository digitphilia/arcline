# -*- encoding: utf-8 -*-

"""
Historian Analytics
-------------------

Baseline univariate analytics over the ``[ts, value]`` DataFrames
returned by :func:`arcline.historian.fetcher.fetch`. Returns plain
:mod:`pandas` objects so callers (CLI, dashboard) can feed Plotly
traces without an adapter.

Deeper analytics - outlier detection, changepoints, forecasting,
cross-attribute correlation - are intentionally deferred to a future
phase per CLAUDE.md section 6.4.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

ResampleFreq = Literal["D", "W", "M", "Q", "Y"]


def _importPandas() -> Any:
    import pandas as pd
    return pd


def _validateFrame(frame: Any) -> None:
    if "value" not in frame.columns:
        raise ValueError("frame must have a 'value' column")


def summary(frame: Any) -> Dict[str, Any]:
    """
    Return a dictionary of univariate summary statistics for ``frame``.

    Keys: ``count``, ``min``, ``max``, ``mean``, ``std``, ``median``,
    ``p5``, ``p25``, ``p75``, ``p95``, ``last``, ``lastTs``.
    All numeric outputs are plain Python floats (or ``None`` when the
    input is empty) so they JSON-serialize cleanly into Dash stores.
    """
    _validateFrame(frame)
    if frame.empty:
        return {
            "count": 0, "min": None, "max": None, "mean": None,
            "std": None, "median": None, "p5": None, "p25": None,
            "p75": None, "p95": None, "last": None, "lastTs": None,
        }
    series = frame["value"].astype(float)
    quantiles = series.quantile([0.05, 0.25, 0.50, 0.75, 0.95])
    out: Dict[str, Any] = {
        "count": int(series.count()),
        "min": float(series.min()),
        "max": float(series.max()),
        "mean": float(series.mean()),
        "std": float(series.std(ddof = 0)) if len(series) > 1 else 0.0,
        "median": float(quantiles.loc[0.50]),
        "p5": float(quantiles.loc[0.05]),
        "p25": float(quantiles.loc[0.25]),
        "p75": float(quantiles.loc[0.75]),
        "p95": float(quantiles.loc[0.95]),
        "last": float(series.iloc[-1]),
        "lastTs": None,
    }
    if "ts" in frame.columns and not frame["ts"].empty:
        out["lastTs"] = str(frame["ts"].iloc[-1])
    return out


def rolling(frame: Any, window: int = 7) -> Any:
    """
    Return ``frame`` augmented with rolling mean and standard deviation.

    Output columns: ``ts``, ``value``, ``rollingMean``, ``rollingStd``.
    The window is right-aligned (default 7 periods); minimum-periods
    equals 1 so the head of the series is populated rather than NaN.
    """
    _validateFrame(frame)
    if window < 1:
        raise ValueError("window must be >= 1")
    pd = _importPandas()
    out = frame.copy()
    series = out["value"].astype(float)
    out["rollingMean"] = series.rolling(window, min_periods = 1).mean()
    out["rollingStd"] = series.rolling(window, min_periods = 1).std(ddof = 0).fillna(0.0)
    return out


def distribution(frame: Any, bins: int = 20) -> Any:
    """
    Return a histogram DataFrame with ``binStart``, ``binEnd``, ``count``.

    Empty / single-value inputs degrade gracefully into a single
    zero-width bin with the appropriate count.
    """
    _validateFrame(frame)
    pd = _importPandas()
    if frame.empty:
        return pd.DataFrame(columns = ["binStart", "binEnd", "count"])
    series = frame["value"].astype(float)
    if series.min() == series.max():
        v = float(series.iloc[0])
        return pd.DataFrame(
            [{"binStart": v, "binEnd": v, "count": int(series.count())}]
        )
    import numpy as np
    countsArr, binEdges = np.histogram(series.to_numpy(), bins = bins)
    return pd.DataFrame({
        "binStart": binEdges[:-1],
        "binEnd": binEdges[1:],
        "count": countsArr.astype(int),
    })


def resample(frame: Any, freq: ResampleFreq = "D", how: str = "mean") -> Any:
    """
    Resample ``frame[['ts','value']]`` to ``freq`` using aggregation ``how``.

    ``freq`` accepts the standard pandas offset aliases (``"D"``,
    ``"W"``, ``"M"``, ``"Q"``, ``"Y"``). ``how`` may be any aggregation
    name supported by :meth:`pandas.core.resample.Resampler.agg`
    (e.g. ``"mean"``, ``"sum"``, ``"max"``).
    """
    _validateFrame(frame)
    if "ts" not in frame.columns:
        raise ValueError("frame must have a 'ts' column to resample")
    pd = _importPandas()
    indexed = frame.set_index(pd.to_datetime(frame["ts"]))[["value"]]
    aggregated = indexed.resample(freq).agg(how).reset_index()
    aggregated = aggregated.rename(columns = {"index": "ts"})
    if "ts" not in aggregated.columns:
        aggregated.insert(0, "ts", aggregated.index)
    return aggregated
