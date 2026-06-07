# -*- encoding: utf-8 -*-

"""
Project Integrity Validators
----------------------------

Cross-file integrity checks that run on the raw dictionary form of
``nodes.json`` / ``edges.json`` / ``manifest.yaml`` *before* any
pydantic deserialization. Because pydantic only enforces field-level
invariants, this module is responsible for catching duplicate
``hashKey`` collisions, orphan edges, unknown ``kind`` discriminators,
and manifest-version drift.

Issues are returned as :class:`ValidationIssue` records rather than
raised so that callers (CLI, dashboard) can present a complete report
to the user instead of failing on the first problem.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from arcline.graph.registry import iter_edges, iter_nodes
from arcline.io.schema import MANIFEST_SCHEMA_VERSION


@dataclass(frozen = True)
class ValidationIssue:
    """
    A single non-fatal issue discovered during project validation.

    :type  severity: Literal["error", "warning"]
    :param severity: ``"error"`` for blocking problems (duplicate
        keys, orphan edges); ``"warning"`` for soft issues (unknown
        kinds, schema-version drift).

    :type  code: str
    :param code: Short kebab-case identifier suitable for grepping
        and CI assertions (e.g. ``"duplicate-node-key"``).

    :type  message: str
    :param message: Human-readable description of the issue.

    :type  location: Optional[str]
    :param location: Path-style pointer into the offending artifact
        (e.g. ``"edges[3].srcKey"``); ``None`` when the issue is
        artifact-wide.
    """

    severity : Literal["error", "warning"]
    code : str
    message : str
    location : Optional[str] = None


def __duplicate_keys__(
        records : List[Dict[str, Any]],
        kind_label : str,
        code : str
) -> List[ValidationIssue]:
    """
    Helper that walks ``records`` and emits one ``error`` issue per
    duplicate ``hashKey`` occurrence (after the first sighting).

    :type  records: List[Dict[str, Any]]
    :param records: Raw node or edge dictionaries.

    :type  kind_label: str
    :param kind_label: Human label used in the issue message
        (``"node"`` / ``"edge"``).

    :type  code: str
    :param code: Issue code emitted on each duplicate.

    :rtype:   List[ValidationIssue]
    :returns: One issue per duplicate hashKey occurrence.
    """

    seen : Dict[str, int] = {}
    issues : List[ValidationIssue] = []

    for idx, rec in enumerate(records):
        key = rec.get("hashKey")
        if not isinstance(key, str) or not key:
            continue

        if key in seen:
            issues.append(ValidationIssue(
                severity = "error",
                code = code,
                message = (
                    f"Duplicate {kind_label} hashKey {key!r} "
                    f"(first seen at index {seen[key]})."
                ),
                location = f"{kind_label}s[{idx}].hashKey",
            ))
        else:
            seen[key] = idx

    return issues


def validate_project(
        nodes : List[Dict[str, Any]],
        edges : List[Dict[str, Any]],
        manifest : Dict[str, Any]
) -> List[ValidationIssue]:
    """
    Run cross-file integrity checks on the raw dictionary
    representation of an :mod:`arcline` project. The function is
    pure: it does not touch the filesystem and does not deserialize
    into pydantic instances.

    Checks performed:

      * duplicate ``hashKey`` within nodes (error)
      * duplicate ``hashKey`` within edges (error)
      * edge ``srcKey`` / ``dstKey`` not in node hashKeys (error)
      * node / edge ``kind`` not in the type registry (warning)
      * manifest missing required keys (error)
      * manifest ``arclineSchemaVersion`` mismatch (warning)
      * node ``latitude`` / ``longitude`` out of range (error)

    :type  nodes: List[Dict[str, Any]]
    :param nodes: Raw node records as loaded from ``nodes.json``.

    :type  edges: List[Dict[str, Any]]
    :param edges: Raw edge records as loaded from ``edges.json``.

    :type  manifest: Dict[str, Any]
    :param manifest: Raw manifest dictionary as loaded from
        ``manifest.yaml``.

    :rtype:   List[ValidationIssue]
    :returns: Aggregated list of issues; an empty list means the
        project is structurally sound.
    """

    issues : List[ValidationIssue] = []

    issues.extend(__duplicate_keys__(
        nodes, kind_label = "node", code = "duplicate-node-key"
    ))
    issues.extend(__duplicate_keys__(
        edges, kind_label = "edge", code = "duplicate-edge-key"
    ))

    node_keys = {
        rec.get("hashKey") for rec in nodes
        if isinstance(rec.get("hashKey"), str)
    }

    for idx, rec in enumerate(edges):
        src = rec.get("srcKey")
        dst = rec.get("dstKey")

        if not isinstance(src, str) or src not in node_keys:
            issues.append(ValidationIssue(
                severity = "error",
                code = "orphan-edge-source",
                message = (
                    f"Edge at index {idx} references unknown "
                    f"srcKey {src!r}."
                ),
                location = f"edges[{idx}].srcKey",
            ))

        if not isinstance(dst, str) or dst not in node_keys:
            issues.append(ValidationIssue(
                severity = "error",
                code = "orphan-edge-destination",
                message = (
                    f"Edge at index {idx} references unknown "
                    f"dstKey {dst!r}."
                ),
                location = f"edges[{idx}].dstKey",
            ))

    known_node_kinds = { kind for kind, _ in iter_nodes() }
    known_edge_kinds = { kind for kind, _ in iter_edges() }

    for idx, rec in enumerate(nodes):
        kind = rec.get("kind")
        if isinstance(kind, str) and kind not in known_node_kinds:
            issues.append(ValidationIssue(
                severity = "warning",
                code = "unknown-node-kind",
                message = (
                    f"Node kind {kind!r} is not registered; "
                    f"deserialization will fail unless the "
                    f"corresponding class is imported first."
                ),
                location = f"nodes[{idx}].kind",
            ))

        lat = rec.get("latitude")
        lon = rec.get("longitude")

        if isinstance(lat, (int, float)) and not (-90.0 <= lat <= 90.0):
            issues.append(ValidationIssue(
                severity = "error",
                code = "latitude-out-of-range",
                message = (
                    f"Node latitude {lat!r} outside [-90, 90]."
                ),
                location = f"nodes[{idx}].latitude",
            ))

        if isinstance(lon, (int, float)) and not (-180.0 <= lon <= 180.0):
            issues.append(ValidationIssue(
                severity = "error",
                code = "longitude-out-of-range",
                message = (
                    f"Node longitude {lon!r} outside [-180, 180]."
                ),
                location = f"nodes[{idx}].longitude",
            ))

    for idx, rec in enumerate(edges):
        kind = rec.get("kind")
        if isinstance(kind, str) and kind not in known_edge_kinds:
            issues.append(ValidationIssue(
                severity = "warning",
                code = "unknown-edge-kind",
                message = (
                    f"Edge kind {kind!r} is not registered; "
                    f"deserialization will fail unless the "
                    f"corresponding class is imported first."
                ),
                location = f"edges[{idx}].kind",
            ))

    required = ("name", "arclineSchemaVersion", "createdAt")
    for key in required:
        if key not in manifest or manifest.get(key) in (None, ""):
            issues.append(ValidationIssue(
                severity = "error",
                code = "manifest-missing-key",
                message = f"Manifest missing required key {key!r}.",
                location = f"manifest.{key}",
            ))

    declared = manifest.get("arclineSchemaVersion")
    if (
        isinstance(declared, str)
        and declared
        and declared != MANIFEST_SCHEMA_VERSION
    ):
        issues.append(ValidationIssue(
            severity = "warning",
            code = "manifest-schema-version-drift",
            message = (
                f"Manifest arclineSchemaVersion {declared!r} differs "
                f"from current {MANIFEST_SCHEMA_VERSION!r}; a future "
                f"migration step may be required."
            ),
            location = "manifest.arclineSchemaVersion",
        ))

    return issues
