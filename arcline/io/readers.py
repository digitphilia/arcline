# -*- encoding: utf-8 -*-

"""
Project Readers
---------------

Deserialise on-disk project artifacts (JSON, YAML, Parquet, CSV) into
pydantic-validated :class:`AbstractNode` and :class:`AbstractEdge`
instances. Each reader resolves the concrete class via the
:mod:`arcline.graph.registry` ``kind`` discriminator before
instantiation, so adding a new built-in or third-party node/edge
class only requires registering it; the reader code does not change.

Single-file mode (``{"nodes": [...], "edges": [...]}``) is supported
for JSON and YAML; tabular formats use one file per artifact.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import (
    ArclineRegistryError,
    resolve_edge,
    resolve_node,
)


_REQUIRED_NODE_FIELDS : Tuple[str, ...] = ("kind", "name", "hashKey")
_REQUIRED_EDGE_FIELDS : Tuple[str, ...] = (
    "kind", "name", "hashKey", "srcKey", "dstKey",
)


def __requireFields__(
        record : Dict[str, Any],
        required : Tuple[str, ...],
        kindLabel : str
) -> None:
    """
    Raise :class:`KeyError` if ``record`` is missing any of the
    fields listed in ``required``.

    :type  record: Dict[str, Any]
    :param record: Raw node or edge dictionary.

    :type  required: Tuple[str, ...]
    :param required: Required field names.

    :type  kindLabel: str
    :param kindLabel: ``"Node"`` or ``"Edge"`` for the error
        message.

    :raises KeyError: When a required field is absent.

    :rtype:   None
    """

    for field in required:
        if field not in record:
            raise KeyError(
                f"{kindLabel} record missing required field "
                f"{field!r}."
            )


def __dropna__(row : Dict[str, Any]) -> Dict[str, Any]:
    """
    Replace tabular ``NaN`` values with ``None`` so pydantic's
    ``Optional`` fields accept them cleanly. Lists, dicts, and
    arbitrary scalars survive untouched.

    :type  row: Dict[str, Any]
    :param row: One row from a :class:`pandas.DataFrame` rendered as
        a dict.

    :rtype:   Dict[str, Any]
    :returns: A new dict with scalar ``NaN`` replaced by ``None``.
    """

    cleaned : Dict[str, Any] = {}
    import pandas as pd
    for key, value in row.items():
        try:
            isNa = bool(pd.isna(value))
        except (TypeError, ValueError):
            isNa = False
        cleaned[key] = None if isNa else value

    return cleaned


def __buildNode__(record : Dict[str, Any]) -> AbstractNode:
    """
    Resolve a node ``kind`` and instantiate the registered class.

    :type  record: Dict[str, Any]
    :param record: Raw node dictionary; copied locally before
        instantiation so the caller's data is left untouched.

    :raises KeyError: If a required field is missing or the ``kind``
        is not registered.

    :rtype:   AbstractNode
    :returns: A pydantic-validated node instance.
    """

    __requireFields__(record, _REQUIRED_NODE_FIELDS, "Node")
    payload = dict(record)
    kind = payload.pop("kind")
    try:
        cls = resolve_node(kind)
    except ArclineRegistryError as exc:
        raise ValueError(
            f"Unknown node kind {kind!r}: {exc}"
        ) from exc
    return cls(**payload)


def __buildEdge__(
        record : Dict[str, Any],
        nodesByKey : Dict[str, AbstractNode]
) -> AbstractEdge:
    """
    Resolve an edge ``kind``, look up its endpoints in
    ``nodesByKey`` and instantiate the registered class.

    :type  record: Dict[str, Any]
    :param record: Raw edge dictionary.

    :type  nodesByKey: Dict[str, AbstractNode]
    :param nodesByKey: Lookup mapping from ``hashKey`` to the
        already-deserialised node instance.

    :raises KeyError: If a required field is missing, the ``kind``
        is not registered, or an endpoint hashKey is unknown.

    :rtype:   AbstractEdge
    :returns: A pydantic-validated edge instance with concrete
        ``srcNode`` / ``dstNode`` references.
    """

    __requireFields__(record, _REQUIRED_EDGE_FIELDS, "Edge")
    payload = dict(record)
    kind = payload.pop("kind")
    srcKey = payload.pop("srcKey")
    dstKey = payload.pop("dstKey")

    if srcKey not in nodesByKey:
        raise KeyError(
            f"Edge references unknown srcKey {srcKey!r}."
        )

    if dstKey not in nodesByKey:
        raise KeyError(
            f"Edge references unknown dstKey {dstKey!r}."
        )

    try:
        cls = resolve_edge(kind)
    except ArclineRegistryError as exc:
        raise ValueError(
            f"Unknown edge kind {kind!r}: {exc}"
        ) from exc
    return cls(
        srcNode = nodesByKey[srcKey],
        dstNode = nodesByKey[dstKey],
        **payload,
    )


def __splitPayload__(
        payload : Any
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Normalise a JSON/YAML payload into ``(nodes, edges)`` raw lists.

    :type  payload: Any
    :param payload: Parsed payload, expected to be a dict with
        ``"nodes"`` and ``"edges"`` keys.

    :raises ValueError: If ``payload`` does not match the expected
        single-file layout.

    :rtype:   Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]
    :returns: The extracted nodes and edges lists.
    """

    if not isinstance(payload, dict):
        raise ValueError(
            "Expected a top-level mapping with 'nodes' and "
            "'edges' keys."
        )

    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])

    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError(
            "Both 'nodes' and 'edges' must be JSON arrays."
        )

    return nodes, edges


