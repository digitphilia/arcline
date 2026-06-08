# -*- encoding: utf-8 -*-

"""
Tests for arcline.utils Helpers
-------------------------------

Covers deterministic identifier hashing, haversine and bounding-box
helpers, and the logging configuration (idempotent setup plus the
MS-SQL DSN credentials redactor).
"""

import logging

import pytest

from arcline.utils.geo import bbox, haversine
from arcline.utils.hashing import makeEdgeKey, makeKey, makeNodeKey
from arcline.utils.logging import (
    CredentialsRedactor,
    __reset_for_tests__,
    configureLogging,
)


def test_make_key_deterministic() -> None:
    a = makeKey("supplier", "Acme")
    b = makeKey("supplier", "Acme")
    assert a == b


def test_make_node_vs_edge_prefix() -> None:
    assert makeNodeKey("supplier", "Acme").startswith("N-")
    assert makeEdgeKey("lane", "A", "B").startswith("E-")


def test_haversine_known_distance() -> None:
    dist = haversine(0.0, 0.0, 0.0, 1.0)
    assert abs(dist - 111.19) < 0.5


def test_haversine_symmetry() -> None:
    forward = haversine(12.97, 77.59, 19.07, 72.87)
    reverse = haversine(19.07, 72.87, 12.97, 77.59)
    assert abs(forward - reverse) < 1e-9


def test_bbox_basic() -> None:
    points = [(10.0, 20.0), (-5.0, 50.0), (30.0, -10.0)]
    assert bbox(points) == (-5.0, -10.0, 30.0, 50.0)


def test_bbox_empty_raises() -> None:
    with pytest.raises(ValueError):
        bbox([])


def test_logging_idempotent() -> None:
    __reset_for_tests__()
    configureLogging()
    configureLogging()


def test_credentials_redactor_scrubs_dsn() -> None:
    redactor = CredentialsRedactor()
    record = logging.LogRecord(
        name = "test", level = logging.INFO, pathname = __file__,
        lineno = 1,
        msg = "connecting to mssql+pyodbc://user:pass@host/db now",
        args = (), exc_info = None,
    )

    assert redactor.filter(record) is True
    assert "***" in record.getMessage()
    assert "user:pass@host" not in record.getMessage()


def test_credentials_redactor_attached_to_handler(capsys) -> None:
    """Regression: redactor must scrub logs from CHILD loggers too."""

    __reset_for_tests__()
    configureLogging()

    child = logging.getLogger("arcline.x")
    child.warning("opening mssql+pyodbc://u:p@host/db now")

    for handler in logging.getLogger().handlers:
        handler.flush()

    captured = capsys.readouterr()
    assert "***" in captured.err
    assert "u:p@host" not in captured.err
