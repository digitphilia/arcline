# -*- encoding: utf-8 -*-

"""
Built-in Customer Node Definition
---------------------------------

A :class:`Customer` represents a downstream demand point characterized
by the mean and standard deviation of its demand distribution.
"""

from pydantic import Field
from typing import ClassVar, Optional

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import register_node


class Customer(AbstractNode):
    """
    Concrete supply-chain node modeling a demand point with a
    Gaussian-style demand summary (mean and standard deviation).

    :param demandMean: Mean of the demand distribution (units).
    :param demandStd: Standard deviation of the demand distribution.
    """

    kind : ClassVar[str] = "customer"

    demandMean : float = Field(
        0.0, ge = 0.0, description = "Mean of the Demand Distribution"
    )

    demandStd : float = Field(
        0.0, ge = 0.0,
        description = "Standard Deviation of the Demand Distribution"
    )


    @property
    def imagePath(self) -> Optional[str]:
        """
        Default customer icon shipped with the package.
        """

        return "./icons/graph.png"


    @property
    def nodeColor(self) -> Optional[str]:
        """
        Default customer node color in HEX.
        """

        return "#E07A5F"


register_node(Customer)