def __assemble__(
        nodeRecords : List[Dict[str, Any]],
        edgeRecords : List[Dict[str, Any]]
) -> Tuple[List[AbstractNode], List[AbstractEdge]]:
    """
    Build pydantic node and edge instances from raw record lists.

    :type  nodeRecords: List[Dict[str, Any]]
    :param nodeRecords: Raw node dictionaries.

    :type  edgeRecords: List[Dict[str, Any]]
    :param edgeRecords: Raw edge dictionaries.

    :rtype:   Tuple[List[AbstractNode], List[AbstractEdge]]
    :returns: Parallel lists of constructed nodes and edges.
    """

    nodes : List[AbstractNode] = [
        __buildNode__(rec) for rec in nodeRecords
    ]
    nodesByKey : Dict[str, AbstractNode] = {
        node.hashKey: node for node in nodes
    }
    edges : List[AbstractEdge] = [
        __buildEdge__(rec, nodesByKey) for rec in edgeRecords
    ]

    return nodes, edges


def fromJson(
        path : Path
) -> Tuple[List[AbstractNode], List[AbstractEdge]]:
    """
    Read a single-file JSON project payload of the form
    ``{"nodes": [...], "edges": [...]}`` and deserialise it into
    pydantic-validated graph objects.

    :type  path: Path
    :param path: Filesystem path to the JSON file.

    :raises KeyError: If a record is missing required fields or
        references an unknown ``kind`` or ``hashKey``.
    :raises ValueError: If the payload structure is invalid.

    :rtype:   Tuple[List[AbstractNode], List[AbstractEdge]]
    :returns: ``(nodes, edges)`` lists.
    """

    with Path(path).open("r", encoding = "utf-8") as fp:
        payload = json.load(fp)

    nodeRecords, edgeRecords = __splitPayload__(payload)
    return __assemble__(nodeRecords, edgeRecords)


def fromYaml(
        path : Path
) -> Tuple[List[AbstractNode], List[AbstractEdge]]:
    """
    Read a single-file YAML project payload (same structure as
    :func:`fromJson`) and deserialise it into graph objects.

    :type  path: Path
    :param path: Filesystem path to the YAML file.

    :raises KeyError: As in :func:`fromJson`.
    :raises ValueError: As in :func:`fromJson`.

    :rtype:   Tuple[List[AbstractNode], List[AbstractEdge]]
    :returns: ``(nodes, edges)`` lists.
    """

    with Path(path).open("r", encoding = "utf-8") as fp:
        payload = yaml.safe_load(fp)

    nodeRecords, edgeRecords = __splitPayload__(payload or {})
    return __assemble__(nodeRecords, edgeRecords)


def fromParquet(
        nodesPath : Path,
        edgesPath : Path
) -> Tuple[List[AbstractNode], List[AbstractEdge]]:
    """
    Read separate Parquet files for nodes and edges and deserialise
    them into graph objects. ``NaN`` values are replaced with
    ``None`` before instantiation so pydantic ``Optional`` fields
    accept them cleanly.

    :type  nodesPath: Path
    :param nodesPath: Path to the nodes Parquet file.

    :type  edgesPath: Path
    :param edgesPath: Path to the edges Parquet file.

    :raises KeyError: As in :func:`fromJson`.

    :rtype:   Tuple[List[AbstractNode], List[AbstractEdge]]
    :returns: ``(nodes, edges)`` lists.
    """

    import pandas as pd
    nodesDf = pd.read_parquet(Path(nodesPath))
    edgesDf = pd.read_parquet(Path(edgesPath))

    nodeRecords = [
        __dropna__(row) for row in nodesDf.to_dict(orient = "records")
    ]
    edgeRecords = [
        __dropna__(row) for row in edgesDf.to_dict(orient = "records")
    ]

    return __assemble__(nodeRecords, edgeRecords)


def fromCsv(
        nodesPath : Path,
        edgesPath : Path
) -> Tuple[List[AbstractNode], List[AbstractEdge]]:
    """
    Read separate CSV files for nodes and edges and deserialise them
    into graph objects. ``NaN`` values are replaced with ``None``
    before instantiation.

    :type  nodesPath: Path
    :param nodesPath: Path to the nodes CSV file.

    :type  edgesPath: Path
    :param edgesPath: Path to the edges CSV file.

    :raises KeyError: As in :func:`fromJson`.

    :rtype:   Tuple[List[AbstractNode], List[AbstractEdge]]
    :returns: ``(nodes, edges)`` lists.
    """

    import pandas as pd
    nodesDf = pd.read_csv(Path(nodesPath))
    edgesDf = pd.read_csv(Path(edgesPath))

    nodeRecords = [
        __dropna__(row) for row in nodesDf.to_dict(orient = "records")
    ]
    edgeRecords = [
        __dropna__(row) for row in edgesDf.to_dict(orient = "records")
    ]

    return __assemble__(nodeRecords, edgeRecords)
