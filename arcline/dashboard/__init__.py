# -*- encoding: utf-8 -*-

"""
arcline Interactive Dashboard
=============================

Dash + Plotly powered front-end for browsing, editing, and visualising
an :class:`arcline.graph.base.AbstractGraph` instance backed by an
on-disk :class:`arcline.io.Project`. The dashboard is the user-facing
companion to the headless graph and I/O layers; it exposes CRUD pages
for nodes / edges and a full-network visualisation page with
force-directed, tiered, and geographic layout modes.

Phase 1 of the framework ships the dashboard as a single-user, local
process (no auth, no multi-tenant state); multi-user hardening is
parked for a later phase.
"""

from arcline.dashboard.app import createApp, run

__all__ = [
    "createApp",
    "run",
]
