# -*- encoding: utf-8 -*-

"""
Fluent Network Builder
----------------------

:class:`NetworkBuilder` is a small, ergonomic helper that accumulates
:class:`AbstractNode` and :class:`AbstractEdge` instances and hands
them off to a backend implementation of
:class:`arcline.graph.base.AbstractGraph`. It performs cross-cutting
validation (no duplicate ``hashKey``s, edge endpoints exist) before
materializing the graph so that backend-level errors stay surface-
level and easy to debug.
"""

from typing import Any, Dict, List, Optional

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.graph import AbstractGraph
from arcline.graph.registry import resolve_node


class NetworkBuilder:
    """
    Fluent helper for constructing :class:`AbstractGraph` instances.

    The builder is intentionally lightweight: it stores nodes and
    edges in two ordered lists keyed by ``hashKey`` and only validates
    structural invariants (duplicate keys, missing endpoints) at
    :meth:`build` time. Field-level validation is handled upstream by
    the pydantic models themselves.

    .. code-block:: python

        b = NetworkBuilder()
        s = b.add(Supplier(name = "S1", hashKey = "N-S1"))
        p = b.add(Plant(name = "P1", hashKey = "N-P1"))
        b.connect(s, p, name = "S1->P1", hashKey = "E-S1-P1")
        graph = b.build(backend = "networkx")
    """

    def __init__(self) -> None:
        """
        Initialise an empty builder. Nodes and edges are accumulated
        in insertion order on :attr:`_nodes` / :attr:`_edges`.
        """

        self._nodes : List[AbstractNode] = []
        self._edges : List[AbstractEdge] = []
        self.__nodeKeys : set = set()
        self.__edgeSignatures : set = set()


    def add(self, node : AbstractNode) -> AbstractNode:
        """
        Append a pre-constructed node instance to the builder.

        :type  node: AbstractNode
        :param node: The node to append.

        :raises ValueError: If a node with the same ``hashKey`` is
            already present in the builder.

        :rtype:   AbstractNode
        :returns: The same ``node`` (so callers can chain or alias).
        """

        if node.hashKey in self.__nodeKeys:
            raise ValueError(
                f"Duplicate node hashKey {node.hashKey!r}."
            )

        self._nodes.append(node)
        self.__nodeKeys.add(node.hashKey)
        return node


    def addNode(self, kind : str, **fields : Any) -> AbstractNode:
        """
        Construct a node from its registered ``kind`` discriminator
        and append it to the builder. The ``hashKey`` must currently
        be supplied by the caller; auto-generation is planned for a
        future iteration.

        :type  kind: str
        :param kind: Registered ``kind`` discriminator (e.g.
            ``"supplier"``, ``"plant"``).

        **Keyword Arguments**

        Forwarded verbatim to the resolved node class. Must include
        every required pydantic field, notably ``name`` and
        ``hashKey``.

        :raises ValueError: If a node with the same ``hashKey`` is
            already present in the builder.

        :rtype:   AbstractNode
        :returns: The newly-constructed node instance.
        """

        # ..versionchanged:: <today> Auto Hash Key Generation
        # TODO: when arcline.utils.hashing.makeKey lands, allow
        # callers to omit ``hashKey`` and synthesise one here.
        cls = resolve_node(kind)
        return self.add(cls(**fields))


    def add_edge(
            self,
            src : AbstractNode,
            dst : AbstractNode,
            cls : Optional[type] = None,
            **fields : Any
    ) -> AbstractEdge:
        """
        Append an edge between two previously-added nodes. ``src``
        and ``dst`` must both already be present in the builder.

        :type  src: AbstractNode
        :param src: Source endpoint (must already be in the builder).

        :type  dst: AbstractNode
        :param dst: Destination endpoint (must already be in the
            builder).

        :type  cls: Optional[type]
        :param cls: Concrete :class:`AbstractEdge` subclass to
            instantiate. When ``None``, defaults to
            :class:`arcline.graph.library.lane.Lane` (lazily imported
            to avoid an import cycle with the library package).

        **Keyword Arguments**

        Forwarded verbatim to ``cls``. Must include every required
        pydantic field on the edge, notably ``name`` and ``hashKey``.

        :raises ValueError: If either endpoint is not in the builder
            or if an edge with the same ``hashKey`` is already
            present.

        :rtype:   AbstractEdge
        :returns: The newly-constructed edge instance.
        """

        if cls is None:
            from arcline.graph.library.lane import Lane
            cls = Lane

        srcKey = src.hashKey
        dstKey = dst.hashKey

        if srcKey not in self.__nodeKeys:
            raise ValueError(
                f"Source node {srcKey!r} not registered with builder."
            )

        if dstKey not in self.__nodeKeys:
            raise ValueError(
                f"Destination node {dstKey!r} not registered with "
                f"builder."
            )

        edge = cls(srcNode = src, dstNode = dst, **fields)

        signature = (edge.hashKey, srcKey, dstKey)
        if signature in self.__edgeSignatures:
            raise ValueError(
                f"Duplicate edge hashKey {edge.hashKey!r} "
                f"between {srcKey!r} and {dstKey!r}."
            )

        self._edges.append(edge)
        self.__edgeSignatures.add(signature)
        return edge


    def connect(
            self,
            src : AbstractNode,
            dst : AbstractNode,
            cls : Optional[type] = None,
            **fields : Any
    ) -> AbstractEdge:
        """
        Alias for :meth:`add_edge` that reads more naturally in
        builder-style code.
        """

        return self.add_edge(src = src, dst = dst, cls = cls, **fields)


    def build(self, backend : str = "networkx") -> AbstractGraph:
        """
        Validate accumulated state and materialise an
        :class:`AbstractGraph` from it.

        :type  backend: str
        :param backend: Backend identifier; only ``"networkx"`` is
            supported in the current iteration.

        :raises ValueError: If a duplicate ``hashKey`` is detected,
            if an edge endpoint is missing, or if ``backend`` is
            unknown.

        :rtype:   AbstractGraph
        :returns: A fully-built backend graph instance.
        """

        seen : Dict[str, AbstractNode] = {}
        for node in self._nodes:
            if node.hashKey in seen:
                raise ValueError(
                    f"Duplicate node hashKey {node.hashKey!r}."
                )
            seen[node.hashKey] = node

        edge_keys : set = set()
        for edge in self._edges:
            srcKey = edge.srcNode.hashKey
            dstKey = edge.dstNode.hashKey

            if srcKey not in seen:
                raise ValueError(
                    f"Edge {edge.hashKey!r} references missing "
                    f"source {srcKey!r}."
                )

            if dstKey not in seen:
                raise ValueError(
                    f"Edge {edge.hashKey!r} references missing "
                    f"destination {dstKey!r}."
                )

            signature = (edge.hashKey, srcKey, dstKey)
            if signature in edge_keys:
                raise ValueError(
                    f"Duplicate edge hashKey {edge.hashKey!r} "
                    f"between {srcKey!r} and {dstKey!r}."
                )
            edge_keys.add(signature)

        if backend == "networkx":
            from arcline.graph.backends.networkx import NetworkXGraph
            return NetworkXGraph(
                nodes = list(self._nodes), edges = list(self._edges)
            )

        raise ValueError(f"Unknown backend {backend!r}.")
