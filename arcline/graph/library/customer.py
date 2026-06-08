# -*- encoding: utf-8 -*-

"""
Built-in Customer Node Definition
---------------------------------

A :class:`CustomerNode` represents a downstream demand point with a
Gaussian-style demand summary (mean and standard deviation) and a
commercial segment.
"""

from pydantic import Field
from typing import ClassVar, Dict, Optional

from arcline.graph.enums import CustomerSegment
from arcline.graph.library._intermediates import DemandNode
from arcline.graph.registry import register_node
from arcline.historian.spec import HistorySpec


class CustomerNode(DemandNode):
    """
    Concrete supply-chain node modeling a downstream demand point.

    :param demandMean: Mean of the demand distribution (units).
    :param demandStd: Standard deviation of the demand distribution.
    :param segment: Commercial customer segmentation; defaults to
        :attr:`CustomerSegment.RETAIL`.
    """

    kind : ClassVar[str] = "customer"

    demandMean : float = Field(
        0.0, ge = 0.0, description = "Mean of the Demand Distribution"
    )

    demandStd : float = Field(
        0.0, ge = 0.0,
        description = "Standard Deviation of the Demand Distribution"
    )

    segment : CustomerSegment = Field(
        default = CustomerSegment.RETAIL,
        description = "Commercial Customer Segment",
    )

    history : ClassVar[Dict[str, HistorySpec]] = {
        "demandMean": HistorySpec(
            table = "fact_customer_demand",
            schema = "dwh",
            keyColumn = "node_hash_key",
            valueColumn = "units_ordered",
            tsColumn = "order_date",
            description = "Realized order quantity per order date.",
        ),
    }


    @property
    def imagePath(self) -> Optional[str]:
        """Default customer icon shipped with the package."""

        return "./icons/graph.png"


    @property
    def nodeColor(self) -> Optional[str]:
        """Default customer node color in HEX."""

        return "#E07A5F"


register_node(CustomerNode)
