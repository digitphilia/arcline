# -*- encoding: utf-8 -*-

"""
Concrete Implementation of :class:`AbstractGraph` using NetworkX API
--------------------------------------------------------------------

This module provides :class:`NetworkXGraph`, the :mod:`networkx`-backed
concrete implementation of :class:`arcline.graph.base.AbstractGraph`.
It is the recommended choice for development workflows, exploratory
notebooks, and small subgraphs where the pure-Python overhead of
:mod:`networkx` (typicall ≤ 1M edges) is tolerable.

The practical scale ceiling for this backend is on the order of one
million edges; past that point per-operation overhead from the
Python-level adjacency structure begins to dominate runtime. For the
full supply-chain network, prefer the :mod:`igraph` backend which
sits on a C-level graph engine and offers one to two orders of
magnitude better throughput on bulk operations.

The wrapped backend is always a :class:`networkx.MultiDiGraph` but any
other instances of :class:`networkx.Graph` is also supported, but may
not be valid when designing for a supply chain optimization problem.
The supply-chain framework treats lanes as directed (asymmetric lead
time and cost) and as multi-edges so that parallel lanes between the
same endpoint pair can be modeled independently (different carriers,
contracts, transportation modes). Vertices in the underlying graph
are keyed by :attr:`AbstractNode.hashKey` and parallel edges between
the same endpoint pair are disambiguated by :attr:`AbstractEdge.hashKey`
passed to NetworkX as the edge ``key``.
"""

from collections.abc import Iterator
from typing import Any, Dict, List, Optional, Tuple

import networkx

from arcline.graph.base import AbstractGraph, AbstractNode, AbstractEdge

