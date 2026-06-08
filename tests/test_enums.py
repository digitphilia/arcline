# -*- encoding: utf-8 -*-

"""Unit tests for :mod:`arcline.graph.enums`."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from arcline.graph.enums import (
    CustomerSegment,
    FacilityStatus,
    LaneServiceLevel,
    OperationalShift,
    OwnershipType,
    StorageType,
    TransportationMode,
)


class _ModelWithMode(BaseModel):
    mode : TransportationMode = TransportationMode.ROAD


def test_canonicalLookup() -> None:
    assert TransportationMode("ROAD") is TransportationMode.ROAD
    assert TransportationMode.RAIL.value == "RAIL"
    assert TransportationMode.RAIL.name == "RAIL"


@pytest.mark.parametrize(
    "candidate,expected",
    [
        ("road", TransportationMode.ROAD),
        ("Road", TransportationMode.ROAD),
        ("RAIL", TransportationMode.RAIL),
        ("rail", TransportationMode.RAIL),
        ("Sea",  TransportationMode.SEA),
        ("aIr",  TransportationMode.AIR),
    ],
)
def test_caseInsensitiveLegacyLookup(
    candidate : str, expected : TransportationMode
) -> None:
    assert TransportationMode(candidate) is expected


def test_unknownTokenRaises() -> None:
    with pytest.raises(ValueError):
        TransportationMode("not-a-mode")


def test_pydanticRoundTripCanonical() -> None:
    payload = _ModelWithMode(mode = TransportationMode.RAIL)
    serialised = payload.model_dump(mode = "json")
    assert serialised == {"mode": "RAIL"}

    raw = payload.model_dump_json()
    assert json.loads(raw) == {"mode": "RAIL"}

    rebuilt = _ModelWithMode.model_validate_json(raw)
    assert rebuilt.mode is TransportationMode.RAIL


def test_pydanticAcceptsLegacyLowercase() -> None:
    rebuilt = _ModelWithMode.model_validate({"mode": "road"})
    assert rebuilt.mode is TransportationMode.ROAD

    rebuilt = _ModelWithMode.model_validate_json('{"mode": "rail"}')
    assert rebuilt.mode is TransportationMode.RAIL


def test_underscoreMembersResolve() -> None:
    assert OwnershipType("THIRD_PARTY") is OwnershipType.THIRD_PARTY
    assert OwnershipType("third_party") is OwnershipType.THIRD_PARTY
    assert StorageType("cold_chain") is StorageType.COLD_CHAIN
    assert OperationalShift("twenty_four_seven") is (
        OperationalShift.TWENTY_FOUR_SEVEN
    )


def test_allEnumsExportCanonicalNames() -> None:
    for enumCls in (
        TransportationMode, FacilityStatus, OwnershipType,
        OperationalShift, StorageType, CustomerSegment,
        LaneServiceLevel,
    ):
        for member in enumCls:
            assert member.name == member.value, (
                f"{enumCls.__name__}.{member.name} "
                f"value {member.value!r} != name"
            )
