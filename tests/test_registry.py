# -*- encoding: utf-8 -*-

"""
Tests for the Type Registry
---------------------------

Validates ``kind`` ↔ class resolution, idempotent re-registration,
collision detection for distinct classes claiming the same ``kind``,
and the registry snapshot helpers.
"""

from typing import ClassVar, Optional

import pytest

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.library import (
    Customer,
    Lane,
    Plant,
    Production,
    Storage,
    Supplier,
    Warehouse,
)
from arcline.graph.registry import (
    ArclineRegistryError,
    iter_nodes,
    register_node,
    resolve_edge,
    resolve_node,
)


def test_resolve_node_known_kinds() -> None:
    assert resolve_node("supplier") is Supplier
    assert resolve_node("plant") is Plant
    assert resolve_node("warehouse") is Warehouse
    assert resolve_node("customer") is Customer


def test_resolve_edge_known_kinds() -> None:
    assert resolve_edge("lane") is Lane
    assert resolve_edge("production") is Production
    assert resolve_edge("storage") is Storage


def test_unknown_kind_raises() -> None:
    with pytest.raises(ArclineRegistryError):
        resolve_node("alien")


def test_duplicate_registration_idempotent() -> None:
    register_node(Supplier)
    register_node(Supplier)
    assert resolve_node("supplier") is Supplier


def test_duplicate_kind_different_class_raises() -> None:
    class FakeSupplier(AbstractNode):
        kind : ClassVar[str] = "supplier"

        @property
        def imagePath(self) -> Optional[str]:
            return None

        @property
        def nodeColor(self) -> Optional[str]:
            return "#000000"

    with pytest.raises(ArclineRegistryError):
        register_node(FakeSupplier)


def test_iter_nodes_contains_taxonomy() -> None:
    kinds = { kind for kind, _ in iter_nodes() }
    assert {"supplier", "plant", "warehouse", "customer"}.issubset(kinds)
