# -*- encoding: utf-8 -*-

"""
Dashboard Theme Tokens
======================

Central source-of-truth for the dashboard's visual language. Tokens
are exposed in two complementary shapes:

  * :data:`DARK_TOKENS` / :data:`LIGHT_TOKENS` - flat dict of CSS-var
    name -> colour string. ``styles.css`` materialises the same names
    as CSS variables under ``html[data-theme="dark"]`` /
    ``html[data-theme="light"]`` so React / D3 code and stylesheet
    rules see the *same* values.
  * :func:`canvasTheme` - subset of tokens forwarded to the
    :class:`NetworkCanvas` component so D3 renders strokes / labels /
    backgrounds that match the active CSS theme.

Per-kind colour and icon resolution piggy-backs on the existing
:mod:`arcline.dashboard.viz.styles` probes so class-level overrides
(``nodeColor``, ``imagePath``) remain the single point of truth for
domain-specific colour choices.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from arcline.dashboard.viz.styles import kindColor, kindIcon
from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.graph import AbstractGraph
from arcline.graph.base.nodes import AbstractNode


DARK_TOKENS : Dict[str, str] = {
    "bg":             "#0d1017",
    "surface":        "rgba(24, 27, 34, 0.72)",
    "surface2":       "rgba(31, 36, 46, 0.85)",
    "border":         "rgba(255, 255, 255, 0.08)",
    "borderStrong":   "rgba(255, 255, 255, 0.18)",
    "text":           "#e6e8ee",
    "muted":          "#8a93a6",
    "accent":         "#7aa2ff",
    "accentSoft":     "rgba(122, 162, 255, 0.18)",
    "success":        "#4ade80",
    "warning":        "#fbbf24",
    "danger":         "#f87171",
    "edge":           "rgba(255, 255, 255, 0.32)",
    "edgeHighlight":  "#7aa2ff",
    "nodeStroke":     "rgba(255, 255, 255, 0.18)",
    "selectionRing":  "#ffd166",
    "pendingEdge":    "#ffd166",
    "glassBg":        "rgba(20, 23, 30, 0.55)",
    "glassBlur":      "18px",
}

LIGHT_TOKENS : Dict[str, str] = {
    "bg":             "#f6f7fb",
    "surface":        "rgba(255, 255, 255, 0.78)",
    "surface2":       "rgba(255, 255, 255, 0.95)",
    "border":         "rgba(15, 23, 42, 0.10)",
    "borderStrong":   "rgba(15, 23, 42, 0.22)",
    "text":           "#1f2937",
    "muted":          "#64748b",
    "accent":         "#2563eb",
    "accentSoft":     "rgba(37, 99, 235, 0.10)",
    "success":        "#16a34a",
    "warning":        "#d97706",
    "danger":         "#dc2626",
    "edge":           "rgba(15, 23, 42, 0.45)",
    "edgeHighlight":  "#2563eb",
    "nodeStroke":     "rgba(15, 23, 42, 0.18)",
    "selectionRing":  "#f59e0b",
    "pendingEdge":    "#f59e0b",
    "glassBg":        "rgba(255, 255, 255, 0.70)",
    "glassBlur":      "18px",
}


def canvasTheme(themeName : str = "dark") -> Dict[str, str]:
    """
    Subset of the active token table that the :class:`NetworkCanvas`
    component reads at render time. The subset is intentionally
    narrow: only colours D3 actually paints.

    :type  themeName: str
    :param themeName: ``"dark"`` or ``"light"``; falls back to dark
        for unknown names.

    :rtype:   Dict[str, str]
    :returns: Mapping forwarded as the ``theme`` prop on the canvas.
    """

    tokens = LIGHT_TOKENS if themeName == "light" else DARK_TOKENS
    canvasKeys = (
        "bg", "surface", "border", "text", "muted", "accent",
        "edge", "edgeHighlight", "nodeStroke",
        "selectionRing", "pendingEdge",
    )
    return {key: tokens[key] for key in canvasKeys}


def _iconUrl(iconPath : Optional[str], iconBase : str) -> Optional[str]:
    """
    Resolve a registry-provided icon path to a URL the browser can
    fetch. Existing classes expose absolute filesystem paths via
    ``imagePath``; we only need the basename when serving from
    ``/assets/icons/``.

    :type  iconPath: Optional[str]
    :param iconPath: Raw value returned by :func:`kindIcon`.

    :type  iconBase: str
    :param iconBase: URL prefix (typically ``/assets/icons/``).

    :rtype:   Optional[str]
    :returns: A browser-resolvable URL, or ``None`` when no icon.
    """

    if not iconPath:
        return None
    base = iconBase.rstrip("/") + "/"
    fileName = iconPath.replace("\\", "/").rsplit("/", 1)[-1]
    return base + quote(fileName)


def nodeToDict(
        node : AbstractNode, iconBase : str = "/assets/icons/"
) -> Dict[str, Any]:
    """
    Serialise an :class:`AbstractNode` into the flat JSON shape the
    canvas consumes.

    :type  node: AbstractNode
    :param node: The node to serialise.

    :type  iconBase: str
    :param iconBase: URL prefix for icons.

    :rtype:   Dict[str, Any]
    :returns: ``{hashKey, kind, name, color, icon, lat, lng}``.
    """

    kind = type(node).kind
    payload = node.model_dump()
    return {
        "hashKey": node.hashKey,
        "kind": kind,
        "name": getattr(node, "name", node.hashKey),
        "color": kindColor(kind, "node"),
        "icon": _iconUrl(kindIcon(kind), iconBase),
        "lat": payload.get("latitude"),
        "lng": payload.get("longitude"),
    }


def edgeToDict(edge : AbstractEdge) -> Dict[str, Any]:
    """
    Serialise an :class:`AbstractEdge` into the flat JSON shape the
    canvas consumes.

    :type  edge: AbstractEdge
    :param edge: The edge to serialise.

    :rtype:   Dict[str, Any]
    :returns: ``{hashKey, kind, srcKey, dstKey, color, width}``.
    """

    kind = type(edge).kind
    return {
        "hashKey": edge.hashKey,
        "kind": kind,
        "srcKey": edge.srcNode.hashKey,
        "dstKey": edge.dstNode.hashKey,
        "color": kindColor(kind, "edge"),
        "width": 1.6,
    }


def serializeGraph(
        graph : AbstractGraph, iconBase : str = "/assets/icons/"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Serialise an entire graph into the canvas wire format.

    :type  graph: AbstractGraph
    :param graph: The live graph instance.

    :type  iconBase: str
    :param iconBase: URL prefix for icons.

    :rtype:   Dict[str, List[Dict[str, Any]]]
    :returns: ``{"nodes": [...], "edges": [...]}``.
    """

    return {
        "nodes": [nodeToDict(n, iconBase) for n in graph.nodes],
        "edges": [edgeToDict(e) for e in graph.edges],
    }
