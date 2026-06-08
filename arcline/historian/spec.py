# -*- encoding: utf-8 -*-

"""
Historic-Data Specification
---------------------------

A :class:`HistorySpec` is a declarative mapping between a node/edge
attribute and the row-set in a MS-SQL data warehouse that backs it.
Concrete node / edge classes attach a class-level ``history`` mapping
(see :class:`HistorianMixin`) — the historian then composes a fully
parameterized SELECT statement (via SQLAlchemy Core) at fetch time.

The convention is intentionally minimal::

    class Lane(AbstractEdge):
        leadTimeDays : float = Field(...)

        history : ClassVar[Dict[str, HistorySpec]] = {
            "leadTimeDays": HistorySpec(
                table       = "fact_lane_lead_time",
                keyColumn   = "edge_hash_key",
                valueColumn = "actual_lead_time_days",
                tsColumn    = "shipment_date",
                schema      = "dwh",
                filters     = {"is_active": 1},
            ),
        }

Classes with non-trivial joins may override ``fetchHistory`` directly
on the entity class (escape hatch). The convention path is preferred
whenever it suffices because it lets the cache layer trivially derive
a stable spec-hash to invalidate stale Parquet snapshots.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, ClassVar, Dict, Literal, Optional

from pydantic import BaseModel, Field


Aggregation = Literal["raw", "daily", "weekly", "monthly"]


class HistorySpec(BaseModel):
    """
    Declarative SQL mapping for a single historic attribute series.

    :param table: Physical table or view name in the warehouse.
    :param keyColumn: Column that joins back to ``entity.hashKey``.
    :param valueColumn: Numeric column that carries the observed value.
    :param tsColumn: Timestamp column used for the range filter and ordering.
    :param schema: Optional SQL schema namespace (e.g. ``"dwh"``).
    :param filters: Static ``WHERE`` predicates merged into every query
        as parameterized equality clauses (never string-concatenated).
    :param aggregation: Optional resample hint applied after the fetch.
    :param valueTransform: Optional named transform (e.g. ``"hours_to_days"``)
        applied client-side. Free-form transforms must be coded explicitly.
    :param description: Human-readable docstring for the spec; surfaced in
        the dashboard tooltips.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    table        : str = Field(..., min_length = 1)
    keyColumn    : str = Field(..., min_length = 1)
    valueColumn  : str = Field(..., min_length = 1)
    tsColumn     : str = Field(..., min_length = 1)
    schema_      : Optional[str] = Field(
        default = None,
        alias = "schema",
        description = "Optional SQL schema namespace.",
    )
    filters      : Dict[str, Any] = Field(default_factory = dict)
    aggregation  : Aggregation = "raw"
    valueTransform : Optional[str] = None
    description  : Optional[str] = None

    def qualifiedTable(self) -> str:
        """Return ``schema.table`` if a schema is set, otherwise ``table``."""
        return f"{self.schema_}.{self.table}" if self.schema_ else self.table

    def specHash(self) -> str:
        """
        Deterministic short hash over the spec contents.

        Used as part of the Parquet cache filename so that spec drift
        (e.g. swapping the ``valueColumn``) automatically invalidates
        previously-cached snapshots without manual ``arcline history
        clear`` intervention.
        """
        payload = json.dumps(
            self.model_dump(by_alias = True, exclude_none = True),
            sort_keys = True,
            separators = (",", ":"),
            default = str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


class HistorianMixin:
    """
    Marker mixin granting a class the ``history`` ClassVar slot.

    Concrete classes redeclare ``history`` with their own attribute
    mappings. The base mixin keeps an empty default so introspection
    code (e.g. the ``/dashboard/history`` selector pane) can call
    ``getattr(cls, "history", {})`` without ``hasattr`` guards.
    """

    history : ClassVar[Dict[str, HistorySpec]] = {}

    @classmethod
    def historySpec(cls, attribute: str) -> HistorySpec:
        """
        Resolve the :class:`HistorySpec` for ``attribute`` on this class.

        :raises SpecError: If no spec is registered for ``attribute``.
        """
        from arcline.historian.exceptions import SpecError

        spec = cls.history.get(attribute)
        if spec is None:
            raise SpecError(
                f"{cls.__name__!s} has no HistorySpec for attribute "
                f"{attribute!r}; declare it under the class-level "
                f"`history` mapping."
            )
        return spec

    @classmethod
    def historicAttributes(cls) -> tuple[str, ...]:
        """Return the tuple of attribute names that have a HistorySpec."""
        return tuple(cls.history.keys())
