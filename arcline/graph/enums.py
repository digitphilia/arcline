# -*- encoding: utf-8 -*-

"""
Categorical Enumerations for the Built-in Taxonomy
--------------------------------------------------

Single source of truth for every categorical (string-valued) attribute
exposed by the concrete node and edge classes under
:mod:`arcline.graph.library`.

All enums inherit :class:`_CamelStrEnum` so their JSON wire format is
the canonical UPPER_SNAKE member name (e.g. ``"RAIL"``,
``"COLD_CHAIN"``). A custom ``_missing_`` classmethod accepts the
legacy lowercase ``Literal`` payloads emitted by ``arcline`` v0.1
(e.g. ``"rail"``) so existing on-disk projects continue to load
unchanged; :func:`Project.save` always re-emits the canonical form.

Usage::

    class LaneEdge(TransportEdge):
        mode : TransportationMode = Field(
            default = TransportationMode.ROAD,
            description = "Transport mode used on the lane.",
        )
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class _CamelStrEnum(str, Enum):
    """
    String-valued enum base whose ``.value`` is identical to the
    member name (``ROAD = "ROAD"``).

    Identical-value-and-name eliminates the value/name divergence
    headache; pydantic v2 serialises the member as the string
    ``.value`` which here equals the canonical ``.name``.

    The case-insensitive :meth:`_missing_` hook accepts the legacy
    lowercase tokens that v0.1 of ``arcline`` wrote to disk under
    ``Literal["road", "rail", ...]`` fields, so an UPGRADED v0.2.0
    install can still ``Project.open()`` a v1 project before the
    v1->v2 migrator rewrites the artefacts.
    """

    @classmethod
    def _missing_(cls, value : object) -> Optional["_CamelStrEnum"]:
        """
        Permissive lookup that accepts any case-variant of either the
        canonical UPPER_SNAKE member name or the lowercase member
        value (legacy v0.1 wire format).

        :type  value: object
        :param value: Candidate string passed to ``cls(value)``.

        :rtype:   Optional[_CamelStrEnum]
        :returns: The matching enum member, or ``None`` to let
            :class:`Enum` raise the standard ``ValueError``.
        """

        if not isinstance(value, str):
            return None

        upper = value.upper()
        for member in cls:
            if member.name == upper or member.value.upper() == upper:
                return member
        return None


class TransportationMode(_CamelStrEnum):
    """Transport modality used on a transportation edge."""

    ROAD = "ROAD"
    RAIL = "RAIL"
    SEA  = "SEA"
    AIR  = "AIR"


class FacilityStatus(_CamelStrEnum):
    """Operational lifecycle state of a physical facility."""

    PLANNED         = "PLANNED"
    OPEN            = "OPEN"
    CLOSED          = "CLOSED"
    DECOMMISSIONED  = "DECOMMISSIONED"


class OwnershipType(_CamelStrEnum):
    """Asset ownership pattern for a facility."""

    OWNED        = "OWNED"
    LEASED       = "LEASED"
    THIRD_PARTY  = "THIRD_PARTY"


class OperationalShift(_CamelStrEnum):
    """Active operating shift pattern for a facility."""

    DAY                 = "DAY"
    NIGHT               = "NIGHT"
    TWENTY_FOUR_SEVEN   = "TWENTY_FOUR_SEVEN"


class StorageType(_CamelStrEnum):
    """Climate / handling regime for stored product."""

    AMBIENT      = "AMBIENT"
    COLD_CHAIN   = "COLD_CHAIN"
    FROZEN       = "FROZEN"
    HAZMAT       = "HAZMAT"


class CustomerSegment(_CamelStrEnum):
    """Commercial customer segmentation."""

    RETAIL     = "RETAIL"
    WHOLESALE  = "WHOLESALE"
    B2B        = "B2B"
    B2C        = "B2C"


class LaneServiceLevel(_CamelStrEnum):
    """Commercial service level offered on a transportation lane."""

    STANDARD   = "STANDARD"
    EXPEDITED  = "EXPEDITED"
    OVERNIGHT  = "OVERNIGHT"


class Currency(_CamelStrEnum):
    """ISO 4217 currency tokens used on cost-bearing fields.

    Declared for forward compatibility with Phase 2 (optimisation) and
    not yet wired into any built-in field.
    """

    USD  = "USD"
    EUR  = "EUR"
    GBP  = "GBP"
    INR  = "INR"
    JPY  = "JPY"


class UnitOfMeasure(_CamelStrEnum):
    """Physical unit of measure for capacity and demand fields.

    Declared for forward compatibility with Phase 2 (optimisation) and
    not yet wired into any built-in field.
    """

    EACH    = "EACH"
    CASE    = "CASE"
    PALLET  = "PALLET"
    KG      = "KG"
    TON     = "TON"
    LITRE   = "LITRE"


__all__ = [
    "TransportationMode",
    "FacilityStatus",
    "OwnershipType",
    "OperationalShift",
    "StorageType",
    "CustomerSegment",
    "LaneServiceLevel",
    "Currency",
    "UnitOfMeasure",
]
