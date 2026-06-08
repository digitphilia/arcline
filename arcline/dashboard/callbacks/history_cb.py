# -*- encoding: utf-8 -*-

"""
History Page Callbacks
----------------------

Wires the ``/dashboard/history`` page selectors to the historian:

  * Populates the entity dropdown from the bound graph, scoped to the
    chosen entity type and to classes that declare a ``history``
    ClassVar.
  * Drives the attribute dropdown off the selected entity.
  * Fetches the series (cache-first; ``Refresh from DB`` bypasses the
    cache for one call), renders the time-series + distribution charts,
    and emits a summary card.
  * Downsamples series longer than ``LTTB_THRESHOLD`` via the LTTB
    algorithm to keep the browser responsive.
"""

from __future__ import annotations

from typing import Any, List

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, html, no_update

from arcline.dashboard.state import session
from arcline.historian import (
    HistorianError,
    distribution,
    fetch,
    resample,
    rolling,
    specFor,
    summary,
)

LTTB_THRESHOLD : int = 50_000


def _entityType(cls) -> str:
    from arcline.graph.base.edges import AbstractEdge
    return "edge" if issubclass(cls, AbstractEdge) else "node"


def _entityChoices(graph, kind: str) -> List[dict]:
    options = []
    pool = graph.edges if kind == "edge" else graph.nodes
    for entity in pool:
        cls = type(entity)
        if not getattr(cls, "history", {}):
            continue
        if _entityType(cls) != kind:
            continue
        options.append({
            "label": f"{cls.__name__} - {entity.name} ({entity.hashKey})",
            "value": entity.hashKey,
        })
    return options


def _findEntity(graph, hashKey: str):
    for n in graph.nodes:
        if n.hashKey == hashKey:
            return n
    for e in graph.edges:
        if e.hashKey == hashKey:
            return e
    return None


def _lttbDownsample(frame, target: int = LTTB_THRESHOLD):
    if len(frame) <= target:
        return frame
    import numpy as np
    bucketSize = (len(frame) - 2) / (target - 2)
    indices = [0]
    for i in range(target - 2):
        start = int((i + 1) * bucketSize) + 1
        end = min(int((i + 2) * bucketSize) + 1, len(frame) - 1)
        if start >= end:
            indices.append(start)
            continue
        valuesSlice = frame["value"].iloc[start:end].to_numpy()
        idx = start + int(np.argmax(np.abs(valuesSlice - valuesSlice.mean())))
        indices.append(idx)
    indices.append(len(frame) - 1)
    return frame.iloc[indices].reset_index(drop = True)


def _emptyFigure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title = title,
        xaxis = {"visible": False}, yaxis = {"visible": False},
        annotations = [{
            "text": "No data",
            "xref": "paper", "yref": "paper",
            "x": 0.5, "y": 0.5, "showarrow": False,
            "font": {"size": 16, "color": "#888"},
        }],
        height = 300,
    )
    return fig


def _summaryCard(stats: dict) -> Any:
    if stats["count"] == 0:
        return dbc.Alert("No data in selected range.", color = "secondary")
    rows = [
        ("count", stats["count"]),
        ("mean", f"{stats['mean']:.4f}"),
        ("std", f"{stats['std']:.4f}"),
        ("min", f"{stats['min']:.4f}"),
        ("p5", f"{stats['p5']:.4f}"),
        ("median", f"{stats['median']:.4f}"),
        ("p95", f"{stats['p95']:.4f}"),
        ("max", f"{stats['max']:.4f}"),
        ("last", f"{stats['last']:.4f}"),
        ("lastTs", stats["lastTs"] or "-"),
    ]
    return dbc.Table(
        [html.Tbody([html.Tr([html.Th(k), html.Td(str(v))]) for k, v in rows])],
        bordered = True, size = "sm", striped = True,
    )


