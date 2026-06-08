# -*- encoding: utf-8 -*-

"""
Visualize Page Callbacks
------------------------

Wire the D3 :class:`NetworkCanvas` to the live graph session:

  * click       -> update selection panel
  * dbl-click   -> open edit form for entity
  * pendingEdge -> open edge-create form prefilled with src/dst
  * + Node / + Edge FAB buttons -> open create form
  * Connect toggle -> push ``connectMode`` to the canvas
  * Layout mode    -> push ``layoutMode`` to the canvas
  * Save / form-save -> mutate via :mod:`arcline.dashboard.state`
                        command pattern, refresh canvas, toast
"""

from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
from dash import (
    ALL, MATCH, Dash, Input, Output, State, ctx, html, no_update,
)

from arcline.dashboard.callbacks.nodes_cb import coercePayload, walkValues
from arcline.dashboard.components import makeEdgeForm, makeNodeForm
from arcline.dashboard.state import session
from arcline.dashboard.state.store import STORE_GRAPH_DIRTY
from arcline.dashboard.theme import canvasTheme, serializeGraph
from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import resolve_edge, resolve_node


NODE_FORM_PREFIX : str = "viz-nform"
EDGE_FORM_PREFIX : str = "viz-eform"


def __findNode__(hashKey : str) -> Optional[AbstractNode]:
    """Locate a node by hashKey in the bound session graph."""
    if not session.isBound():
        return None
    for node in session.getGraph().nodes:
        if node.hashKey == hashKey:
            return node
    return None


def __findEdge__(hashKey : str) -> Optional[AbstractEdge]:
    """Locate an edge by hashKey in the bound session graph."""
    if not session.isBound():
        return None
    for edge in session.getGraph().edges:
        if edge.hashKey == hashKey:
            return edge
    return None


def __selectionPanel__(kind : Optional[str], hashKey : Optional[str]) -> Any:
    """
    Build the read-only attribute view shown in the side drawer.
    """
    if not kind or not hashKey:
        return html.Div(
            "Click a node or edge to inspect, double-click to edit.",
            className = "text-muted small",
        )

    entity : Any = (
        __findNode__(hashKey) if kind == "node" else __findEdge__(hashKey)
    )
    if entity is None:
        return dbc.Alert(
            "Selection no longer exists in the graph.",
            color = "warning", className = "small mb-0",
        )

    payload : Dict[str, Any] = {
        "kind": type(entity).kind, **entity.model_dump(),
    }
    rows : List[Any] = []
    for key, value in payload.items():
        rows.append(
            html.Div(
                [
                    html.Span(f"{key}", className = "attr-key"),
                    html.Span(str(value), className = "attr-val"),
                ],
                className = "attr-row",
            )
        )
    return html.Div(rows)


def __freshDirty__(dirty : Any) -> int:
    """Bump the integer dirty-tick used to invalidate the canvas."""
    try:
        return int(dirty) + 1
    except (TypeError, ValueError):
        return 1


def __buildEdgeFromForm__(
        kind : str, harvested : Dict[str, Any],
) -> AbstractEdge:
    """
    Resolve src/dst by hashKey, drop them out of the payload, build
    the edge.
    """
    cls = resolve_edge(kind)
    srcKey = harvested.pop("srcKey", None)
    dstKey = harvested.pop("dstKey", None)
    if not srcKey or not dstKey:
        raise ValueError("Both srcKey and dstKey are required.")
    srcNode = __findNode__(srcKey)
    dstNode = __findNode__(dstKey)
    if srcNode is None or dstNode is None:
        raise ValueError("srcKey / dstKey do not resolve to nodes.")
    cleaned = coercePayload(cls, harvested)
    return cls(srcNode = srcNode, dstNode = dstNode, **cleaned)


