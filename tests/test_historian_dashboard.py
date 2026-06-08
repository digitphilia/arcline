# -*- encoding: utf-8 -*-

"""
Phase 1.5 - P15-7 (dashboard) tests.

Smoke-only tests that import the page + callbacks module without
running the live Dash server (the full Dash testing harness is too
heavy for the CI baseline).
"""

from __future__ import annotations

import pytest

dash = pytest.importorskip("dash")


def test_historyPage_importable():
    from arcline.dashboard.pages import history as historyPage
    assert callable(historyPage.layout)


def test_historyCallback_importable():
    from arcline.dashboard.callbacks import history_cb
    assert callable(history_cb.register)


def test_navbar_includesDbStatusPill():
    from arcline.dashboard.components.navbar import makeNavbar
    navbar = makeNavbar("test")
    rendered = str(navbar)
    assert "db-status-pill" in rendered


def test_lttb_downsampleHonorsThreshold():
    import pandas as pd
    from arcline.dashboard.callbacks.history_cb import _lttbDownsample, LTTB_THRESHOLD
    n = LTTB_THRESHOLD + 100
    frame = pd.DataFrame({
        "ts": pd.date_range("2020-01-01", periods = n, freq = "h"),
        "value": list(range(n)),
    })
    out = _lttbDownsample(frame, target = 1000)
    assert len(out) <= 1000
    assert out["ts"].iloc[0] == frame["ts"].iloc[0]
    assert out["ts"].iloc[-1] == frame["ts"].iloc[-1]
