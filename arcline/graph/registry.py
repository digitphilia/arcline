# -*- encoding: utf-8 -*-

"""
Type Registry for Built-in Supply-Chain Taxonomy
------------------------------------------------

A lightweight kind ↔ class registry that maps the string discriminator
``kind`` (declared as a :class:`typing.ClassVar` on every concrete
node and edge class under :mod:`arcline.graph.library`) to the
implementing pydantic class.

The registry is used for polymorphic (de)serialization: a JSON record
with ``"kind": "warehouse"`` can be reconstructed into a
:class:`arcline.graph.library.warehouse.Warehouse` instance without
the I/O layer hard-coding the taxonomy.

:NOTE: The registry stores process-local state in two private module
dictionaries; importing :mod:`arcline.graph.library` triggers the
side-effect registrations for every shipped node and edge type.
"""

from typing import Dict, List, Tuple

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.base.edges import AbstractEdge


_NODE_KINDS : Dict[str, type] = {}
_EDGE_KINDS : Dict[str, type] = {}


class ArclineRegistryError(Exception):
    """
    Raised whenever the type registry is asked to perform an
    invalid operation - registering a class without a ``kind``
    attribute, registering two distinct classes under the same
    ``kind``, or resolving an unknown ``kind`` string.
    """

    pass


def __validate_kind__(cls : type, base : type) -> str:
    """
    Internal helper that validates a class is a strict subclass of
    ``base`` and exposes a non-empty class-level ``kind`` string
    discriminator.

    :type  cls: type
    :param cls: The class being registered.

    :type  base: type
    :param base: The expected abstract base class
        (:class:`AbstractNode` or :class:`AbstractEdge`).

    :raises ArclineRegistryError: If ``cls`` is not a subclass of
        ``base`` or does not declare a non-empty ``kind`` attribute.

    :rtype:   str
    :returns: The validated ``kind`` discriminator string.
    """

    if not isinstance(cls, type) or not issubclass(cls, base):
        raise ArclineRegistryError(
            f"{cls!r} must be a subclass of {base.__name__}."
        )

    kind = getattr(cls, "kind", None)
    if not isinstance(kind, str) or not kind:
        raise ArclineRegistryError(
            f"{cls.__name__} must declare a non-empty class-level "
            f"`kind: ClassVar[str]` discriminator."
        )

    return kind


def register_node(cls : type) -> type:
    """
    Register a concrete :class:`AbstractNode` subclass under its
    class-level ``kind`` discriminator. Idempotent when called with
    the exact same class twice; raises on a different class trying
    to claim an already-registered ``kind``.

    Designed to double as a decorator.

    :type  cls: type
    :param cls: The concrete node class to register.

    :raises ArclineRegistryError: If ``cls`` is not a subclass of
        :class:`AbstractNode`, does not declare a ``kind``, or if
        another class is already registered under the same ``kind``.

    :rtype:   type
    :returns: The same ``cls`` (so the function can be used as a
        decorator).
    """

    kind = __validate_kind__(cls, AbstractNode)
    existing = _NODE_KINDS.get(kind)

    if existing is not None and existing is not cls:
        raise ArclineRegistryError(
            f"Node kind {kind!r} already registered to "
            f"{existing.__name__}; cannot reassign to {cls.__name__}."
        )

    _NODE_KINDS[kind] = cls
    return cls


def register_edge(cls : type) -> type:
    """
    Register a concrete :class:`AbstractEdge` subclass under its
    class-level ``kind`` discriminator. Idempotent when called with
    the exact same class twice; raises on a different class trying
    to claim an already-registered ``kind``.

    Designed to double as a decorator.

    :type  cls: type
    :param cls: The concrete edge class to register.

    :raises ArclineRegistryError: If ``cls`` is not a subclass of
        :class:`AbstractEdge`, does not declare a ``kind``, or if
        another class is already registered under the same ``kind``.

    :rtype:   type
    :returns: The same ``cls`` (so the function can be used as a
        decorator).
    """

    kind = __validate_kind__(cls, AbstractEdge)
    existing = _EDGE_KINDS.get(kind)

    if existing is not None and existing is not cls:
        raise ArclineRegistryError(
            f"Edge kind {kind!r} already registered to "
            f"{existing.__name__}; cannot reassign to {cls.__name__}."
        )

    _EDGE_KINDS[kind] = cls
    return cls


def __ensure_library_loaded__() -> None:
    """
    Internal helper that triggers a lazy import of the built-in
    :mod:`arcline.graph.library` taxonomy so that registry lookups
    succeed even when the caller has not imported the library
    subpackage explicitly.
    """

    if not _NODE_KINDS or not _EDGE_KINDS:
        import importlib
        importlib.import_module("arcline.graph.library")


def resolve_node(kind : str) -> type:
    """
    Look up a previously-registered node class by its ``kind``
    discriminator.

    :type  kind: str
    :param kind: The string discriminator declared on the target
        class as a :class:`typing.ClassVar`.

    :raises ArclineRegistryError: If no node class is registered
        under ``kind``.

    :rtype:   type
    :returns: The concrete node class registered under ``kind``.
    """

    __ensure_library_loaded__()
    cls = _NODE_KINDS.get(kind)
    if cls is None:
        raise ArclineRegistryError(
            f"No node class registered under kind {kind!r}."
        )

    return cls


def resolve_edge(kind : str) -> type:
    """
    Look up a previously-registered edge class by its ``kind``
    discriminator.

    :type  kind: str
    :param kind: The string discriminator declared on the target
        class as a :class:`typing.ClassVar`.

    :raises ArclineRegistryError: If no edge class is registered
        under ``kind``.

    :rtype:   type
    :returns: The concrete edge class registered under ``kind``.
    """

    __ensure_library_loaded__()
    cls = _EDGE_KINDS.get(kind)
    if cls is None:
        raise ArclineRegistryError(
            f"No edge class registered under kind {kind!r}."
        )

    return cls


def iter_nodes() -> List[Tuple[str, type]]:
    """
    Snapshot the currently-registered node taxonomy as a list of
    ``(kind, cls)`` pairs.

    :rtype:   List[Tuple[str, type]]
    :returns: List of registered node entries.
    """

    return list(_NODE_KINDS.items())


def iter_edges() -> List[Tuple[str, type]]:
    """
    Snapshot the currently-registered edge taxonomy as a list of
    ``(kind, cls)`` pairs.

    :rtype:   List[Tuple[str, type]]
    :returns: List of registered edge entries.
    """

    return list(_EDGE_KINDS.items())


def clear_registry() -> None:
    """
    Empty the node and edge registries. Intended primarily for use
    inside test fixtures that need a clean slate; production code
    should not need to call this.
    """

    _NODE_KINDS.clear()
    _EDGE_KINDS.clear()