def register(app : Dash) -> None:
    """
    Attach all visualize-page callbacks to ``app``.
    """

    # ── push graph + layout + connectMode + theme into canvas ──
    @app.callback(
        Output("viz-canvas", "nodes"),
        Output("viz-canvas", "edges"),
        Output("viz-canvas", "ts"),
        Input(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = False,
    )
    def refreshCanvas(dirty : Any) -> Tuple[Any, Any, Any]:
        if not session.isBound():
            return no_update, no_update, no_update
        serialized = serializeGraph(session.getGraph())
        tick = int(dirty) if isinstance(dirty, int) else 0
        return serialized["nodes"], serialized["edges"], tick

    @app.callback(
        Output("viz-canvas", "layoutMode"),
        Input("viz-mode", "value"),
        prevent_initial_call = False,
    )
    def pushLayoutMode(mode : Optional[str]) -> Any:
        return mode or "force"

    @app.callback(
        Output("viz-canvas", "connectMode"),
        Output("viz-connect-mode", "data"),
        Output("viz-connect-toggle", "color"),
        Output("viz-connect-toggle", "outline"),
        Input("viz-connect-toggle", "n_clicks"),
        State("viz-connect-mode", "data"),
        prevent_initial_call = True,
    )
    def toggleConnect(n : Optional[int], current : Any) -> Tuple[Any, ...]:
        active = not bool(current)
        return (
            active, active,
            "primary" if active else "secondary",
            not active,
        )

    # ── selection sync ──
    @app.callback(
        Output("viz-selected-panel", "children"),
        Output("viz-canvas", "selectedId"),
        Input("viz-canvas", "clickedElement"),
        prevent_initial_call = True,
    )
    def syncSelection(payload : Optional[Dict[str, Any]]) -> Any:
        if not payload:
            return no_update, no_update
        kind = payload.get("kind")
        hashKey = payload.get("hashKey")
        return __selectionPanel__(kind, hashKey), hashKey

    # ── modal open: create node ──
    @app.callback(
        Output("viz-modal", "is_open"),
        Output("viz-modal-title", "children"),
        Output("viz-modal-body", "children"),
        Input({"type": "viz-add-node", "kind": ALL}, "n_clicks"),
        Input({"type": "viz-add-edge", "kind": ALL}, "n_clicks"),
        Input("viz-canvas", "dblClickedElement"),
        Input("viz-canvas", "pendingEdge"),
        Input(f"{NODE_FORM_PREFIX}-cancel", "n_clicks"),
        Input(f"{EDGE_FORM_PREFIX}-cancel", "n_clicks"),
        prevent_initial_call = True,
    )
    def openModal(
            addNodeClicks : List[Optional[int]],
            addEdgeClicks : List[Optional[int]],
            dblClicked : Optional[Dict[str, Any]],
            pendingEdge : Optional[Dict[str, Any]],
            nCancel : Optional[int],
            eCancel : Optional[int],
    ) -> Tuple[Any, Any, Any]:
        trigger = ctx.triggered_id
        if trigger is None:
            return no_update, no_update, no_update

        # cancel buttons close the modal
        if trigger in (f"{NODE_FORM_PREFIX}-cancel",
                       f"{EDGE_FORM_PREFIX}-cancel"):
            return False, no_update, no_update

        # dropdown item -> create form
        if isinstance(trigger, dict):
            kind = trigger.get("kind")
            if trigger.get("type") == "viz-add-node" and any(
                    n for n in addNodeClicks if n
            ):
                form = makeNodeForm(
                    kind = kind, formIdPrefix = NODE_FORM_PREFIX,
                )
                return True, f"Create {kind.capitalize()}", form
            if trigger.get("type") == "viz-add-edge" and any(
                    n for n in addEdgeClicks if n
            ):
                form = makeEdgeForm(
                    kind = kind, formIdPrefix = EDGE_FORM_PREFIX,
                )
                return True, f"Create {kind.capitalize()} Edge", form
            return no_update, no_update, no_update

        # dbl-click -> edit form
        if trigger == "viz-canvas" and dblClicked:
            sel = dblClicked
            kind = sel.get("kind"); hashKey = sel.get("hashKey")
            if kind == "node" and hashKey:
                instance = __findNode__(hashKey)
                if instance is not None:
                    form = makeNodeForm(
                        kind = type(instance).kind, instance = instance,
                        formIdPrefix = NODE_FORM_PREFIX,
                    )
                    return (
                        True,
                        f"Edit {type(instance).kind.capitalize()} - "
                        f"{instance.name}",
                        form,
                    )
            if kind == "edge" and hashKey:
                instance = __findEdge__(hashKey)
                if instance is not None:
                    form = makeEdgeForm(
                        kind = type(instance).kind, instance = instance,
                        formIdPrefix = EDGE_FORM_PREFIX,
                    )
                    return (
                        True,
                        f"Edit {type(instance).kind.capitalize()} - "
                        f"{instance.hashKey}",
                        form,
                    )

        # pending drag-connect -> new lane prefilled
        if trigger == "viz-canvas" and pendingEdge:
            srcKey = pendingEdge.get("srcKey")
            dstKey = pendingEdge.get("dstKey")
            if srcKey and dstKey:
                form = makeEdgeForm(
                    kind = "lane", formIdPrefix = EDGE_FORM_PREFIX,
                )
                # prefill src/dst by injecting initial selection
                # (the form already accepts options; default value
                # is None - patch via clientside on first paint is
                # overkill, so we expose hidden stores)
                wrapper = html.Div(
                    [
                        form,
                        html.Div(
                            id = f"{EDGE_FORM_PREFIX}-prefill-src",
                            **{"data-value": srcKey},
                            style = {"display": "none"},
                        ),
                        html.Div(
                            id = f"{EDGE_FORM_PREFIX}-prefill-dst",
                            **{"data-value": dstKey},
                            style = {"display": "none"},
                        ),
                    ]
                )
                return True, "Connect: Create Lane", wrapper

        return no_update, no_update, no_update

    # prefill src/dst dropdowns when connect-mode produced an edge
    app.clientside_callback(
        """
        function(srcWrap, dstWrap) {
            if (!srcWrap || !dstWrap) {
                return [window.dash_clientside.no_update,
                        window.dash_clientside.no_update];
            }
            var src = srcWrap && srcWrap.props
                ? srcWrap.props['data-value'] : null;
            var dst = dstWrap && dstWrap.props
                ? dstWrap.props['data-value'] : null;
            return [src, dst];
        }
        """,
        Output(f"{EDGE_FORM_PREFIX}-srcKey", "value", allow_duplicate = True),
        Output(f"{EDGE_FORM_PREFIX}-dstKey", "value", allow_duplicate = True),
        Input(f"{EDGE_FORM_PREFIX}-prefill-src", "data-value"),
        Input(f"{EDGE_FORM_PREFIX}-prefill-dst", "data-value"),
        prevent_initial_call = True,
    )

    # ── save: NODE (create or update) ──
    @app.callback(
        Output("viz-modal", "is_open", allow_duplicate = True),
        Output(STORE_GRAPH_DIRTY, "data", allow_duplicate = True),
        Output("viz-toast", "is_open", allow_duplicate = True),
        Output("viz-toast", "children", allow_duplicate = True),
        Output("viz-toast", "icon", allow_duplicate = True),
        Output("viz-toast", "header", allow_duplicate = True),
        Output(f"{NODE_FORM_PREFIX}-error", "children", allow_duplicate = True),
        Input(f"{NODE_FORM_PREFIX}-save", "n_clicks"),
        State(f"{NODE_FORM_PREFIX}-kind", "data"),
        State("viz-modal-body", "children"),
        State(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = True,
    )
    def saveNode(
            n_clicks : Optional[int],
            kind : Optional[str],
            body : Any,
            dirty : Any,
    ) -> Tuple[Any, ...]:
        if not n_clicks or not kind or not session.isBound():
            return (no_update,) * 7

        cls = resolve_node(kind)
        harvested : Dict[str, Any] = {}
        walkValues(body, f"{NODE_FORM_PREFIX}-", harvested)
        payload = coercePayload(cls, harvested)

        try:
            instance = cls(**payload)
            existing = __findNode__(instance.hashKey)
            if existing is None:
                session.addNodeCmd(instance)
                verb = "added"
            else:
                changes = instance.model_dump(exclude_unset = False)
                changes.pop("hashKey", None)
                session.updateNodeCmd(existing, **changes)
                verb = "updated"
        except Exception as exc:
            return (
                no_update, no_update, True, str(exc), "danger",
                "Validation error", str(exc),
            )

        return (
            False, __freshDirty__(dirty),
            True, f"Node {instance.name} {verb}.",
            "success", "Saved", "",
        )

    # ── save: EDGE (create or update) ──
    @app.callback(
        Output("viz-modal", "is_open", allow_duplicate = True),
        Output(STORE_GRAPH_DIRTY, "data", allow_duplicate = True),
        Output("viz-toast", "is_open", allow_duplicate = True),
        Output("viz-toast", "children", allow_duplicate = True),
        Output("viz-toast", "icon", allow_duplicate = True),
        Output("viz-toast", "header", allow_duplicate = True),
        Output(f"{EDGE_FORM_PREFIX}-error", "children", allow_duplicate = True),
        Input(f"{EDGE_FORM_PREFIX}-save", "n_clicks"),
        State(f"{EDGE_FORM_PREFIX}-kind", "data"),
        State("viz-modal-body", "children"),
        State(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = True,
    )
    def saveEdge(
            n_clicks : Optional[int],
            kind : Optional[str],
            body : Any,
            dirty : Any,
    ) -> Tuple[Any, ...]:
        if not n_clicks or not kind or not session.isBound():
            return (no_update,) * 7

        harvested : Dict[str, Any] = {}
        walkValues(body, f"{EDGE_FORM_PREFIX}-", harvested)

        try:
            instance = __buildEdgeFromForm__(kind, harvested)
            existing = __findEdge__(instance.hashKey)
            if existing is None:
                session.addEdgeCmd(instance)
                verb = "added"
            else:
                changes = instance.model_dump(exclude_unset = False)
                changes.pop("hashKey", None)
                changes.pop("srcNode", None)
                changes.pop("dstNode", None)
                session.updateEdgeCmd(existing, **changes)
                verb = "updated"
        except Exception as exc:
            return (
                no_update, no_update, True, str(exc), "danger",
                "Validation error", str(exc),
            )

        return (
            False, __freshDirty__(dirty),
            True, f"Edge {instance.hashKey} {verb}.",
            "success", "Saved", "",
        )

    # ── global Save (navbar + FAB) ──
    @app.callback(
        Output("viz-toast", "is_open", allow_duplicate = True),
        Output("viz-toast", "children", allow_duplicate = True),
        Output("viz-toast", "icon", allow_duplicate = True),
        Output("viz-toast", "header", allow_duplicate = True),
        Input("viz-save-btn", "n_clicks"),
        Input("arc-global-save-btn", "n_clicks"),
        prevent_initial_call = True,
    )
    def saveProject(
            fabClicks : Optional[int], navClicks : Optional[int],
    ) -> Tuple[Any, ...]:
        if not (fabClicks or navClicks) or not session.isBound():
            return no_update, no_update, no_update, no_update
        try:
            session.saveProject()
        except Exception as exc:
            return True, str(exc), "danger", "Save failed"
        return True, "Project saved to disk.", "success", "Saved"

    # ── delete via right-click context (simple: delete selection) ──
    @app.callback(
        Output(STORE_GRAPH_DIRTY, "data", allow_duplicate = True),
        Output("viz-toast", "is_open", allow_duplicate = True),
        Output("viz-toast", "children", allow_duplicate = True),
        Output("viz-toast", "icon", allow_duplicate = True),
        Output("viz-toast", "header", allow_duplicate = True),
        Output("viz-selected-panel", "children", allow_duplicate = True),
        Input("viz-canvas", "contextElement"),
        State(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = True,
    )
    def contextDelete(
            payload : Optional[Dict[str, Any]], dirty : Any,
    ) -> Tuple[Any, ...]:
        # MVP UX: right-click on a node/edge deletes it
        # (avoids needing a full DOM context menu component)
        if not payload or not session.isBound():
            return (no_update,) * 6
        kind = payload.get("kind"); hashKey = payload.get("hashKey")
        if not kind or not hashKey:
            return (no_update,) * 6
        try:
            if kind == "node":
                target = __findNode__(hashKey)
                if target is None:
                    return (no_update,) * 6
                session.removeNodeCmd(target)
                msg = f"Node {target.name} deleted."
            else:
                target = __findEdge__(hashKey)
                if target is None:
                    return (no_update,) * 6
                session.removeEdgeCmd(target)
                msg = f"Edge {target.hashKey} deleted."
        except Exception as exc:
            return (
                no_update, True, str(exc), "danger",
                "Delete failed", no_update,
            )

        return (
            __freshDirty__(dirty),
            True, msg, "warning", "Deleted",
            __selectionPanel__(None, None),
        )

    # silence unused import warning - MATCH reserved for future expansion
    _ = MATCH
