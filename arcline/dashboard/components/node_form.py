# -*- encoding: utf-8 -*-

"""
Auto-Generated Node Form Component
----------------------------------

Renders a CRUD form for any concrete :class:`AbstractNode` subclass
by introspecting its pydantic v2 ``model_fields`` map. Each field is
mapped to an appropriate dash-bootstrap-components input control:

  * ``int`` / ``float``       -> :class:`dbc.Input` (``type="number"``)
  * ``bool``                  -> :class:`dbc.Switch`
  * ``Literal[...]``          -> :class:`dbc.Select`
  * ``Dict[str, Any]``        -> :class:`dbc.Textarea` (JSON encoded)
  * everything else           -> :class:`dbc.Input` (``type="text"``)

The component is a thin wrapper around a :class:`dbc.Card`; the
calling page is responsible for embedding it (e.g. inside a modal)
and wiring callbacks against the deterministic input IDs derived
from ``f"{formIdPrefix}-{fieldName}"``.
"""

import json
import typing
from typing import Any, Optional, get_args, get_origin

import dash_bootstrap_components as dbc
from dash import dcc, html
from pydantic.fields import FieldInfo

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import resolve_node


_SKIP_FIELDS : set = {"nodeData"}


def __field_value__(instance : Optional[AbstractNode], name : str) -> Any:
    """
    Read the current value of ``name`` from ``instance`` when present.

    :type  instance: Optional[AbstractNode]
    :param instance: The pre-existing node instance (or ``None`` for
        a brand-new form).

    :type  name: str
    :param name: Field name.

    :rtype:   Any
    :returns: The current field value or ``None`` when missing.
    """

    if instance is None:
        return None

    return instance.model_dump().get(name)


def __is_optional__(annotation : Any) -> bool:
    """
    Detect ``Optional[X]`` / ``Union[X, None]`` annotations.

    :type  annotation: Any
    :param annotation: The pydantic field annotation.

    :rtype:   bool
    :returns: ``True`` when ``None`` is one of the union members.
    """

    if get_origin(annotation) is typing.Union:
        return type(None) in get_args(annotation)

    return False


def __unwrap_optional__(annotation : Any) -> Any:
    """
    Strip the ``None`` member from an ``Optional[X]`` annotation,
    returning the inner type ``X`` (or the original annotation when
    not optional).

    :type  annotation: Any
    :param annotation: The pydantic field annotation.

    :rtype:   Any
    :returns: The non-``None`` member of the union, or the original
        annotation when unchanged.
    """

    if get_origin(annotation) is typing.Union:
        nonNone = [a for a in get_args(annotation) if a is not type(None)]
        if len(nonNone) == 1:
            return nonNone[0]

    return annotation


def inferInput(
        field_info : FieldInfo,
        value : Any,
        inputId : str
) -> Any:
    """
    Build the most appropriate Dash input control for a pydantic
    field. The mapping uses :func:`typing.get_origin` and
    :func:`typing.get_args` to identify ``Optional``, ``Literal`` and
    ``Union`` annotations.

    :type  field_info: FieldInfo
    :param field_info: The pydantic ``FieldInfo`` instance.

    :type  value: Any
    :param value: Initial value to prefill the control with.

    :type  inputId: str
    :param inputId: DOM id assigned to the rendered control.

    :rtype:   Any
    :returns: A Dash component instance ready for inclusion in the
        form layout.
    """

    annotation = __unwrap_optional__(field_info.annotation)
    origin = get_origin(annotation)

    if origin is typing.Literal:
        options = [
            {"label": str(opt), "value": opt}
            for opt in get_args(annotation)
        ]
        return dbc.Select(
            id = inputId, options = options,
            value = value if value is not None else options[0]["value"],
        )

    if annotation is bool:
        return dbc.Switch(
            id = inputId, value = bool(value) if value is not None else False
        )

    if annotation in (int, float):
        return dbc.Input(
            id = inputId, type = "number",
            value = value if value is not None else "",
        )

    if annotation is dict or origin is dict:
        asText = (
            json.dumps(value, indent = 2, default = str)
            if value is not None else "{}"
        )
        return dbc.Textarea(id = inputId, value = asText, rows = 4)

    return dbc.Input(
        id = inputId, type = "text",
        value = str(value) if value is not None else "",
    )


def makeNodeForm(
        kind : str,
        instance : Optional[AbstractNode] = None,
        formIdPrefix : str = "node-form"
) -> dbc.Card:
    """
    Build a :class:`dbc.Card` containing an auto-generated form for
    the concrete node class registered under ``kind``.

    :type  kind: str
    :param kind: Registered node ``kind`` discriminator
        (e.g. ``"supplier"``, ``"plant"``).

    :type  instance: Optional[AbstractNode]
    :param instance: Optional pre-existing node to prefill the form
        with (edit mode); ``None`` produces a blank create form.

    :type  formIdPrefix: str
    :param formIdPrefix: Prefix used to derive deterministic input
        IDs as ``f"{formIdPrefix}-{fieldName}"``.

    :rtype:   dbc.Card
    :returns: A fully-assembled form card with Save / Cancel buttons
        and an inline error region.
    """

    cls = resolve_node(kind)
    rows : list = []

    for name, field_info in cls.model_fields.items():
        if name in _SKIP_FIELDS:
            continue

        inputId = f"{formIdPrefix}-{name}"
        current = __field_value__(instance, name)
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
        className = "node-form-card",
    )
