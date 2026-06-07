# -*- encoding: utf-8 -*-

"""
Edges Page Callbacks
--------------------

Wires the dynamic form rendering, modal toggling, and save / delete
side effects on the ``/dashboard/edges`` page. The form harvests
``srcKey`` and ``dstKey`` as raw hashKey strings - the save handler
resolves them back to the corresponding :class:`AbstractNode`
references before instantiating the concrete edge class.
"""

from typing import Any, Dict, List, Optional, Tuple

from dash import Dash, Input, Output, State, ctx, no_update

from arcline.dashboard.callbacks.nodes_cb import (
    coerce_payload, walk_values,
)
from arcline.dashboard.components import make_edge_form
from arcline.dashboard.state import session
from arcline.dashboard.state.store import STORE_GRAPH_DIRTY
from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import resolve_edge


def __refresh_rows__() -> List[Dict[str, Any]]:
    """
    Build the latest edge row payload from the current session
    graph (mirrors :func:`make_edge_table` input).

    :rtype:   List[Dict[str, Any]]
    :returns: Row payload for ag-grid / DataTable.
    """

    if not session.is_bound():
        return []

    graph = session.get_graph()
    rows : List[Dict[str, Any]] = []
    for edge in graph.edges:
        payload : Dict[str, Any] = {"kind": type(edge).kind}
        payload.update(edge.model_dump(exclude = {"srcNode", "dstNode"}))
        payload["srcKey"] = edge.srcNode.hashKey
        payload["dstKey"] = edge.dstNode.hashKey
        rows.append(payload)

    return rows


def __resolve_node__(hash_key : str) -> Optional[AbstractNode]:
    """
    Look up a node in the session graph by ``hashKey``.

    :type  hash_key: str
    :param hash_key: The target node ``hashKey``.

    :rtype:   Optional[AbstractNode]
    :returns: The matching node instance, or ``None`` when missing.
    """

    if not session.is_bound():
        return None

    for node in session.get_graph().nodes:
        if node.hashKey == hash_key:
            return node

    return None


def register(app : Dash) -> None:
    """
    Attach all edge-page callbacks to ``app``.

    :type  app: Dash
    :param app: The Dash instance to register against.

    :rtype:   None
    """

    @app.callback(
        Output("edge-modal", "is_open"),
        Input("add-edge-btn", "n_clicks"),
        Input("edge-form-cancel", "n_clicks"),
        Input("edge-form-save", "n_clicks"),
        State("edge-modal", "is_open"),
        prevent_initial_call = True,
    )
    def toggle_edge_modal(
            add_clicks : Optional[int],
            cancel_clicks : Optional[int],
            save_clicks : Optional[int],
            is_open : bool,
    ) -> bool:
        """
        Open the modal on Add Edge; close on Save / Cancel.
        """

        trigger = ctx.triggered_id
        if trigger == "add-edge-btn":
            return True
        return False

    @app.callback(
        Output("edge-form-area", "children"),
        Input("edge-kind-select", "value"),
        prevent_initial_call = False,
    )
    def render_edge_form(kind : Optional[str]) -> Any:
        """
        Re-render the edge form area when the kind selection
        changes.
        """

        if not kind:
            return no_update

        return make_edge_form(kind = kind)

    @app.callback(
        Output("edge-table", "rowData"),
        Output("edge-form-error", "children"),
        Output(STORE_GRAPH_DIRTY, "data"),
        Input("edge-form-save", "n_clicks"),
        State("edge-form-kind", "data"),
        State("edge-form-area", "children"),
        State(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = True,
    )
    def save_edge(
            n_clicks : Optional[int],
            kind : Optional[str],
            form_children : Any,
            dirty : Any,
    ) -> Tuple[Any, str, Any]:
        """
        Materialise an edge from the harvested form values and push
        it through the session command pipeline.
        """

        if not n_clicks or not kind:
            return no_update, no_update, no_update

        if not session.is_bound():
            return no_update, "No project bound.", no_update

        cls = resolve_edge(kind)
        harvested : Dict[str, Any] = {}
        walk_values(form_children, "edge-form-", harvested)

        src_key = harvested.pop("srcKey", None)
        dst_key = harvested.pop("dstKey", None)
        if not src_key or not dst_key:
            return no_update, "srcKey and dstKey are required.", no_update

        src_node = __resolve_node__(src_key)
        dst_node = __resolve_node__(dst_key)
        if src_node is None or dst_node is None:
            return (
                no_update,
                f"Unknown endpoint(s): {src_key!r}, {dst_key!r}.",
                no_update,
            )

        payload = coerce_payload(cls, harvested)
        try:
            instance = cls(
                srcNode = src_node, dstNode = dst_node, **payload
            )
            session.add_edge_cmd(instance)
        except Exception as exc:
            return no_update, f"Failed to save: {exc}", no_update

        next_dirty = (int(dirty) + 1) if isinstance(dirty, int) else 1
        return __refresh_rows__(), "", next_dirty

    @app.callback(
        Output("edge-table", "rowData", allow_duplicate = True),
        Output(STORE_GRAPH_DIRTY, "data", allow_duplicate = True),
        Input("delete-edge-btn", "n_clicks"),
        State("edge-table", "selectedRows"),
        State(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = True,
    )
    def delete_edge(
            n_clicks : Optional[int],
            selected : Optional[List[Dict[str, Any]]],
            dirty : Any,
    ) -> Tuple[Any, Any]:
        """
        Remove the currently-selected edge (if any) from the graph.
        """

        if not n_clicks or not selected or not session.is_bound():
            return no_update, no_update

        graph = session.get_graph()
        hash_key = selected[0].get("hashKey")
        src_key = selected[0].get("srcKey")
        dst_key = selected[0].get("dstKey")
        for cur in graph.edges:
            if cur.hashKey == hash_key \
                    and cur.srcNode.hashKey == src_key \
                    and cur.dstNode.hashKey == dst_key:
                try:
                    session.remove_edge_cmd(cur)
                except Exception:
                    return no_update, no_update
                break

        next_dirty = (int(dirty) + 1) if isinstance(dirty, int) else 1
        return __refresh_rows__(), next_dirty
