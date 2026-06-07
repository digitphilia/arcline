# -*- encoding: utf-8 -*-

"""
Project Writers
---------------

Serialise pydantic-validated :class:`AbstractNode` and
:class:`AbstractEdge` instances back to JSON, YAML or Parquet on
disk. The on-disk shape mirrors the readers' expectations: each
record carries the ``kind`` discriminator at the top, edges carry
``srcKey`` / ``dstKey`` instead of nested node payloads, and JSON
/ YAML use a single-file ``{"nodes": [...], "edges": [...]}``
envelope while Parquet uses one file per artifact.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.nodes import AbstractNode


def __node_record__(node : AbstractNode) -> Dict[str, Any]:
    """
    Serialise a single node into a flat record dictionary with
    ``kind`` placed first.

    :type  node: AbstractNode
    :param node: The node to serialise.

    :rtype:   Dict[str, Any]
    :returns: A flat dictionary suitable for JSON / YAML / Parquet
        export.
    """

    payload = node.model_dump()
    record : Dict[str, Any] = {"kind": type(node).kind}
    record.update(payload)
    return record


def __edge_record__(edge : AbstractEdge) -> Dict[str, Any]:
    """
    Serialise a single edge into a flat record dictionary, replacing
    nested node references with their ``hashKey`` strings.

    :type  edge: AbstractEdge
    :param edge: The edge to serialise.

    :rtype:   Dict[str, Any]
    :returns: A flat dictionary suitable for export.
    """

    payload = edge.model_dump(exclude = {"srcNode", "dstNode"})
    record : Dict[str, Any] = {"kind": type(edge).kind}
    record.update(payload)
    record["srcKey"] = edge.srcNode.hashKey
    record["dstKey"] = edge.dstNode.hashKey
    return record


def _build_payload(
        nodes : List[AbstractNode],
        edges : List[AbstractEdge]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Assemble the canonical single-file payload envelope used by the
    YAML writer and by in-memory revalidation flows.

    :type  nodes: List[AbstractNode]
    :param nodes: The nodes to serialise.

    :type  edges: List[AbstractEdge]
    :param edges: The edges to serialise.

    :rtype:   Dict[str, List[Dict[str, Any]]]
    :returns: ``{"nodes": [...], "edges": [...]}``.
    """

    return {
        "nodes": [__node_record__(node) for node in nodes],
        "edges": [__edge_record__(edge) for edge in edges],
    }


def to_json_records(
        records : List[Dict[str, Any]],
        path : Path,
        indent : int = 2
) -> None:
    """
    Write a flat list of pre-serialised record dictionaries to ``path``
    as a top-level JSON array.

    This is the canonical writer for ``nodes.json`` and ``edges.json``;
    each file contains only its own records (no ``{"nodes": ...,
    "edges": ...}`` envelope wrapper).

    :type  records: List[Dict[str, Any]]
    :param records: Flat list of records to serialise.

    :type  path: Path
    :param path: Output filesystem path; parent directories must
        already exist.

    :type  indent: int
    :param indent: JSON indentation level; pass ``0`` for a compact
        single-line output.

    :rtype:   None
    """

    with Path(path).open("w", encoding = "utf-8") as fp:
        json.dump(
            records, fp, indent = indent or None,
            ensure_ascii = False, default = str,
        )


def to_json(
        nodes : List[AbstractNode],
        edges : List[AbstractEdge],
        path : Path,
        indent : int = 2
) -> None:
    """
    Write a legacy single-file JSON project payload (envelope form
    ``{"nodes": [...], "edges": [...]}``) to ``path``.

    .. deprecated:: 0.0.1
        Prefer :func:`to_json_records` for per-artifact writes. This
        helper is retained for backward compatibility with the
        envelope-form ``nodes.json`` / ``edges.json`` files produced
        by earlier releases.

    :type  nodes: List[AbstractNode]
    :param nodes: Nodes to serialise.

    :type  edges: List[AbstractEdge]
    :param edges: Edges to serialise.

    :type  path: Path
    :param path: Output filesystem path; parent directories must
        already exist.

    :type  indent: int
    :param indent: JSON indentation level; pass ``0`` for a compact
        single-line output.

    :rtype:   None
    """

    payload = _build_payload(nodes, edges)

    with Path(path).open("w", encoding = "utf-8") as fp:
        json.dump(
            payload, fp, indent = indent or None,
            ensure_ascii = False, default = str,
        )


def to_yaml(
        nodes : List[AbstractNode],
        edges : List[AbstractEdge],
        path : Path
) -> None:
    """
    Write a single-file YAML project payload to ``path``.

    :type  nodes: List[AbstractNode]
    :param nodes: Nodes to serialise.

    :type  edges: List[AbstractEdge]
    :param edges: Edges to serialise.

    :type  path: Path
    :param path: Output filesystem path.

    :rtype:   None
    """

    payload = _build_payload(nodes, edges)

    with Path(path).open("w", encoding = "utf-8") as fp:
        yaml.safe_dump(
            payload, fp, sort_keys = False, default_flow_style = False
        )


def to_parquet(
        nodes : List[AbstractNode],
        edges : List[AbstractEdge],
        nodes_path : Path,
        edges_path : Path
) -> None:
    """
    Write nodes and edges to two separate Parquet files for bulk
    workflows.

    :type  nodes: List[AbstractNode]
    :param nodes: Nodes to serialise.

    :type  edges: List[AbstractEdge]
    :param edges: Edges to serialise.

    :type  nodes_path: Path
    :param nodes_path: Output path for the nodes Parquet file.

    :type  edges_path: Path
    :param edges_path: Output path for the edges Parquet file.

    :rtype:   None
    """

    node_records = [__node_record__(node) for node in nodes]
    edge_records = [__edge_record__(edge) for edge in edges]

    pd.DataFrame(node_records).to_parquet(
        Path(nodes_path), index = False
    )
    pd.DataFrame(edge_records).to_parquet(
        Path(edges_path), index = False
    )
