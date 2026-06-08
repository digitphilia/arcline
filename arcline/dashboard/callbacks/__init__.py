# -*- encoding: utf-8 -*-

"""
Dashboard Callbacks Registry
============================

Single entry point (:func:`registerAll`) used by
:func:`arcline.dashboard.app.createApp` to wire all per-page
callbacks against the :class:`dash.Dash` instance.

The actual callback definitions live in sibling modules
(``nodes_cb``, ``edges_cb``, ``visualize_cb``) and are imported
lazily so that the import-time cost only materialises when the
dashboard is actually instantiated.
"""

from dash import Dash
import dash


def registerAll(app : Dash) -> None:
    """
    Register every callback module against ``app``.

    :type  app: Dash
    :param app: The Dash application instance to attach callbacks
        to.

    :rtype:   None
    """

    from arcline.dashboard.callbacks.nodes_cb import (
        register as registerNodes,
    )
    from arcline.dashboard.callbacks.edges_cb import (
        register as registerEdges,
    )
    from arcline.dashboard.callbacks.visualize_cb import (
        register as registerViz,
    )
    from arcline.dashboard.callbacks.history_cb import (
        register as registerHistory,
    )

    registerNodes(app)
    registerEdges(app)
    registerViz(app)
    registerHistory()

    # navbar theme-toggle (clientside; fires window.arcToggleTheme)
    app.clientside_callback(
        """
        function(n) {
            if (n && window.arcToggleTheme) { window.arcToggleTheme(); }
            return window.dash_clientside.no_update;
        }
        """,
        # we route into the throwaway toast wrapper just to satisfy
        # the callback-needs-output contract; no actual change made
        dash.dependencies.Output("arc-global-save-toast", "children"),
        dash.dependencies.Input("arc-theme-toggle-btn", "n_clicks"),
        prevent_initial_call = True,
    )