class NetworkXGraph(AbstractGraph):
    """
    NetworkX-backed concrete implementation of :class:`AbstractGraph`.
    Suitable for development workflows and small subgraphs where the
    pure-Python overhead of :mod:`networkx` is tolerable. For the full
    network (thousands of nodes, millions of edges), use the
    :mod:`igraph` backend instead.

    The wrapped backend is always a :class:`networkx.MultiDiGraph`. On
    construction the node and edge object lists supplied to
    :meth:`__init__` are materialised into the underlying graph via
    :meth:`buildGraph`; vertices use :attr:`AbstractNode.hashKey` as
    their NetworkX identifier and parallel edges between the same
    endpoint pair are disambiguated by :attr:`AbstractEdge.hashKey`
    passed to NetworkX as the per-edge ``key``.

    Internally a hashKey → ``AbstractNode`` lookup is maintained so
    that :meth:`neighbors`, :meth:`predecessors`, and :meth:`successors`
    can return typed :class:`AbstractNode` objects rather than the raw
    string identifiers that NetworkX stores natively.
    """

    def __init__(
        self,
        nodes : List[AbstractNode],
        edges : List[AbstractEdge],
        G : Optional[networkx.Graph] = None,
        **kwargs
    ) -> None:
        """
        The node and edge object lists are stored on the base class as
        :attr:`nodes` / :attr:`edges` and become the canonical source
        of truth for the model. The underlying NetworkX graph is
        either supplied via ``G`` (useful when wrapping a graph loaded
        from disk) or created fresh as an empty :class:`networkx.Graph`.
        When ``autoBuild`` is ``True`` (the default) :meth:`buildGraph`
        is invoked immediately so the instance is ready for traversal
        queries on return.

        :type  nodes: List[AbstractNode]
        :param nodes: The node objects that compose the graph. Each
            node must be an instance of :class:`AbstractNode` class or
            any derived sub-nodes with pre-built configurations.

        :type  edges: List[AbstractEdge]
        :param edges: The edge objects that compose the graph. Each
            edge holds direct references to its source and destination
            nodes and a unique :attr:`AbstractEdge.hashKey` that
            disambiguates parallel edges in the multi-graph.

        :type  G: Optional[networkx.Graph]
        :param G: Optional pre-built :mod:`networkx` graph to wrap.
            Defaults to a fresh empty :class:`networkx.MultiDiGraph`.

        **Keyword Arguments**

            * **name** (*str*): Model name for logging and auditing,
                defaults to the concrete class name.

            * **autoBuild** (*bool*): When ``True`` (default), the
                :meth:`buildGraph` is called at the end of construction
                to populate ``G`` from the node and edge lists. Pass
                ``False`` to defer materialisation (e.g. when ``G``
                is already populated).
        """

        super().__init__(
            G = G or networkx.MultiDiGraph(),
            nodes = nodes, edges = edges, name = kwargs.get("name", None)
        )

        # ? auto build the graph; else pass developed graph
        if kwargs.get("autoBuild", True):
            self.buildGraph()


    def buildGraph(self) -> bool:
        """
        Build the graph consisting of :attr:`nodes` and :attr:`edges`
        with underlying properties using :mod:`pydantic` models data
        payload which are added as the vertex attributes. For an edge
        the ``hashKey`` is set as the key attribute for multi-graph
        while all other attributes are added as attributes.

        :rtype:   bool
        :returns: The boolean flag is positional, either returns
            ``True`` if the build is succesful.
        """

        self.G.add_nodes_from([
            (node.hashKey, node.model_dump(exclude = {"hashKey"}))
            for node in self.nodes
        ])
        
        for edge in self.edges:
            attrs = edge.model_dump(exclude = {
                "hashKey", "srcNode", "dstNode"
            })

            self.G.add_edge(
                edge.srcNode.hashKey, edge.dstNode.hashKey,
                key = edge.hashKey, **attrs
            )

        return True


    def addNode(self, node : AbstractNode) -> None:
        """
        Insert a node into the graph. The node payload is appended to
        :attr:`nodes` and the underlying :class:`networkx.MultiDiGraph`
        gets a new vertex keyed by :attr:`AbstractNode.hashKey` whose
        attributes mirror the pydantic ``model_dump`` payload.

        :type  node: AbstractNode
        :param node: The node object to be inserted in the graph; must
            carry a :attr:`hashKey` not already present in the graph.

        :raises KeyError: If a node with the same :attr:`hashKey` is
            already present in the graph.
        """

        if self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} already exists."
            )

        self.nodes.append(node)
        self.G.add_node(
            node.hashKey, **node.model_dump(exclude = {"hashKey"})
        )
        self.__invalidate_indices__()


    def addEdge(self, edge : AbstractEdge) -> None:
        """
        Insert an edge into the graph. The edge payload is appended
        to :attr:`edges` and the underlying multi-graph is updated;
        :attr:`AbstractEdge.hashKey` becomes the parallel-edge key so
        that distinct lanes between the same endpoint pair remain
        addressable.

        :type  edge: AbstractEdge
        :param edge: The edge object to be inserted; must reference
            endpoints that already exist in the graph.

        :raises KeyError: If an edge with the same :attr:`hashKey`
            already exists, or if either endpoint is not present.
        """

        srcKey = edge.srcNode.hashKey
        dstKey = edge.dstNode.hashKey

        if not self.G.has_node(srcKey):
            raise KeyError(
                f"Source node {srcKey!r} not present in the graph."
            )

        if not self.G.has_node(dstKey):
            raise KeyError(
                f"Destination node {dstKey!r} not present in the graph."
            )

        if self.G.has_edge(srcKey, dstKey, key = edge.hashKey):
            raise KeyError(
                f"Edge with hashKey {edge.hashKey!r} already exists "
                f"between {srcKey!r} and {dstKey!r}."
            )

        self.edges.append(edge)
        attrs = edge.model_dump(
            exclude = {"hashKey", "srcNode", "dstNode"}
        )
        self.G.add_edge(srcKey, dstKey, key = edge.hashKey, **attrs)
        self.__invalidate_indices__()


    def updateNode(
            self, node : AbstractNode, **changes : Any
    ) -> AbstractNode:
        """
        Apply ``changes`` to an existing node via
        :meth:`pydantic.BaseModel.model_copy`. The replacement
        instance is written back into :attr:`nodes` and the matching
        vertex attributes on the underlying NetworkX graph are
        refreshed in place; the vertex identifier
        (:attr:`hashKey`) is preserved.

        :type  node: AbstractNode
        :param node: The node currently in the graph (looked up by
            :attr:`hashKey`).

        :raises KeyError: If the node is not present in the graph.
        :raises ValueError: If ``hashKey`` appears in ``changes``;
            the identifier is immutable, remove and re-add the node
            instead.

        :rtype:   AbstractNode
        :returns: The newly-constructed node with updates applied.
        """

        if "hashKey" in changes:
            raise ValueError(
                "hashKey is immutable; remove and re-add the node "
                "instead."
            )

        if not self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} not in graph."
            )

        updated = node.model_copy(update = changes)

        for idx, cur in enumerate(self.nodes):
            if cur.hashKey == node.hashKey:
                self.nodes[idx] = updated
                break
        else:
            raise KeyError(
                f"Node {node.hashKey!r} missing from node list."
            )

        self.G.nodes[node.hashKey].clear()
        self.G.nodes[node.hashKey].update(
            updated.model_dump(exclude = {"hashKey"})
        )
        self.__invalidate_indices__()

        return updated


    def updateEdge(
            self, edge : AbstractEdge, **changes : Any
    ) -> AbstractEdge:
        """
        Apply ``changes`` to an existing edge via
        :meth:`pydantic.BaseModel.model_copy`. Endpoints are immutable
        once an edge is inserted; passing ``srcNode`` or ``dstNode``
        in ``changes`` raises :class:`ValueError`. The replacement
        instance is written back into :attr:`edges` and the matching
        edge attributes on the underlying NetworkX multi-graph are
        refreshed in place.

        :type  edge: AbstractEdge
        :param edge: The edge currently in the graph (looked up by
            :attr:`hashKey`).

        :raises KeyError: If the edge is not present in the graph.
        :raises ValueError: If ``srcNode``, ``dstNode`` or ``hashKey``
            appears in ``changes`` (endpoints and identifier are
            immutable; remove and re-add the edge instead).

        :rtype:   AbstractEdge
        :returns: The newly-constructed edge with updates applied.
        """

        if "hashKey" in changes:
            raise ValueError(
                "hashKey is immutable; remove and re-add the edge "
                "instead."
            )

        if "srcNode" in changes or "dstNode" in changes:
            raise ValueError(
                "Cannot rewire an edge via updateEdge; remove and "
                "re-add the edge instead."
            )

        srcKey = edge.srcNode.hashKey
        dstKey = edge.dstNode.hashKey

        if not self.G.has_edge(srcKey, dstKey, key = edge.hashKey):
            raise KeyError(
                f"Edge {edge.hashKey!r} between {srcKey!r} and "
                f"{dstKey!r} not present in the graph."
            )

        updated = edge.model_copy(update = changes)

        for idx, cur in enumerate(self.edges):
            if cur.hashKey == edge.hashKey \
                    and cur.srcNode.hashKey == srcKey \
                    and cur.dstNode.hashKey == dstKey:
                self.edges[idx] = updated
                break
        else:
            raise KeyError(
                f"Edge {edge.hashKey!r} missing from edge list."
            )

        attrs = updated.model_dump(
            exclude = {"hashKey", "srcNode", "dstNode"}
        )
        self.G[srcKey][dstKey][edge.hashKey].clear()
        self.G[srcKey][dstKey][edge.hashKey].update(attrs)
        self.__invalidate_indices__()

        return updated


    def removeNode(self, node : AbstractNode) -> None:
        """
        Remove a node and all of its incident edges from the graph.
        Removal is cascading: every edge touching the node is also
        deleted, and :attr:`nodes` / :attr:`edges` are filtered to
        keep the abstract view in sync with the backend.

        :type  node: AbstractNode
        :param node: The node currently in the graph (looked up by
            :attr:`hashKey`).

        :raises KeyError: If the node is not present in the graph.
        """

        if not self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} not in graph."
            )

        self.G.remove_node(node.hashKey)
        self.nodes = [
            cur for cur in self.nodes if cur.hashKey != node.hashKey
        ]
        self.edges = [
            cur for cur in self.edges
            if cur.srcNode.hashKey != node.hashKey
            and cur.dstNode.hashKey != node.hashKey
        ]
        self.__invalidate_indices__()


    def hasNode(self, node : AbstractNode) -> bool:
        """
        Test whether a node is present in the graph by its
        :attr:`hashKey`.

        :type  node: AbstractNode
        :param node: The node whose presence is to be tested.

        :rtype:   bool
        :returns: ``True`` if the node is present, else ``False``.
        """

        return bool(self.G.has_node(node.hashKey))


    def removeEdge(self, edge : AbstractEdge) -> None:
        """
        Remove a specific parallel edge between two endpoints. In a
        multi-graph the :attr:`AbstractEdge.hashKey` disambiguates
        which lane is removed; sibling lanes between the same pair
        are left intact.

        :type  edge: AbstractEdge
        :param edge: The edge to be removed.

        :raises KeyError: If the edge does not exist in the graph.
        """

        srcKey = edge.srcNode.hashKey
        dstKey = edge.dstNode.hashKey

        if not self.G.has_edge(srcKey, dstKey, key = edge.hashKey):
            raise KeyError(
                f"Edge {edge.hashKey!r} between {srcKey!r} and "
                f"{dstKey!r} not present in the graph."
            )

        self.G.remove_edge(srcKey, dstKey, key = edge.hashKey)
        self.edges = [
            cur for cur in self.edges if cur.hashKey != edge.hashKey
        ]
        self.__invalidate_indices__()


    def hasEdge(
            self, src : AbstractNode, dst : AbstractNode
    ) -> bool:
        """
        Test whether at least one directed edge exists from ``src``
        to ``dst`` in the underlying multi-graph.

        :type  src: AbstractNode
        :param src: The source node of the prospective edge.

        :type  dst: AbstractNode
        :param dst: The destination node of the prospective edge.

        :rtype:   bool
        :returns: ``True`` if at least one parallel edge exists
            between the two endpoints (in the given direction).
        """

        return bool(self.G.has_edge(src.hashKey, dst.hashKey))


    def neighbors(
            self, node : AbstractNode
    ) -> Tuple[AbstractNode, ...]:
        """
        Return the unique union of in-neighbors and out-neighbors of
        a node as :class:`AbstractNode` instances.

        :type  node: AbstractNode
        :param node: The node whose neighbors are to be retrieved.

        :raises KeyError: If the node is not present in the graph.

        :rtype:   Tuple[AbstractNode, ...]
        :returns: Tuple of unique neighbor node instances.
        """

        if not self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} not in graph."
            )

        index = self._nodesByKey
        keys : List[str] = []
        seen : set = set()

        for key in self.G.successors(node.hashKey):
            if key not in seen:
                seen.add(key)
                keys.append(key)

        for key in self.G.predecessors(node.hashKey):
            if key not in seen:
                seen.add(key)
                keys.append(key)

        return tuple(index[key] for key in keys if key in index)


    def predecessors(
            self, node : AbstractNode
    ) -> Tuple[AbstractNode, ...]:
        """
        Return the unique in-neighbors of a node as
        :class:`AbstractNode` instances.

        :type  node: AbstractNode
        :param node: The node whose predecessors are to be retrieved.

        :raises KeyError: If the node is not present in the graph.

        :rtype:   Tuple[AbstractNode, ...]
        :returns: Tuple of unique predecessor node instances.
        """

        if not self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} not in graph."
            )

        index = self._nodesByKey
        return tuple(
            index[key] for key in self.G.predecessors(node.hashKey)
            if key in index
        )


    def successors(
            self, node : AbstractNode
    ) -> Tuple[AbstractNode, ...]:
        """
        Return the unique out-neighbors of a node as
        :class:`AbstractNode` instances.

        :type  node: AbstractNode
        :param node: The node whose successors are to be retrieved.

        :raises KeyError: If the node is not present in the graph.

        :rtype:   Tuple[AbstractNode, ...]
        :returns: Tuple of unique successor node instances.
        """

        if not self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} not in graph."
            )

        index = self._nodesByKey
        return tuple(
            index[key] for key in self.G.successors(node.hashKey)
            if key in index
        )


    def inDegree(self, node : AbstractNode) -> int:
        """
        Return the in-degree of a node. In a multi-graph each
        parallel edge contributes independently.

        :type  node: AbstractNode
        :param node: The node whose in-degree is to be retrieved.

        :raises KeyError: If the node is not present in the graph.

        :rtype:   int
        :returns: Total in-degree of the node.
        """

        if not self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} not in graph."
            )

        return int(self.G.in_degree(node.hashKey))


    def outDegree(self, node : AbstractNode) -> int:
        """
        Return the out-degree of a node. In a multi-graph each
        parallel edge contributes independently.

        :type  node: AbstractNode
        :param node: The node whose out-degree is to be retrieved.

        :raises KeyError: If the node is not present in the graph.

        :rtype:   int
        :returns: Total out-degree of the node.
        """

        if not self.G.has_node(node.hashKey):
            raise KeyError(
                f"Node with hashKey {node.hashKey!r} not in graph."
            )

        return int(self.G.out_degree(node.hashKey))
