# -*- encoding: utf-8 -*-

"""
Project Artifact JSON Schemas
-----------------------------

JSON Schema (draft 2020-12) dictionaries describing the shape of the
three on-disk artifacts that compose an :mod:`arcline` project:
``nodes.json``, ``edges.json`` and ``manifest.yaml``.

The schemas are intentionally permissive at the leaf level
(``additionalProperties = True``) because each registered ``kind``
extends the abstract pydantic models with its own attribute set.
Strict structural checks (orphan edges, duplicate keys, kind
recognition) live in :mod:`arcline.io.validators` instead.
"""

from typing import Any, Dict


MANIFEST_SCHEMA_VERSION : str = "1.0.0"


NODES_SCHEMA : Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "arcline-nodes",
    "type": "array",
    "items": {
        "type": "object",
        "required": ["kind", "name", "hashKey"],
        "properties": {
            "kind": {"type": "string", "minLength": 1},
            "name": {"type": "string", "minLength": 1},
            "hashKey": {"type": "string", "minLength": 1},
            "latitude": {
                "type": ["number", "null"],
                "minimum": -90.0, "maximum": 90.0,
            },
            "longitude": {
                "type": ["number", "null"],
                "minimum": -180.0, "maximum": 180.0,
            },
            "nodeData": {"type": ["object", "null"]},
        },
        "additionalProperties": True,
    },
}


EDGES_SCHEMA : Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "arcline-edges",
    "type": "array",
    "items": {
        "type": "object",
        "required": ["kind", "name", "hashKey", "srcKey", "dstKey"],
        "properties": {
            "kind": {"type": "string", "minLength": 1},
            "name": {"type": "string", "minLength": 1},
            "hashKey": {"type": "string", "minLength": 1},
            "srcKey": {"type": "string", "minLength": 1},
            "dstKey": {"type": "string", "minLength": 1},
        },
        "additionalProperties": True,
    },
}


MANIFEST_SCHEMA : Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "arcline-manifest",
    "type": "object",
    "required": ["name", "arclineSchemaVersion", "createdAt"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "arclineSchemaVersion": {"type": "string", "minLength": 1},
        "createdAt": {"type": "string", "minLength": 1},
        "updatedAt": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "defaultBackend": {"enum": ["networkx"]},
    },
    "additionalProperties": True,
}
