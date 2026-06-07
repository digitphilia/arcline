# -*- encoding: utf-8 -*-

"""
Arcline CLI Entry Point
-----------------------

Wires the three Phase 1 subcommands (``init``, ``validate``,
``dashboard``) onto a single :class:`typer.Typer` application.
"""

import typer

from arcline.cli.commands import dashboard, init, validate


app = typer.Typer(
    name = "arcline",
    help = "arcline - Supply Chain Network Optimization Framework",
    no_args_is_help = True,
    add_completion = False,
)

app.command(name = "init")(init)
app.command(name = "validate")(validate)
app.command(name = "dashboard")(dashboard)


if __name__ == "__main__":
    app()
