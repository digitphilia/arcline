# -*- encoding: utf-8 -*-

"""
Built-in Supplier Node Definition
---------------------------------

A :class:`Supplier` represents an upstream vendor that feeds raw
material or components into a supply-chain network. The class is a
concrete implementation of :class:`arcline.graph.base.AbstractNode`
and is auto-registered with the :mod:`arcline.graph.registry` on
import so that polymorphic (de)serialization can reconstruct
instances from a saved ``"kind": "supplier"`` record.
"""

from pydantic import Field
from typing import ClassVar, Optional

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import register_node


class Supplier(AbstractNode):
    """
    Concrete supply-chain node modeling an upstream vendor with a
    nominal lead time and a reliability score in ``[0, 1]``.

    :param leadTimeDays: Nominal lead time, in days, for the vendor
        to fulfil an order; defaults to ``0.0``.
    :param reliabilityScore: Vendor reliability index in ``[0, 1]``;
        defaults to a perfect ``1.0``.
    """

    kind : ClassVar[str] = "supplier"

    leadTimeDays : float = Field(
        0.0, ge = 0.0, description = "Nominal Lead Time in Days"
    )

    reliabilityScore : float = Field(
        1.0, ge = 0.0, le = 1.0,
        description = "Supplier Reliability in [0, 1]"
    )


    @property
    def imagePath(self) -> Optional[str]:
        """
        Default vendor icon shipped with the package.
        """

        return "./icons/vendor.png"


    @property
    def nodeColor(self) -> Optional[str]:
        """
        Default supplier node color in HEX.
        """

        return "#F2A65A"


register_node(Supplier)
