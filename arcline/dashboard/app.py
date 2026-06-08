# -*- encoding: utf-8 -*-

"""
Dashboard Application Entry Point
---------------------------------

Two top-level helpers compose the dashboard:

  * :func:`createApp` builds the :class:`dash.Dash` instance,
    binds an optional project, registers every multi-page route,
    and wires the callback registry.
  * :func:`run` is the thin convenience wrapper invoked by
    ``python -m arcline.dashboard`` and by the ``arcline dashboard``
    CLI command.
"""

from pathlib import Path
from typing import Any, List, Optional, Union

import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from arcline.dashboard.callbacks import registerAll
from arcline.dashboard.components import makeNavbar
from arcline.dashboard.config import DashboardSettings, getSettings
from arcline.dashboard.server import createServer
from arcline.dashboard.state import session
from arcline.dashboard.state.store import ALL_STORES


def __resolveSettings__(
        projectPath : Optional[Union[Path, str]],
        settings : Optional[DashboardSettings],
) -> DashboardSettings:
    """
    Resolve the active :class:`DashboardSettings`, honouring an
    explicit override before falling back to the env-driven cached
    singleton from :func:`getSettings`. When ``projectPath`` is
    supplied, it overrides the resolved settings' ``projectPath``
    field.

    :type  projectPath: Optional[Union[Path, str]]
    :param projectPath: Optional project path override.

    :type  settings: Optional[DashboardSettings]
    :param settings: Optional fully-formed settings instance.

    :rtype:   DashboardSettings
    :returns: The resolved settings.
    """

    resolved = settings if settings is not None else getSettings()
    if projectPath is not None:
        resolved = resolved.model_copy(
            update = {"projectPath": Path(projectPath)}
        )

    return resolved


def __resolveTheme__(name : str) -> Any:
    """
    Resolve a dash-bootstrap-components theme name to its stylesheet
    URL; falls back to ``BOOTSTRAP`` for unknown names.

    :type  name: str
    :param name: Theme identifier (case-insensitive).

    :rtype:   Any
    :returns: The stylesheet URL string.
    """

    return getattr(dbc.themes, name.upper(), dbc.themes.BOOTSTRAP)


def __deriveProjectName__() -> str:
    """
    Read the bound project's display name, falling back to a
    placeholder when no project is bound.

    :rtype:   str
    :returns: The display name for the navbar brand.
    """

    if not session.isBound():
        return "(no project)"

    try:
        return session.getProject().name
    except RuntimeError:
        return "(no project)"


def __buildLayout__() -> html.Div:
    """
    Build the top-level Dash layout shared across every page.

    :rtype:   html.Div
    :returns: A container holding the navbar, the multi-page
        container, and every shared ``dcc.Store`` slot.
    """

    stores : List[Any] = [dcc.Store(id = sid) for sid in ALL_STORES]
    return html.Div(
        [
            makeNavbar(projectName = __deriveProjectName__()),
            *stores,
            dash.page_container,
        ]
    )


def createApp(
        projectPath : Optional[Union[Path, str]] = None,
        settings : Optional[DashboardSettings] = None
) -> Dash:
    """
    Construct and return a fully wired :class:`dash.Dash` instance.

    :type  projectPath: Optional[Union[Path, str]]
    :param projectPath: Optional path to a project; when supplied,
        the project is loaded into the session before the Dash app
        is constructed so that page layouts observe the bound state.

    :type  settings: Optional[DashboardSettings]
    :param settings: Optional pre-resolved settings instance.

    :rtype:   Dash
    :returns: A configured Dash application ready to ``.run()``.
    """

    resolved = __resolveSettings__(projectPath, settings)

    if resolved.projectPath is not None:
        session.bindProject(resolved.projectPath)

    flaskServer = createServer(resolved)
    theme = __resolveTheme__(resolved.theme)

    app = Dash(
        __name__,
        server = flaskServer,
        use_pages = True,
        pages_folder = "pages",
        external_stylesheets = [
            theme,
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        ],
        external_scripts = [
            "https://d3js.org/d3.v7.min.js",
        ],
        suppress_callback_exceptions = True,
        title = "arcline | Dashboard",
    )

    app.layout = __buildLayout__()
    registerAll(app)
    return app


def run(
        projectPath : Optional[Union[Path, str]] = None,
        host : str = "127.0.0.1",
        port : int = 8050,
        debug : bool = False
) -> None:
    """
    Build the dashboard app and start its development server.

    :type  projectPath: Optional[Union[Path, str]]
    :param projectPath: Optional path to a project; forwarded to
        :func:`createApp`.

    :type  host: str
    :param host: Bind host for the underlying Flask server.

    :type  port: int
    :param port: TCP port to listen on.

    :type  debug: bool
    :param debug: Enable Dash hot-reload and verbose tracebacks.

    :rtype:   None
    """

    app = createApp(projectPath = projectPath)
    runner = getattr(app, "run", None) or getattr(app, "run_server")
    runner(host = host, port = port, debug = debug)


if __name__ == "__main__":
    run()
