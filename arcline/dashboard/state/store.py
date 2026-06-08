# -*- encoding: utf-8 -*-

"""
Client-Side Store Keys
----------------------

Centralised string identifiers for every ``dcc.Store`` that lives in
the dashboard layout. Putting the IDs here (instead of inlining them
in each page) lets callbacks reference a single canonical constant
and keeps the front-end / back-end contract explicit.

The two thin helpers (:func:`serializeMeta` / :func:`deserializeMeta`)
wrap :func:`json.dumps` / :func:`json.loads` so callers can round-trip
arbitrary JSON-serialisable mapping payloads through a store slot.
"""

import json
from typing import Any, Dict, Optional


STORE_PROJECT_PATH : str = "store-project-path"
STORE_GRAPH_DIRTY : str = "store-graph-dirty"
STORE_SELECTED_NODE : str = "store-selected-node"
STORE_SELECTED_EDGE : str = "store-selected-edge"
STORE_VIZ_MODE : str = "store-viz-mode"
STORE_REFRESH_TICK : str = "store-refresh-tick"


ALL_STORES : list = [
    STORE_PROJECT_PATH,
    STORE_GRAPH_DIRTY,
    STORE_SELECTED_NODE,
    STORE_SELECTED_EDGE,
    STORE_VIZ_MODE,
    STORE_REFRESH_TICK,
]


def serializeMeta(meta : Dict[str, Any]) -> str:
    """
    Serialise a metadata mapping into a compact JSON string suitable
    for a ``dcc.Store`` slot.

    :type  meta: Dict[str, Any]
    :param meta: A JSON-serialisable mapping payload.

    :rtype:   str
    :returns: Compact JSON string representation.
    """

    return json.dumps(meta, default = str)


def deserializeMeta(raw : Optional[str]) -> Dict[str, Any]:
    """
    Deserialise a JSON-encoded metadata mapping coming back from a
    ``dcc.Store`` slot.

    :type  raw: Optional[str]
    :param raw: The raw JSON string previously emitted by
        :func:`serializeMeta`; treated as an empty mapping when
        ``None`` or empty.

    :rtype:   Dict[str, Any]
    :returns: Deserialised mapping payload (empty dict if ``raw`` is
        falsy or malformed).
    """

    if not raw:
        return {}

    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return {}

    return payload if isinstance(payload, dict) else {}
