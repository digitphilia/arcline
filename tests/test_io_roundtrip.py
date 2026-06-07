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

from arcline.graph.library import Customer, Plant, Supplier
from arcline.io import (
    Project,
    from_csv,
    from_parquet,
    from_yaml,
    to_parquet,
    to_yaml,
    validate_project,
)


def _manifest() -> Dict[str, Any]:
    return {
        "name": "fixture",
        "arclineSchemaVersion": "1.0.0",
        "createdAt": "2025-01-01T00:00:00+00:00",
    }


def test_save_and_open_roundtrip(sample_project : Project) -> None:
    reopened = Project.open(sample_project.path)
    graph = reopened.toGraph()

    assert len(reopened.nodes) == len(sample_project.nodes)
    assert len(reopened.edges) == len(sample_project.edges)
    assert graph.numNodes == 3
    assert graph.numEdges == 2

    orig_kinds = [type(n).kind for n in sample_project.nodes]
    new_kinds = [type(n).kind for n in reopened.nodes]
    assert orig_kinds == new_kinds


def test_typed_classes_preserved(sample_project : Project) -> None:
    reopened = Project.open(sample_project.path)
    classes = {type(node) for node in reopened.nodes}

    assert classes.issubset({Supplier, Plant, Customer})
    assert Supplier in classes
    assert Plant in classes
    assert Customer in classes


def test_validate_clean_project_has_no_errors(
        sample_project : Project
) -> None:
    issues = sample_project.validate()
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_orphan_edge_flagged_by_validator() -> None:
    raw_nodes : List[Dict[str, Any]] = [
        {"kind": "supplier", "name": "S", "hashKey": "N-S"},
    ]
    raw_edges : List[Dict[str, Any]] = [
        {
            "kind": "lane", "name": "bad", "hashKey": "E-BAD",
            "srcKey": "N-S", "dstKey": "N-MISSING",
        },
    ]
    issues = validate_project(raw_nodes, raw_edges, _manifest())
    codes = [i.code for i in issues if i.severity == "error"]

    assert any("orphan" in code for code in codes)


def test_duplicate_hashkey_flagged_by_validator() -> None:
    raw_nodes : List[Dict[str, Any]] = [
        {"kind": "supplier", "name": "A", "hashKey": "N-DUP"},
        {"kind": "supplier", "name": "B", "hashKey": "N-DUP"},
    ]
    issues = validate_project(raw_nodes, [], _manifest())
    errors = [i for i in issues if i.severity == "error"]

    assert any(i.code == "duplicate-node-key" for i in errors)


def test_lat_lon_out_of_range_flagged() -> None:
    raw_nodes : List[Dict[str, Any]] = [
        {
            "kind": "supplier", "name": "X", "hashKey": "N-X",
            "latitude": 999.0, "longitude": -999.0,
        },
    ]
    issues = validate_project(raw_nodes, [], _manifest())
    codes = {i.code for i in issues if i.severity == "error"}

    assert "latitude-out-of-range" in codes
    assert "longitude-out-of-range" in codes


def test_manifest_schema_version_warning() -> None:
    manifest = {
        "name": "x",
        "arclineSchemaVersion": "9.9.9",
        "createdAt": "2025-01-01T00:00:00+00:00",
    }
    issues = validate_project([], [], manifest)
    warnings = [i for i in issues if i.severity == "warning"]
    assert any(
        i.code == "manifest-schema-version-drift" for i in warnings
    )


def test_yaml_format_roundtrip(
        sample_project : Project, tmp_path : Path
) -> None:
    out = tmp_path / "graph.yaml"
    to_yaml(
        nodes = sample_project.nodes, edges = sample_project.edges,
        path = out,
    )
    nodes, edges = from_yaml(out)

    assert len(nodes) == len(sample_project.nodes)
    assert len(edges) == len(sample_project.edges)


def test_csv_format_roundtrip(tmp_path : Path) -> None:
    nodes_csv = tmp_path / "nodes.csv"
    edges_csv = tmp_path / "edges.csv"

    nodes_csv.write_text(
        "kind,name,hashKey,leadTimeDays\n"
        "supplier,S1,N-S1,3.0\n",
        encoding = "utf-8",
    )
    edges_csv.write_text(
        "kind,name,hashKey,srcKey,dstKey,distanceKm,costPerUnit,"
        "transitDays,mode\n",
        encoding = "utf-8",
    )

    nodes, edges = from_csv(nodes_csv, edges_csv)

    assert len(nodes) == 1
    assert nodes[0].hashKey == "N-S1"
    assert edges == []


def test_parquet_format_roundtrip(
        sample_project : Project, tmp_path : Path
) -> None:
    pytest.importorskip("pyarrow")

    nodes_pq = tmp_path / "nodes.parquet"
    edges_pq = tmp_path / "edges.parquet"

    to_parquet(
        nodes = sample_project.nodes, edges = sample_project.edges,
        nodes_path = nodes_pq, edges_path = edges_pq,
    )

    nodes, edges = from_parquet(nodes_pq, edges_pq)
    assert len(nodes) == len(sample_project.nodes)
    assert len(edges) == len(sample_project.edges)
