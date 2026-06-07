# -*- encoding: utf-8 -*-

"""
Arcline CLI Subcommand Implementations
--------------------------------------

Pure callbacks for the three Phase 1 subcommands wired into
:mod:`arcline.cli.main`. Each function is intentionally small and
delegates the real work to :class:`arcline.io.Project`; the CLI
itself is only responsible for argument parsing and human-friendly
output.

The ``dashboard`` callback lazy-imports :mod:`arcline.dashboard` so
that ``arcline init`` and ``arcline validate`` keep working even
when the optional dashboard extras are not installed.
"""

from pathlib import Path
from typing import Optional

import typer

from arcline.io import Project


def init(
        path : Path = typer.Argument(
            ..., help = "Project directory to create"
        ),
        name : Optional[str] = typer.Option(
            None, "--name", "-n", help = "Project name"
        )
) -> None:
    """
    Create an empty arcline project at ``path``.

    :type  path: Path
    :param path: Target directory; created if it does not yet exist.

    :type  name: Optional[str]
    :param name: Optional human-readable project name; defaults to
        the target directory's basename.

    :rtype:   None
    """

    Project.init(path, name = name)
    typer.secho(
        f"Initialized arcline project at {path}",
        fg = typer.colors.GREEN,
    )


def validate(
        path : Path = typer.Argument(
            ..., help = "Project directory to validate"
        )
) -> None:
    """
    Validate the integrity of an arcline project on disk and report
    every issue found. Exits with status code ``1`` if any
    ``error``-severity issue is reported.

    :type  path: Path
    :param path: Path to the project root directory.

    :rtype:   None
    """

    proj = Project.open(path)
    issues = proj.validate()

    if not issues:
        typer.secho(
            f"Project at {path} is valid (0 issues).",
            fg = typer.colors.GREEN,
        )
        raise typer.Exit(code = 0)

    error_count = 0
    for issue in issues:
        color = (
            typer.colors.RED if issue.severity == "error"
            else typer.colors.YELLOW
        )
        location = f" @ {issue.location}" if issue.location else ""
        typer.secho(
            f"[{issue.severity.upper()}] [{issue.code}] "
            f"{issue.message}{location}",
            fg = color,
        )
        if issue.severity == "error":
            error_count += 1

    if error_count:
        typer.secho(
            f"\n{error_count} error(s) found.",
            fg = typer.colors.RED, err = True,
        )
        raise typer.Exit(code = 1)

    typer.secho(
        f"\n{len(issues)} warning(s) found; project is loadable.",
        fg = typer.colors.YELLOW,
    )


def dashboard(
        path : Path = typer.Argument(
            ..., help = "Project directory to serve"
        ),
        host : str = typer.Option(
            "127.0.0.1", "--host", help = "Host interface to bind."
        ),
        port : int = typer.Option(
            8050, "--port", help = "Port to listen on."
        ),
        debug : bool = typer.Option(
            False, "--debug", help = "Enable Dash debug mode."
        )
) -> None:
    """
    Launch the Dash dashboard for the project at ``path``.

    The dashboard module is imported lazily so that this command
    fails gracefully when the optional ``[dashboard]`` extras are
    not installed.

    :type  path: Path
    :param path: Project root directory to serve.

    :type  host: str
    :param host: Host interface to bind.

    :type  port: int
    :param port: Port to listen on.

    :type  debug: bool
    :param debug: Enable Dash debug mode (auto-reload, verbose
        tracebacks).

    :rtype:   None
    """

    try:
        from arcline.dashboard.app import run
    except ImportError as exc:
        typer.secho(
            f"Dashboard not available: {exc}. Install with "
            f"`pip install -e .[dashboard]`.",
            fg = typer.colors.RED, err = True,
        )
        raise typer.Exit(code = 2)

    run(path, host = host, port = port, debug = debug)
