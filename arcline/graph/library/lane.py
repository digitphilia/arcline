# -*- encoding: utf-8 -*-

"""
Built-in Lane Edge Definition
-----------------------------

A :class:`LaneEdge` represents a transportation arc between two nodes.
``mode`` and ``transitDays`` are inherited from :class:`TransportEdge`;
``costPerUnit`` and ``capacityPerPeriod`` are inherited from
:class:`FlowEdge`.
"""

from pydantic import Field
from typing import ClassVar, Dict, Optional

from arcline.graph.enums import LaneServiceLevel
from arcline.graph.library._intermediates import TransportEdge
from arcline.graph.registry import register_edge
from arcline.historian.spec import HistorySpec


class LaneEdge(TransportEdge):
    """
    Concrete supply-chain edge modeling a transportation lane.

    :param distanceKm: Lane distance in kilometres.
    :param serviceLevel: Commercial service tier; defaults to
        :attr:`LaneServiceLevel.STANDARD`.
    """

    kind : ClassVar[str] = "lane"

    distanceKm : float = Field(
        0.0, ge = 0.0, description = "Lane Distance in Kilometres"
    )

    serviceLevel : LaneServiceLevel = Field(
        default = LaneServiceLevel.STANDARD,
        description = "Commercial Service Level",
    )

    history : ClassVar[Dict[str, HistorySpec]] = {
        "transitDays": HistorySpec(
            table = "fact_lane_lead_time",
            schema = "dwh",
            keyColumn = "edge_hash_key",
            valueColumn = "actual_lead_time_days",
            tsColumn = "shipment_date",
            filters = {"is_active": 1},
            description = "Realized lead time per shipment, daily grain.",
        ),
        "costPerUnit": HistorySpec(
            table = "fact_lane_cost",
            schema = "dwh",
            keyColumn = "edge_hash_key",
            valueColumn = "unit_cost",
            tsColumn = "invoice_date",
            description = "Realized unit cost per invoiced shipment.",
        ),
    }


    @property
    def edgeColor(self) -> Optional[str]:
        """Default lane edge color in HEX."""

        return "#5C6BC0"


register_edge(LaneEdge)
