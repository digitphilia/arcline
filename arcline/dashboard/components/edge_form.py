# -*- encoding: utf-8 -*-

"""
Auto-Generated Edge Form Component
----------------------------------

The edge form mirrors :func:`arcline.dashboard.components.node_form`
but augments the pydantic-derived inputs with two
:class:`dbc.Select` dropdowns at the top of the card for picking the
edge's source and destination node by ``hashKey``.

These two selectors are *not* pydantic fields on the edge class -
the underlying :class:`AbstractEdge` stores ``srcNode`` and
``dstNode`` as fully materialised :class:`AbstractNode` references.
The conversion between ``srcKey`` / ``dstKey`` form fields and the
nested node references is performed by the callback layer.
"""

from typing import Optional

import dash_bootstrap_components as dbc
from dash import dcc, html

from arcline.dashboard.components.node_form import inferInput
from arcline.dashboard.state import session
from arcline.graph.base.edges import AbstractEdge
from arcline.graph.registry import resolve_edge


_SKIP_FIELDS : set = {"srcNode", "dstNode"}


def __node_options__() -> list:
    """
    Build a ``[{"label": ..., "value": ...}]`` list of every node
    currently present in the bound graph.

    Returns an empty list when no project is bound, allowing the
    edge form to be rendered as a placeholder on pages that load
    before a project is opened.

    :rtype:   list
    :returns: Options payload suitable for :class:`dbc.Select`.
    """

    if not session.isBound():
        return []

    graph = session.getGraph()
    return [
        {
            "label": f"{node.name} ({node.hashKey})",
            "value": node.hashKey,
        }
        for node in graph.nodes
    ]


def makeEdgeForm(
        kind : str,
        instance : Optional[AbstractEdge] = None,
        formIdPrefix : str = "edge-form"
) -> dbc.Card:
    """
    Build a :class:`dbc.Card` containing an auto-generated form for
    the concrete edge class registered under ``kind``.

    :type  kind: str
    :param kind: Registered edge ``kind`` discriminator
        (e.g. ``"lane"``, ``"production"``, ``"storage"``).

    :type  instance: Optional[AbstractEdge]
    :param instance: Optional pre-existing edge to prefill the form
        with (edit mode); ``None`` produces a blank create form.

    :type  formIdPrefix: str
    :param formIdPrefix: Prefix used to derive deterministic input
        IDs as ``f"{formIdPrefix}-{fieldName}"``.

    :rtype:   dbc.Card
    :returns: A fully-assembled form card with Save / Cancel buttons
        and an inline error region.
    """

    cls = resolve_edge(kind)
    options = __node_options__()

    srcValue = instance.srcNode.hashKey if instance is not None else None
    dstValue = instance.dstNode.hashKey if instance is not None else None

    rows : list = [
        dbc.Row(
            [
                dbc.Label(
                    "srcKey", html_for = f"{formIdPrefix}-srcKey",
                    width = 4, className = "text-end fw-bold",
                ),
                dbc.Col(
                    dbc.Select(
                        id = f"{formIdPrefix}-srcKey",
                        options = options, value = srcValue,
                    ),
                    width = 8,
                ),
            ],
            className = "mb-2",
        ),
        dbc.Row(
            [
                dbc.Label(
                    "dstKey", html_for = f"{formIdPrefix}-dstKey",
                    width = 4, className = "text-end fw-bold",
                ),
                dbc.Col(
                    dbc.Select(
                        id = f"{formIdPrefix}-dstKey",
                        options = options, value = dstValue,
                    ),
                    width = 8,
                ),
            ],
            className = "mb-2",
        ),
    ]

    for name, field_info in cls.model_fields.items():
        if name in _SKIP_FIELDS:
            continue

        inputId = f"{formIdPrefix}-{name}"
        current = (
            instance.model_dump().get(name) if instance is not None
            else None
        )
        control = inferInput(field_info, current, inputId)

        rows.append(
            dbc.Row(
                [
                    dbc.Label(
                        name, html_for = inputId, width = 4,
                        className = "text-end fw-bold",
                    ),
                    dbc.Col(control, width = 8),
                ],
                className = "mb-2",
            )
        )

    buttons = dbc.Row(
        [
            dbc.Col(
                dbc.Button(
                    "Save", id = f"{formIdPrefix}-save",
                    color = "primary", className = "me-2",
                ),
                width = "auto",
            ),
            dbc.Col(
                dbc.Button(
                    "Cancel", id = f"{formIdPrefix}-cancel",
                    color = "secondary", outline = True,
                ),
                width = "auto",
            ),
        ],
        className = "mt-3",
    )

    body = dbc.CardBody(
        [
            dbc.Form(rows),
            html.Div(
                id = f"{formIdPrefix}-error",
                className = "text-danger small mt-2",
            ),
            buttons,
            dcc.Store(id = f"{formIdPrefix}-kind", data = kind),
        ]
    )

    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    f"{kind.capitalize()} - "
                    f"{'Edit' if instance is not None else 'Create'}",
                    className = "mb-0",
                )
            ),
            body,
        ],
        className = "edge-form-card",
    )
