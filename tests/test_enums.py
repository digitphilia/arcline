# -*- encoding: utf-8 -*-

"""Unit tests for :mod:`arcline.graph.enums`."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from arcline.graph.enums import (
    Currency,
    CustomerSegment,
    FacilityStatus,
    LaneServiceLevel,
    OperationalShift,
    OwnershipType,
    StorageType,
    TransportationMode,
    UnitOfMeasure,
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
        LaneServiceLevel, Currency, UnitOfMeasure,
    ):
        for member in enumCls:
            assert member.name == member.value, (
                f"{enumCls.__name__}.{member.name} "
                f"value {member.value!r} != name"
            )


# ---------- str subclass semantics --------------------------------------------


def test_enumIsStringSubclass() -> None:
    """
    ``_CamelStrEnum`` derives from ``str``, so members must compare
    equal to their canonical string value and behave as strings in
    formatting / serialisation contexts.
    """

    assert isinstance(TransportationMode.ROAD, str)
    assert TransportationMode.ROAD == "ROAD"
    assert StorageType.COLD_CHAIN == "COLD_CHAIN"
    assert f"{TransportationMode.AIR}" == "TransportationMode.AIR"
    assert TransportationMode.AIR.value == "AIR"


def test_enumHashableInSetsAndDicts() -> None:
    """
    Members must hash to the same bucket as their string value so they
    can be used safely as set members and dict keys (e.g. style maps).
    """

    bucket = {
        TransportationMode.ROAD, TransportationMode.ROAD,
        TransportationMode.RAIL,
    }
    assert len(bucket) == 2

    palette : dict = {
        TransportationMode.ROAD: "#1f77b4",
        TransportationMode.RAIL: "#ff7f0e",
    }
    assert palette[TransportationMode.ROAD] == "#1f77b4"


# ---------- pydantic round-trip across the full enum catalogue ----------------


@pytest.mark.parametrize(
    "enumCls,member",
    [
        (TransportationMode,  TransportationMode.SEA),
        (FacilityStatus,      FacilityStatus.CLOSED),
        (OwnershipType,       OwnershipType.THIRD_PARTY),
        (OperationalShift,    OperationalShift.TWENTY_FOUR_SEVEN),
        (StorageType,         StorageType.COLD_CHAIN),
        (CustomerSegment,     CustomerSegment.WHOLESALE),
        (LaneServiceLevel,    LaneServiceLevel.EXPEDITED),
        (Currency,            Currency.INR),
        (UnitOfMeasure,       UnitOfMeasure.PALLET),
    ],
)
def test_allEnumsRoundTripThroughPydantic(
    enumCls : type, member,
) -> None:
    """
    Every enum in the catalogue must serialise to its canonical UPPER
    name through ``model_dump(mode="json")`` and deserialise back to
    the same member through ``model_validate_json``.
    """

    class _M(BaseModel):
        value : enumCls

    payload = _M(value = member)
    serialised = payload.model_dump(mode = "json")
    assert serialised == {"value": member.name}

    rebuilt = _M.model_validate_json(payload.model_dump_json())
    assert rebuilt.value is member
