# -*- encoding: utf-8 -*-

"""
Tests for Project I/O Round-Trips and Validators
------------------------------------------------

Round-trips the :class:`arcline.io.Project` facade through disk, the
JSON / YAML / Parquet readers and writers, and verifies that the
cross-file validators flag duplicate keys, orphan edges, lat/lon
out-of-range values, and schema-version drift.
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest

from arcline.graph.library import CustomerNode, PlantNode, SupplierNode
from arcline.io import (
    Project,
    fromCsv,
    fromParquet,
    fromYaml,
    toParquet,
    toYaml,
    validateProject,
)


def _manifest() -> Dict[str, Any]:
    return {
        "name": "fixture",
        "arclineSchemaVersion": "1.0.0",
        "createdAt": "2025-01-01T00:00:00+00:00",
    }


def test_save_and_open_roundtrip(sampleProject : Project) -> None:
    reopened = Project.open(sampleProject.path)
    graph = reopened.toGraph()

    assert len(reopened.nodes) == len(sampleProject.nodes)
    assert len(reopened.edges) == len(sampleProject.edges)
    assert graph.numNodes == 3
    assert graph.numEdges == 2

    origKinds = [type(n).kind for n in sampleProject.nodes]
    newKinds = [type(n).kind for n in reopened.nodes]
    assert origKinds == newKinds


def test_typed_classes_preserved(sampleProject : Project) -> None:
    reopened = Project.open(sampleProject.path)
    classes = {type(node) for node in reopened.nodes}

    assert classes.issubset({SupplierNode, PlantNode, CustomerNode})
    assert SupplierNode in classes
    assert PlantNode in classes
    assert CustomerNode in classes


def test_validate_clean_project_has_no_errors(
        sampleProject : Project
) -> None:
    issues = sampleProject.validate()
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_orphan_edge_flagged_by_validator() -> None:
    rawNodes : List[Dict[str, Any]] = [
        {"kind": "supplier", "name": "S", "hashKey": "N-S"},
    ]
    rawEdges : List[Dict[str, Any]] = [
        {
            "kind": "lane", "name": "bad", "hashKey": "E-BAD",
            "srcKey": "N-S", "dstKey": "N-MISSING",
        },
    ]
    issues = validateProject(rawNodes, rawEdges, _manifest())
    codes = [i.code for i in issues if i.severity == "error"]

    assert any("orphan" in code for code in codes)


def test_duplicate_hashkey_flagged_by_validator() -> None:
    rawNodes : List[Dict[str, Any]] = [
        {"kind": "supplier", "name": "A", "hashKey": "N-DUP"},
        {"kind": "supplier", "name": "B", "hashKey": "N-DUP"},
    ]
    issues = validateProject(rawNodes, [], _manifest())
    errors = [i for i in issues if i.severity == "error"]

    assert any(i.code == "duplicate-node-key" for i in errors)


def test_lat_lon_out_of_range_flagged() -> None:
    rawNodes : List[Dict[str, Any]] = [
        {
            "kind": "supplier", "name": "X", "hashKey": "N-X",
            "latitude": 999.0, "longitude": -999.0,
        },
    ]
    issues = validateProject(rawNodes, [], _manifest())
    codes = {i.code for i in issues if i.severity == "error"}

    assert "latitude-out-of-range" in codes
    assert "longitude-out-of-range" in codes


def test_manifest_schema_version_warning() -> None:
    manifest = {
        "name": "x",
        "arclineSchemaVersion": "9.9.9",
        "createdAt": "2025-01-01T00:00:00+00:00",
    }
    issues = validateProject([], [], manifest)
    warnings = [i for i in issues if i.severity == "warning"]
    assert any(
        i.code == "manifest-schema-version-drift" for i in warnings
    )


def test_yaml_format_roundtrip(
        sampleProject : Project, tmp_path : Path
) -> None:
    out = tmp_path / "graph.yaml"
    toYaml(
        nodes = sampleProject.nodes, edges = sampleProject.edges,
        path = out,
    )
    nodes, edges = fromYaml(out)

    assert len(nodes) == len(sampleProject.nodes)
    assert len(edges) == len(sampleProject.edges)


def test_csv_format_roundtrip(tmp_path : Path) -> None:
    nodesCsv = tmp_path / "nodes.csv"
    edgesCsv = tmp_path / "edges.csv"

    nodesCsv.write_text(
        "kind,name,hashKey,leadTimeDays\n"
        "supplier,S1,N-S1,3.0\n",
        encoding = "utf-8",
    )
    edgesCsv.write_text(
        "kind,name,hashKey,srcKey,dstKey,distanceKm,costPerUnit,"
        "transitDays,mode\n",
        encoding = "utf-8",
    )

    nodes, edges = fromCsv(nodesCsv, edgesCsv)

    assert len(nodes) == 1
    assert nodes[0].hashKey == "N-S1"
    assert edges == []


def test_parquet_format_roundtrip(
        sampleProject : Project, tmp_path : Path
) -> None:
    pytest.importorskip("pyarrow")

    nodesPq = tmp_path / "nodes.parquet"
    edgesPq = tmp_path / "edges.parquet"

    toParquet(
        nodes = sampleProject.nodes, edges = sampleProject.edges,
        nodesPath = nodesPq, edgesPath = edgesPq,
    )

    nodes, edges = fromParquet(nodesPq, edgesPq)
    assert len(nodes) == len(sampleProject.nodes)
    assert len(edges) == len(sampleProject.edges)


def test_save_writes_flat_arrays(sampleProject : Project) -> None:
    """Regression: nodes.json and edges.json must be flat arrays."""

    import json as _json

    nodesRaw = _json.loads(
        (sampleProject.path / "nodes.json").read_text(
            encoding = "utf-8"
        )
    )
    edgesRaw = _json.loads(
        (sampleProject.path / "edges.json").read_text(
            encoding = "utf-8"
        )
    )

    assert isinstance(nodesRaw, list)
    assert isinstance(edgesRaw, list)
    assert len(nodesRaw) == len(sampleProject.nodes)
    assert len(edgesRaw) == len(sampleProject.edges)
    assert all("kind" in rec for rec in nodesRaw)
    assert all("srcKey" in rec for rec in edgesRaw)


def test_open_accepts_legacy_envelope_form(
        sampleProject : Project
) -> None:
    """Back-compat: envelope-form nodes.json / edges.json still loads."""

    import json as _json

    nodesPath = sampleProject.path / "nodes.json"
    edgesPath = sampleProject.path / "edges.json"
    nodesRecords = _json.loads(nodesPath.read_text(encoding = "utf-8"))
    edgesRecords = _json.loads(edgesPath.read_text(encoding = "utf-8"))

    nodesPath.write_text(
        _json.dumps({"nodes": nodesRecords, "edges": []}),
        encoding = "utf-8",
    )
    edgesPath.write_text(
        _json.dumps({"nodes": [], "edges": edgesRecords}),
        encoding = "utf-8",
    )

    reopened = Project.open(sampleProject.path)
    assert len(reopened.nodes) == len(sampleProject.nodes)
    assert len(reopened.edges) == len(sampleProject.edges)


def test_open_rejects_null_nodes_payload(
        sampleProject : Project
) -> None:
    """Regression: ``{"nodes": null}`` must raise ValueError, not TypeError."""

    import json as _json

    nodesPath = sampleProject.path / "nodes.json"
    edgesPath = sampleProject.path / "edges.json"

    nodesPath.write_text(
        _json.dumps({"nodes": None, "edges": []}),
        encoding = "utf-8",
    )
    edgesPath.write_text(
        _json.dumps({"nodes": [], "edges": None}),
        encoding = "utf-8",
    )

    with pytest.raises(ValueError):
        Project.open(sampleProject.path)


def test_validator_warns_self_loop() -> None:
    """Regression: srcKey == dstKey must emit a self-loop-edge warning."""

    rawNodes : List[Dict[str, Any]] = [
        {"kind": "supplier", "name": "S", "hashKey": "N-S"},
    ]
    rawEdges : List[Dict[str, Any]] = [
        {
            "kind": "lane", "name": "loop", "hashKey": "E-LOOP",
            "srcKey": "N-S", "dstKey": "N-S",
            "distanceKm": 0.0, "costPerUnit": 0.0,
            "transitDays": 0.0, "mode": "road",
        },
    ]

    issues = validateProject(rawNodes, rawEdges, _manifest())
    assert any(i.code == "self-loop-edge" for i in issues)


def test_validator_unknown_kind_is_error() -> None:
    """Regression: unknown kind must be severity == 'error', not warning."""

    rawNodes : List[Dict[str, Any]] = [
        {"kind": "alien", "name": "X", "hashKey": "N-X"},
    ]
    issues = validateProject(rawNodes, [], _manifest())
    matches = [i for i in issues if i.code == "unknown-node-kind"]

    assert matches
    assert all(i.severity == "error" for i in matches)
