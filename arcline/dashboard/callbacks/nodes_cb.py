# -*- encoding: utf-8 -*-

"""
Nodes Page Callbacks
--------------------

Wires the dynamic form rendering, modal toggling, and save / delete
side effects on the ``/dashboard/nodes`` page. Mutations are
delegated to :mod:`arcline.dashboard.state.session` so that every
write flows through the single command-pattern choke point.
"""

from typing import Any, Dict, List, Optional, Tuple

from dash import Dash, Input, Output, State, ctx, no_update

from arcline.dashboard.components import make_node_form, make_node_table
from arcline.dashboard.state import session
from arcline.dashboard.state.store import STORE_GRAPH_DIRTY
from arcline.graph.registry import resolve_node


def walk_values(
        node : Any, prefix : str, sink : Dict[str, Any]
) -> None:
    """
    Recursively walk a Dash component-children tree looking for
    rendered input controls whose ``id`` starts with ``prefix``;
    harvest their ``value`` into ``sink`` keyed by the trailing
    field name segment.

    :type  node: Any
    :param node: The current node in the children tree.

    :type  prefix: str
    :param prefix: ID prefix to match (for example ``"node-form-"``).

    :type  sink: Dict[str, Any]
    :param sink: Output mapping populated in place.

    :rtype:   None
    """

    if isinstance(node, dict):
        props = node.get("props", {}) if "props" in node else {}
        node_id = props.get("id")
        if isinstance(node_id, str) and node_id.startswith(prefix):
            field_name = node_id[len(prefix):]
            if field_name and "value" in props:
                sink[field_name] = props.get("value")

        for child_key in ("children",):
            child = props.get(child_key)
            if child is not None:
                walk_values(child, prefix, sink)

    elif isinstance(node, list):
        for item in node:
            walk_values(item, prefix, sink)


def coerce_payload(
        cls : type, payload : Dict[str, Any]
) -> Dict[str, Any]:
    """
    Drop empty values from a harvested form payload so pydantic
    field defaults can take over.

    :type  cls: type
    :param cls: The target pydantic model class.

    :type  payload: Dict[str, Any]
    :param payload: Raw harvested values.

    :rtype:   Dict[str, Any]
    :returns: Cleaned payload restricted to recognised model fields.
    """

    accepted = set(cls.model_fields.keys())
    cleaned : Dict[str, Any] = {}
    for key, value in payload.items():
        if key not in accepted:
            continue
        if value in (None, ""):
            continue
        cleaned[key] = value

    return cleaned


def __refresh_rows__() -> List[Dict[str, Any]]:
    """
    Build the latest row payload from the current session graph.

    :rtype:   List[Dict[str, Any]]
    :returns: Row payload mirroring :func:`make_node_table` input.
    """

    if not session.is_bound():
        return []

    graph = session.get_graph()
    rows : List[Dict[str, Any]] = []
    for node in graph.nodes:
        payload : Dict[str, Any] = {"kind": type(node).kind}
        payload.update(node.model_dump())
        rows.append(payload)

    return rows


def register(app : Dash) -> None:
    """
    Attach all node-page callbacks to ``app``.

    :type  app: Dash
    :param app: The Dash instance to register against.

    :rtype:   None
    """

    @app.callback(
        Output("node-modal", "is_open"),
        Input("add-node-btn", "n_clicks"),
        Input("node-form-cancel", "n_clicks"),
        Input("node-form-save", "n_clicks"),
        State("node-modal", "is_open"),
        prevent_initial_call = True,
    )
    def toggle_node_modal(
            add_clicks : Optional[int],
            cancel_clicks : Optional[int],
            save_clicks : Optional[int],
            is_open : bool,
    ) -> bool:
        """
        Open the modal on Add Node; close on Save / Cancel.
        """

        trigger = ctx.triggered_id
        if trigger == "add-node-btn":
            return True
        return False

    @app.callback(
        Output("node-form-area", "children"),
        Input("node-kind-select", "value"),
        prevent_initial_call = False,
    )
    def render_node_form(kind : Optional[str]) -> Any:
        """
        Re-render the form area when the user selects a different
        node kind.
        """

        if not kind:
            return no_update

        return make_node_form(kind = kind)

    @app.callback(
        Output("node-table", "rowData"),
        Output("node-form-error", "children"),
        Output(STORE_GRAPH_DIRTY, "data"),
        Input("node-form-save", "n_clicks"),
        State("node-form-kind", "data"),
        State("node-form-area", "children"),
        State(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = True,
    )
    def save_node(
            n_clicks : Optional[int],
            kind : Optional[str],
            form_children : Any,
            dirty : Any,
    ) -> Tuple[Any, str, Any]:
        """
        Materialise a node from the harvested form values and push
        it through the session command pipeline.
        """

        if not n_clicks or not kind:
            return no_update, no_update, no_update

        if not session.is_bound():
            return no_update, "No project bound.", no_update

        cls = resolve_node(kind)
        harvested : Dict[str, Any] = {}
        walk_values(form_children, "node-form-", harvested)
        payload = coerce_payload(cls, harvested)

        try:
            instance = cls(**payload)
            session.add_node_cmd(instance)
        except Exception as exc:
            return no_update, f"Failed to save: {exc}", no_update

        next_dirty = (int(dirty) + 1) if isinstance(dirty, int) else 1
        return __refresh_rows__(), "", next_dirty

    @app.callback(
        Output("node-table", "rowData", allow_duplicate = True),
        Output(STORE_GRAPH_DIRTY, "data", allow_duplicate = True),
        Input("delete-node-btn", "n_clicks"),
        State("node-table", "selectedRows"),
        State(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = True,
    )
    def delete_node(
            n_clicks : Optional[int],
            selected : Optional[List[Dict[str, Any]]],
            dirty : Any,
    ) -> Tuple[Any, Any]:
        """
        Remove the currently-selected node (if any) from the graph.
        """

        if not n_clicks or not selected or not session.is_bound():
            return no_update, no_update

        graph = session.get_graph()
        hash_key = selected[0].get("hashKey")
        for cur in graph.nodes:
            if cur.hashKey == hash_key:
                try:
                    session.remove_node_cmd(cur)
                except Exception:
                    return no_update, no_update
                break

        next_dirty = (int(dirty) + 1) if isinstance(dirty, int) else 1
        return __refresh_rows__(), next_dirty
