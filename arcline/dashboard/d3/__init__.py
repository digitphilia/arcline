# -*- encoding: utf-8 -*-

"""
arcline_d3 - Custom Dash Component Package
==========================================

Houses the hand-written :class:`NetworkCanvas` Dash component built on
React (provided by Dash at runtime) and D3.js (loaded externally via
:data:`arcline.dashboard.app` ``external_scripts``).

The component is implemented as plain ES5 JavaScript (no JSX, no
webpack build step) so the framework can be shipped without a Node
toolchain on the end-user side. ``window.arcline_d3.NetworkCanvas``
is the React component the Python wrapper resolves at render time.
"""

from arcline.dashboard.d3.NetworkCanvas import NetworkCanvas

__all__ = ["NetworkCanvas"]