def register() -> None:
    @callback(
        Output("history-entity-dropdown", "options"),
        Output("history-entity-dropdown", "value"),
        Input("history-entity-type", "value"),
    )
    def _populateEntities(entityType):
        if not session.isBound():
            return [], None
        graph = session.getGraph()
        return _entityChoices(graph, entityType or "edge"), None

    @callback(
        Output("history-attribute-dropdown", "options"),
        Output("history-attribute-dropdown", "value"),
        Input("history-entity-dropdown", "value"),
    )
    def _populateAttributes(hashKey):
        if not hashKey or not session.isBound():
            return [], None
        graph = session.getGraph()
        entity = _findEntity(graph, hashKey)
        if entity is None:
            return [], None
        attrs = list(getattr(type(entity), "history", {}).keys())
        return [{"label": a, "value": a} for a in attrs], (attrs[0] if attrs else None)

    @callback(
        Output("history-timeseries", "figure"),
        Output("history-distribution", "figure"),
        Output("history-summary", "children"),
        Input("history-entity-dropdown", "value"),
        Input("history-attribute-dropdown", "value"),
        Input("history-date-range", "start_date"),
        Input("history-date-range", "end_date"),
        Input("history-aggregation", "value"),
        Input("history-refresh-btn", "n_clicks"),
    )
    def _renderCharts(hashKey, attribute, startDate, endDate, aggregation, refreshClicks):
        if not (hashKey and attribute and startDate and endDate and session.isBound()):
            return _emptyFigure("Time-series"), _emptyFigure("Distribution"), ""

        project = session.getProject()
        graph = session.getGraph()
        entity = _findEntity(graph, hashKey)
        if entity is None:
            return _emptyFigure("Time-series"), _emptyFigure("Distribution"), ""

        kind = type(entity).kind
        spec = specFor(kind, attribute)
        if spec is None:
            return _emptyFigure("Time-series"), _emptyFigure("Distribution"), \
                   dbc.Alert(f"No HistorySpec for {kind}/{attribute}", color = "warning")

        triggered = (dash.callback_context.triggered or [{}])[0].get("prop_id", "")
        refresh = "history-refresh-btn" in triggered and bool(refreshClicks)

        try:
            frame = fetch(
                projectPath = project.path, kind = kind, hashKey = hashKey,
                attribute = attribute, spec = spec,
                start = startDate, end = endDate, refresh = refresh,
            )
        except HistorianError as exc:
            return _emptyFigure("Time-series"), _emptyFigure("Distribution"), \
                   dbc.Alert(str(exc), color = "danger")

        if aggregation in ("W", "M"):
            frame = resample(frame, freq = aggregation, how = "mean")

        if frame.empty:
            return _emptyFigure("Time-series"), _emptyFigure("Distribution"), \
                   dbc.Alert("No data in selected range.", color = "secondary")

        downsampled = _lttbDownsample(frame, LTTB_THRESHOLD)
        rolled = rolling(downsampled, window = 7)

        ts = go.Figure()
        ts.add_trace(go.Scattergl(
            x = downsampled["ts"], y = downsampled["value"],
            mode = "lines+markers", name = "value",
        ))
        ts.add_trace(go.Scattergl(
            x = rolled["ts"], y = rolled["rollingMean"],
            mode = "lines", name = "7-period rolling mean",
            line = {"dash": "dash"},
        ))
        ts.update_layout(
            title = f"{attribute} - {entity.name}",
            xaxis_title = "ts", yaxis_title = attribute, height = 350,
        )

        dist = distribution(frame, bins = 20)
        distFig = go.Figure()
        if not dist.empty:
            distFig.add_trace(go.Bar(
                x = (dist["binStart"] + dist["binEnd"]) / 2.0,
                y = dist["count"],
            ))
        distFig.update_layout(
            title = "Distribution", xaxis_title = attribute,
            yaxis_title = "count", height = 280,
        )

        return ts, distFig, _summaryCard(summary(frame))