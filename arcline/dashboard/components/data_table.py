# -*- encoding: utf-8 -*-

"""
Data Table Components for Nodes and Edges
-----------------------------------------

Wraps :mod:`dash_ag_grid` (when installed) or falls back to
:class:`dash.dash_table.DataTable` to render the project's node and
edge tables. Both tables share the same row shape produced by the
:func:`arcline.io.writers.__node_record__` and ``__edge_record__``
helpers - this keeps the on-disk JSON, the dashboard table, and any
future bulk-edit affordances aligned.
"""

from typing import Any, Dict, List

from arcline.graph.base.graph import AbstractGraph


try:
    import dash_ag_grid as dag

    _HAS_AG_GRID : bool = True
except ImportError:
    dag = None
    _HAS_AG_GRID = False


from dash import dash_table


_NODE_BASE_COLUMNS : List[str] = [
    "kind", "name", "hashKey", "latitude", "longitude",
]
_EDGE_BASE_COLUMNS : List[str] = [
    "kind", "name", "hashKey", "srcKey", "dstKey", "mode",
]


def __node_rows__(graph : AbstractGraph) -> List[Dict[str, Any]]:
    """
    Build the row payload for the node table.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   List[Dict[str, Any]]
    :returns: One dictionary per node with ``kind`` plus every
        serialisable pydantic field.
    """

    rows : List[Dict[str, Any]] = []
    for node in graph.nodes:
        payload : Dict[str, Any] = {"kind": type(node).kind}
        payload.update(node.model_dump())
        rows.append(payload)

    return rows


def __edge_rows__(graph : AbstractGraph) -> List[Dict[str, Any]]:
    """
    Build the row payload for the edge table.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   List[Dict[str, Any]]
    :returns: One dictionary per edge with ``kind``, ``srcKey``,
        ``dstKey`` plus every serialisable pydantic field (except
        the nested node references which are replaced by their
        ``hashKey`` strings).
    """

    rows : List[Dict[str, Any]] = []
    for edge in graph.edges:
        payload : Dict[str, Any] = {"kind": type(edge).kind}
        payload.update(edge.model_dump(exclude = {"srcNode", "dstNode"}))
        payload["srcKey"] = edge.srcNode.hashKey
        payload["dstKey"] = edge.dstNode.hashKey
        rows.append(payload)

    return rows


def __columns_from_rows__(
        rows : List[Dict[str, Any]], base : List[str]
) -> List[str]:
    """
    Compute the ordered column list - start with ``base``, then
    append any additional keys discovered in ``rows``.

    :type  rows: List[Dict[str, Any]]
    :param rows: Row payload.

    :type  base: List[str]
    :param base: Preferred column order.

    :rtype:   List[str]
    :returns: Final ordered column name list.
    """

    seen : set = set(base)
    columns : List[str] = list(base)
    for row in rows:
        for key in row.keys():
            if key not in seen:
                columns.append(key)
                seen.add(key)

    return columns


def __build_grid__(
        rows : List[Dict[str, Any]],
        columns : List[str],
        table_id : str
) -> Any:
    """
    Build either an ag-grid or a fallback :class:`dash_table.DataTable`
    depending on whether :mod:`dash_ag_grid` is installed.

    :type  rows: List[Dict[str, Any]]
    :param rows: Row payload.

    :type  columns: List[str]
    :param columns: Column order.

    :type  table_id: str
    :param table_id: DOM id assigned to the rendered component.

    :rtype:   Any
    :returns: A Dash component instance ready for inclusion in a
        page layout.
    """

    if _HAS_AG_GRID:
        column_defs = [
            {"field": col, "sortable": True, "filter": True}
            for col in columns
        ]
        return dag.AgGrid(
            id = table_id, rowData = rows, columnDefs = column_defs,
            defaultColDef = {"resizable": True, "minWidth": 120},
            dashGridOptions = {
                "rowSelection": "single", "animateRows": True,
            },
            style = {"height": "480px", "width": "100%"},
        )

    return dash_table.DataTable(
        id = table_id, data = rows,
        columns = [{"name": c, "id": c} for c in columns],
        row_selectable = "single", page_size = 25,
        style_table = {"overflowX": "auto"},
        style_cell = {"fontSize": "0.85rem", "padding": "4px 8px"},
    )


def make_node_table(
        graph : AbstractGraph, table_id : str = "node-table"
) -> Any:
    """
    Build the project's node table component.

    :type  graph: AbstractGraph
    :param graph: The live backend graph providing the row data.

    :type  table_id: str
    :param table_id: DOM id assigned to the rendered table.

    :rtype:   Any
    :returns: A Dash table component instance.
    """

    rows = __node_rows__(graph)
    columns = __columns_from_rows__(rows, _NODE_BASE_COLUMNS)
    return __build_grid__(rows, columns, table_id)


def make_edge_table(
        graph : AbstractGraph, table_id : str = "edge-table"
) -> Any:
    """
    Build the project's edge table component.

    :type  graph: AbstractGraph
    :param graph: The live backend graph providing the row data.

    :type  table_id: str
    :param table_id: DOM id assigned to the rendered table.

    :rtype:   Any
    :returns: A Dash table component instance.
    """

    rows = __edge_rows__(graph)
    columns = __columns_from_rows__(rows, _EDGE_BASE_COLUMNS)
    return __build_grid__(rows, columns, table_id)
