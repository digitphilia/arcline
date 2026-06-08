# -*- encoding: utf-8 -*-

"""
Phase 1.5 — P15-1 (foundation) tests.

Covers :class:`HistorySpec` validation, deterministic spec hashing,
the :class:`HistorianMixin` ClassVar slot on
:class:`AbstractNode` / :class:`AbstractEdge`, and the public
:mod:`arcline.historian` import surface.
"""

from __future__ import annotations

from typing import ClassVar, Dict

import pytest
from pydantic import ValidationError

from arcline.historian import (
    HistorySpec,
    HistorianMixin,
    HistorianError,
    SpecError,
)
from arcline.graph.base.nodes import AbstractNode
from arcline.graph.base.edges import AbstractEdge


def makeSpec(**overrides) -> HistorySpec:
    payload = dict(
        table = "fact_lane_lead_time",
        keyColumn = "edge_hash_key",
        valueColumn = "actual_lead_time_days",
        tsColumn = "shipment_date",
    )
    payload.update(overrides)
    return HistorySpec(**payload)


def test_historySpec_minimalFieldsAccepted():
    spec = makeSpec()
    assert spec.qualifiedTable() == "fact_lane_lead_time"
    assert spec.aggregation == "raw"
    assert spec.filters == {}


def test_historySpec_schemaQualifiesTable():
    spec = makeSpec(schema = "dwh")
    assert spec.qualifiedTable() == "dwh.fact_lane_lead_time"


def test_historySpec_rejectsEmptyColumn():
    with pytest.raises(ValidationError):
        makeSpec(valueColumn = "")


def test_historySpec_rejectsUnknownField():
    with pytest.raises(ValidationError):
        HistorySpec(
            table = "t", keyColumn = "k", valueColumn = "v",
            tsColumn = "ts", bogus = 1,
        )


def test_historySpec_isFrozen():
    spec = makeSpec()
    with pytest.raises(ValidationError):
        spec.table = "other"  # type: ignore[misc]


def test_historySpec_hashIsDeterministic():
    a, b = makeSpec(filters = {"is_active": 1}), makeSpec(filters = {"is_active": 1})
    assert a.specHash() == b.specHash()
    assert len(a.specHash()) == 12


def test_historySpec_hashChangesOnDrift():
    base = makeSpec().specHash()
    assert makeSpec(valueColumn = "other_col").specHash() != base
    assert makeSpec(filters = {"is_active": 0}).specHash() != base
    assert makeSpec(aggregation = "daily").specHash() != base


def test_historianMixin_defaultMappingIsEmpty():
    class Empty(HistorianMixin):
        pass
    assert Empty.history == {}
    assert Empty.historicAttributes() == ()


def test_historianMixin_specLookup():
    spec = makeSpec()

    class WithHistory(HistorianMixin):
        history : ClassVar[Dict[str, HistorySpec]] = {"leadTimeDays": spec}

    assert WithHistory.historicAttributes() == ("leadTimeDays",)
    assert WithHistory.historySpec("leadTimeDays") is spec


def test_historianMixin_missingAttributeRaisesSpecError():
    class Empty(HistorianMixin):
        pass
    with pytest.raises(SpecError):
        Empty.historySpec("nonexistent")


def test_abstractNode_inheritsHistoryMixin():
    assert issubclass(AbstractNode, HistorianMixin)
    assert AbstractNode.history == {}


def test_abstractEdge_inheritsHistoryMixin():
    assert issubclass(AbstractEdge, HistorianMixin)
    assert AbstractEdge.history == {}


def test_exceptionHierarchy():
    assert issubclass(SpecError, HistorianError)
