# -*- encoding: utf-8 -*-

"""
Dash Multi-Page Registry
========================

Module-level package whose presence enables :mod:`dash`'s ``pages``
discovery mechanism. Each sibling module in this directory registers
itself with :func:`dash.register_page` at import time; this file is
intentionally bare aside from the module docstring.
"""
