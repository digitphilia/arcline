# -*- encoding: utf-8 -*-

"""
Arcline Command-Line Interface
==============================

Thin :mod:`typer` shim exposing the ``arcline`` console script with
``init``, ``validate`` and ``dashboard`` subcommands. The dashboard
command lazy-imports :mod:`arcline.dashboard` so the CLI remains
usable even when the optional dashboard extras are not installed.
"""

from arcline.cli.main import app

__all__ = ["app"]
