# -*- encoding: utf-8 -*-

"""
Built-in Lane Edge Definition
-----------------------------

A :class:`Lane` represents a transportation arc between two nodes -
distance, unit cost, transit days, and a transport mode are the four
core attributes that drive flow / cost optimization on the lane.
"""

from pydantic import Field
from typing import ClassVar, Literal, Optional

from arcline.graph.base.edges import AbstractEdge
from arcline.graph.registry import register_edge


class Lane(AbstractEdge):
    """
    Concrete supply-chain edge modeling a transportation lane.

    :param distanceKm: Lane distance in kilometres.
    :param costPerUnit: Variable cost per unit shipped on the lane.
    :param transitDays: Nominal transit time in days.
    :param mode: Transportation mode; one of ``"road"``, ``"rail"``,
        ``"sea"`` or ``"air"``.
    """

    kind : ClassVar[str] = "lane"

    distanceKm : float = Field(
        0.0, ge = 0.0, description = "Lane Distance in Kilometres"
    )

    costPerUnit : float = Field(
        0.0, ge = 0.0, description = "Variable Unit Cost on the Lane"
    )

    transitDays : float = Field(
        0.0, ge = 0.0, description = "Nominal Transit Time in Days"
    )

    mode : Literal["road", "rail", "sea", "air"] = Field(
        "road", description = "Transportation Mode"
    )


    @property
    def edgeColor(self) -> Optional[str]:
        """
        Default lane edge color in HEX.
        """

        return "#5C6BC0"


register_edge(Lane)
