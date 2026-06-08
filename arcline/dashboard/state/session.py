# -*- encoding: utf-8 -*-

"""
Server-Side Session State
-------------------------

Single-user, single-process holder for the live
:class:`arcline.graph.base.AbstractGraph` instance and the on-disk
:class:`arcline.io.Project` it was loaded from. All mutations flow
through a small command pattern (``addNodeCmd``, ``updateEdgeCmd``
and friends) so that future audit / undo wiring has a single choke
point to instrument.

:NOTE: The module-level state is guarded by an :class:`threading.RLock`
to keep concurrent Dash callbacks correct under the development
server. This is intentionally a single-user MVP - multi-user
hardening (per-session state, isolation, persistence) is parked for
a later phase.
"""

import threading
from pathlib import Path
from typing import Any, Optional, Union

from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.graph import AbstractGraph
from arcline.graph.base.nodes import AbstractNode
from arcline.io.project import Project


# TODO: multi-user - replace these module-level slots with a
# per-Flask-session holder when the dashboard grows multi-tenant.
_GRAPH : Optional[AbstractGraph] = None
_PROJECT : Optional[Project] = None
_LOCK : threading.RLock = threading.RLock()


def bindProject(path : Union[Path, str]) -> None:
    """
    Open the project rooted at ``path`` and load its graph into the
    process-wide session slot.

    :type  path: Union[Path, str]
    :param path: Filesystem path to the project root directory.

    :rtype:   None
    """

    global _GRAPH, _PROJECT

    with _LOCK:
        project = Project.open(path)
        graph = project.toGraph()

        _PROJECT = project
        _GRAPH = graph


def isBound() -> bool:
    """
    Indicate whether a project has been bound to the session.

    :rtype:   bool
    :returns: ``True`` when both project and graph slots are
        populated.
    """

    with _LOCK:
        return _PROJECT is not None and _GRAPH is not None


def getProject() -> Project:
    """
    Return the currently bound :class:`arcline.io.Project` handle.

    :raises RuntimeError: If no project has been bound.

    :rtype:   Project
    :returns: The active project instance.
    """

    with _LOCK:
        if _PROJECT is None:
            raise RuntimeError(
                "No project bound; call bindProject() first."
            )
        return _PROJECT


def getGraph() -> AbstractGraph:
    """
    Return the live :class:`AbstractGraph` instance held in session.

    :raises RuntimeError: If no project has been bound.

    :rtype:   AbstractGraph
    :returns: The mutable backend graph instance.
    """

    with _LOCK:
        if _GRAPH is None:
            raise RuntimeError(
                "No project bound; call bindProject() first."
            )
        return _GRAPH


def reset() -> None:
    """
    Clear the session state. Intended primarily for tests and for the
    eventual "Close project" UI affordance.

    :rtype:   None
    """

    global _GRAPH, _PROJECT

    with _LOCK:
        _GRAPH = None
        _PROJECT = None


def saveProject() -> None:
    """
    Persist the in-memory graph back to the bound project on disk.

    The project's ``nodes`` and ``edges`` are refreshed from the live
    graph before delegating to :meth:`Project.save`.

    :raises RuntimeError: If no project has been bound.

    :rtype:   None
    """

    with _LOCK:
        project = getProject()
        graph = getGraph()
        project.nodes = list(graph.nodes)
        project.edges = list(graph.edges)
        project.save()


def addNodeCmd(node : AbstractNode) -> AbstractGraph:
    """
    Command-pattern wrapper that inserts a node into the live graph.

    :type  node: AbstractNode
    :param node: The node to insert.

    :rtype:   AbstractGraph
    :returns: The (mutated) live graph reference.
    """

    with _LOCK:
        graph = getGraph()
        graph.addNode(node)
        return graph


def updateNodeCmd(
        node : AbstractNode, **changes : Any
) -> AbstractGraph:
    """
    Command-pattern wrapper that applies a set of field updates to
    an existing node.

    :type  node: AbstractNode
    :param node: The current node (looked up by ``hashKey``).

    **Keyword Arguments**

    Forwarded verbatim to :meth:`AbstractGraph.updateNode`.

    :rtype:   AbstractGraph
    :returns: The (mutated) live graph reference.
    """

    with _LOCK:
        graph = getGraph()
        graph.updateNode(node, **changes)
        return graph


def removeNodeCmd(node : AbstractNode) -> AbstractGraph:
    """
    Command-pattern wrapper that deletes a node (and its incident
    edges) from the live graph.

    :type  node: AbstractNode
    :param node: The node to remove.

    :rtype:   AbstractGraph
    :returns: The (mutated) live graph reference.
    """

    with _LOCK:
        graph = getGraph()
        graph.removeNode(node)
        return graph


def addEdgeCmd(edge : AbstractEdge) -> AbstractGraph:
    """
    Command-pattern wrapper that inserts an edge into the live graph.

    :type  edge: AbstractEdge
    :param edge: The edge to insert.

    :rtype:   AbstractGraph
    :returns: The (mutated) live graph reference.
    """

    with _LOCK:
        graph = getGraph()
        graph.addEdge(edge)
        return graph


def updateEdgeCmd(
        edge : AbstractEdge, **changes : Any
) -> AbstractGraph:
    """
    Command-pattern wrapper that applies a set of field updates to
    an existing edge.

    :type  edge: AbstractEdge
    :param edge: The current edge (looked up by ``hashKey``).

    **Keyword Arguments**

    Forwarded verbatim to :meth:`AbstractGraph.updateEdge`.

    :rtype:   AbstractGraph
    :returns: The (mutated) live graph reference.
    """

    with _LOCK:
        graph = getGraph()
        graph.updateEdge(edge, **changes)
        return graph


def removeEdgeCmd(edge : AbstractEdge) -> AbstractGraph:
    """
    Command-pattern wrapper that deletes an edge from the live graph.

    :type  edge: AbstractEdge
    :param edge: The edge to remove.

    :rtype:   AbstractGraph
    :returns: The (mutated) live graph reference.
    """

    with _LOCK:
        graph = getGraph()
        graph.removeEdge(edge)
        return graph
