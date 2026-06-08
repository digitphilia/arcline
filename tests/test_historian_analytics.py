# -*- encoding: utf-8 -*-

"""
Phase 1.5 - P15-4 (analytics) tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from arcline.historian import distribution, resample, rolling, summary


def makeFrame(values, start = "2024-01-01", periods = None) -> pd.DataFrame:
    if periods is None:
        periods = len(values)
    return pd.DataFrame({
        "ts": pd.date_range(start, periods = periods, freq = "D"),
        "value": values,
    })


def test_summary_emptyFrameReturnsZeroCount():
    out = summary(pd.DataFrame({"value": []}))
    assert out["count"] == 0
    assert out["mean"] is None
    assert out["last"] is None


def test_summary_basicStats():
    out = summary(makeFrame([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert out["count"] == 5
    assert out["min"] == 1.0
    assert out["max"] == 5.0
    assert out["mean"] == pytest.approx(3.0)
    assert out["median"] == 3.0
    assert out["last"] == 5.0
    assert out["lastTs"] is not None


def test_summary_quantiles():
    out = summary(makeFrame(list(range(1, 101))))
    assert out["p5"] == pytest.approx(5.95, rel = 1e-2)
    assert out["p95"] == pytest.approx(95.05, rel = 1e-2)
    assert out["p25"] == pytest.approx(25.75, rel = 1e-2)
    assert out["p75"] == pytest.approx(75.25, rel = 1e-2)


def test_summary_rejectsFrameWithoutValueColumn():
    with pytest.raises(ValueError):
        summary(pd.DataFrame({"x": [1, 2]}))


def test_rolling_meanAndStdColumns():
    frame = makeFrame([1.0, 2.0, 3.0, 4.0, 5.0])
    out = rolling(frame, window = 3)
    assert "rollingMean" in out.columns
    assert "rollingStd" in out.columns
    assert out["rollingMean"].iloc[0] == 1.0
    assert out["rollingMean"].iloc[2] == pytest.approx(2.0)
    assert out["rollingMean"].iloc[4] == pytest.approx(4.0)


def test_rolling_invalidWindow():
    with pytest.raises(ValueError):
        rolling(makeFrame([1.0]), window = 0)


def test_distribution_basicHistogram():
    frame = makeFrame(list(range(100)))
    out = distribution(frame, bins = 10)
    assert len(out) == 10
    assert int(out["count"].sum()) == 100
    assert (out["binEnd"] > out["binStart"]).all()


def test_distribution_emptyFrameReturnsEmpty():
    out = distribution(pd.DataFrame({"value": []}))
    assert out.empty
    assert list(out.columns) == ["binStart", "binEnd", "count"]


def test_distribution_constantSeries():
    out = distribution(makeFrame([5.0, 5.0, 5.0, 5.0]))
    assert len(out) == 1
    assert out["count"].iloc[0] == 4
    assert out["binStart"].iloc[0] == 5.0


def test_resample_dailyToWeekly():
    frame = makeFrame([float(i) for i in range(14)])
    out = resample(frame, freq = "W", how = "mean")
    assert len(out) <= 4
    assert "value" in out.columns
    assert "ts" in out.columns


def test_resample_requiresTsColumn():
    with pytest.raises(ValueError):
        resample(pd.DataFrame({"value": [1.0]}), freq = "D")


def test_resample_sumAggregation():
    frame = makeFrame([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
    out = resample(frame, freq = "W", how = "sum")
    assert out["value"].sum() == pytest.approx(28.0)
